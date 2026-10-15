"""Correct the legacy Linux x86 reference timer without changing the binary.

The reference converts TSC ticks using a sampled CPU MHz value. Read that
conversion factor from our child process and correct its reported milliseconds
using a TSC frequency measured against CLOCK_MONOTONIC.
"""

import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import struct
import subprocess
import tempfile
import time


_TICK_SYMBOL = "_ZZN10CycleTimer14secondsPerTickEvE18secondsPerTick_val"
_READY_SYMBOL = "_ZZN10CycleTimer14secondsPerTickEvE11initialized"

_TSC_PROBE = r"""
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <time.h>
#include <x86intrin.h>

int main(void) {
    for (int i = 0; i < 5; ++i) {
        struct timespec start, end, delay = {0, 100000000};
        if (clock_gettime(CLOCK_MONOTONIC, &start)) return 1;
        _mm_lfence();
        unsigned long long first = __rdtsc();
        while (nanosleep(&delay, &delay)) {}
        _mm_lfence();
        unsigned long long last = __rdtsc();
        if (clock_gettime(CLOCK_MONOTONIC, &end)) return 1;
        double seconds = (end.tv_sec - start.tv_sec)
                       + (end.tv_nsec - start.tv_nsec) * 1e-9;
        printf("%.17g\n", seconds / (last - first));
    }
    return 0;
}
"""


class ReferenceTimerCalibration:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.seconds_per_tick = None
        self.symbols = {}

    def _legacy_symbols(self, binary):
        if not self.enabled or platform.system() != "Linux":
            return None
        if platform.machine().lower() not in ("x86_64", "amd64"):
            return None
        if binary in self.symbols:
            return self.symbols[binary]

        image = binary.read_bytes()
        if b"/proc/cpuinfo" not in image or b"cpu MHz" not in image:
            self.symbols[binary] = None
            return None
        if image[:6] != b"\x7fELF\x02\x01":
            raise RuntimeError("Unsupported legacy reference executable format")
        elf_type = struct.unpack_from("<H", image, 16)[0]
        if elf_type not in (2, 3):
            raise RuntimeError("Unsupported legacy reference ELF type")
        nm = shutil.which("nm")
        if not nm:
            raise RuntimeError("Reference timer calibration requires nm (binutils)")
        rows = subprocess.check_output(
            [nm, "-P", "--defined-only", str(binary)], timeout=10
        ).decode().splitlines()
        addresses = {}
        for row in rows:
            fields = row.split()
            if fields and fields[0] in (_TICK_SYMBOL, _READY_SYMBOL):
                addresses[fields[0]] = int(fields[2], 16)
        if len(addresses) != 2:
            raise RuntimeError("Legacy reference timer symbols are unavailable")
        result = (addresses, elf_type == 3)
        self.symbols[binary] = result
        return result

    def _measure_tick(self):
        if "constant_tsc" not in Path("/proc/cpuinfo").read_text():
            raise RuntimeError("Reference timer calibration requires a constant TSC")
        compiler = shutil.which("cc") or shutil.which("gcc")
        if not compiler:
            raise RuntimeError("Reference timer calibration requires a C compiler")
        with tempfile.TemporaryDirectory(prefix="cs149-tsc-") as directory:
            directory = Path(directory)
            source = directory / "measure.c"
            executable = directory / "measure"
            source.write_text(_TSC_PROBE)
            subprocess.run(
                [compiler, "-O2", "-std=c11", str(source), "-o", str(executable)],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=20,
            )
            output = subprocess.check_output([str(executable)], timeout=10)
        samples = [float(value) for value in output.splitlines()]
        if len(samples) != 5 or any(
            not math.isfinite(value) or value <= 0 for value in samples
        ):
            raise RuntimeError("Invalid TSC calibration measurements")
        self.seconds_per_tick = statistics.median(samples)

    @staticmethod
    def _image_base(pid, binary):
        for row in Path("/proc/%d/maps" % pid).read_text().splitlines():
            fields = row.split(maxsplit=5)
            if (len(fields) == 6 and fields[5] == str(binary)
                    and int(fields[2], 16) == 0):
                return int(fields[0].split("-")[0], 16)
        raise OSError("Reference executable mapping is not ready")

    def _read_tick(self, process, binary, symbols, deadline, timeout):
        addresses, is_pie = symbols
        base = None
        while process.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(process.args, timeout)
            try:
                if base is None:
                    base = self._image_base(process.pid, binary) if is_pie else 0
                with open("/proc/%d/mem" % process.pid, "rb", buffering=0) as mem:
                    ready = os.pread(
                        mem.fileno(), 1, base + addresses[_READY_SYMBOL]
                    )
                    if ready == b"\x01":
                        value = os.pread(
                            mem.fileno(), 8, base + addresses[_TICK_SYMBOL]
                        )
                        tick = struct.unpack("<d", value)[0]
                        if math.isfinite(tick) and tick > 0:
                            return tick
                        raise RuntimeError("Invalid legacy reference timer scale")
            except PermissionError as error:
                raise RuntimeError(
                    "Cannot read the child reference timer through /proc; "
                    "local timing calibration is unavailable"
                ) from error
            except (OSError, struct.error):
                pass
            time.sleep(0.001)
        raise RuntimeError("Reference exited before its timer could be calibrated")

    def run(self, command, timeout):
        binary = Path(command[0]).resolve()
        symbols = self._legacy_symbols(binary)
        if symbols is None:
            output = subprocess.check_output(
                command, timeout=timeout
            )
            return output, 1.0
        if self.seconds_per_tick is None:
            self._measure_tick()

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE
        )
        deadline = time.monotonic() + timeout
        try:
            reference_tick = self._read_tick(
                process, binary, symbols, deadline, timeout
            )
            output, _ = process.communicate(
                timeout=max(0.001, deadline - time.monotonic())
            )
            if process.returncode:
                raise subprocess.CalledProcessError(
                    process.returncode, command, output=output
                )
            return output, self.seconds_per_tick / reference_tick
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.communicate()
            raise
