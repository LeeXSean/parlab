# Local notes

Build settings, timing fixes, and local measurement tools in this checkout.
The local CPU setup uses Ubuntu 24.04 on x86-64, GCC 13.3, and ISPC 1.28.1.

## CPU timers

The source-build timers use `std::chrono::steady_clock` to measure elapsed
seconds, avoiding a conversion based on sampled CPU frequency. This applies to
[A1](asst1/common/CycleTimer.h), [A2](asst2/common/CycleTimer.h), and A3's
[SAXPY](asst3/saxpy/CycleTimer.h), [scan](asst3/scan/CycleTimer.h), and
[renderer](asst3/render/CycleTimer.h) host timers.

Prebuilt reference executables keep their original timers. A2 handles its legacy
Linux x86-64 reference separately, as described below.

## A1: ISPC, AVX2, and data

- Programs 3–5 invoke `ispc` from `PATH` with the `avx2-i32x8` target. The
  [P4](asst1/prog4_sqrt/Makefile) and [P6](asst1/prog6_kmeans/Makefile) C++ builds
  also use `-march=native`; their binaries depend on the build machine's CPU.
- The [P3 Makefile](asst1/prog3_mandelbrot_ispc/Makefile) disables floating-point
  contraction in C++ and FMA in ISPC to keep Mandelbrot output consistent with
  the reference calculation.
- P6 reads `data.dat` from its working directory. The large file is excluded
  from Git. [main.cpp](asst1/prog6_kmeans/main.cpp) contains a commented data
  generator; normal execution requires the file to exist already.

## A2: reference timing correction

The supplied Linux x86-64 reference converts TSC ticks using a sampled CPU MHz
value. On the local machine, that scale can disagree with the constant-rate TSC.
[reference_timer.py](asst2/tests/reference_timer.py) calibrates seconds per TSC
tick against `CLOCK_MONOTONIC`, then rescales each reference process's reported
milliseconds. The executable and workloads remain unchanged.

The [harness](asst2/tests/run_test_harness.py) applies this correction automatically
to the recognized legacy Linux x86-64 binary and keeps the original report
format. Other reference platforms pass through unchanged. Calibration requires
a C compiler (`cc` or `gcc`), `nm` from binutils, a constant TSC, and permission
to read the harness's own child process through `/proc/<pid>/mem`.

```sh
cd asst2/part_b
make
python3 ../tests/run_test_harness.py -n 8 -a
```

For Part A, use `asst2/part_a` and omit `-a`.

| Option | Effect |
| --- | --- |
| `--raw-reference-timer` | Disable calibration and use the reference's original reported times. |
| `--timeout SECONDS` | Limit each program execution; defaults to 180 seconds. |

Calibration failures are reported rather than silently accepting an uncorrected
comparison. The default harness still takes the minimum of five program runs,
each with three internal timing iterations. See the
[A2 measurements](docs/asst2/measurements.md) for the correction formula and the
GCC 9.3 versus GCC 13.3 comparison.

## A3: local CUDA build settings

The [SAXPY](asst3/saxpy/Makefile), [scan](asst3/scan/Makefile), and
[renderer](asst3/render/Makefile) Makefiles use `nvcc -arch=native` and the local
CUDA library path `/usr/local/cuda/lib64`. For performance comparisons, the scan
and renderer Python checkers select their `_x86` reference binaries on x86-64.
These are build and checker settings; the A3 implementations are still pending.

## Reproducing measurements

The [A1](docs/assets/benchmarks/benchmark.py) and
[A2](docs/assets/benchmarks/benchmark_a2.py) measurement scripts build temporary
copies, keeping the working source and build products intact. Run ordinary
`make` commands from the individual program or part directory. A2's Makefiles
clean and rebuild `runtasks` on each invocation.

The A2 compiler comparison accepts a separate GCC 9.3 toolchain through
`--cxx9`; it does not replace the system compiler. Commands, environment details,
and saved samples are linked from the [A1](docs/asst1/measurements.md) and
[A2](docs/asst2/measurements.md) measurement notes.
