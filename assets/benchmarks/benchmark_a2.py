"""Measure A2 in temporary copies; leave assignment files and binaries alone.

python3 benchmark_a2.py REPO OUTPUT --cxx9 /path/to/g++-9
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile


TESTS = [
    "super_super_light", "super_light", "ping_pong_equal", "ping_pong_unequal",
    "recursive_fibonacci", "math_operations_in_tight_for_loop",
    "math_operations_in_tight_for_loop_fewer_tasks",
    "math_operations_in_tight_for_loop_fan_in",
    "math_operations_in_tight_for_loop_reduction_tree", "spin_between_run_calls",
    "mandelbrot_chunked",
]
COMPARE = {
    "recursive_fibonacci", "recursive_fibonacci_async",
    "math_operations_in_tight_for_loop", "math_operations_in_tight_for_loop_async",
    "spin_between_run_calls", "spin_between_run_calls_async",
    "super_super_light_async",
}
SLEEP = "Parallel + Thread Pool + Sleep"
TIMING = re.compile(r"\[(.*?)\]:\s*\[([0-9.]+)\] ms")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cxx9", required=True)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("-n", "--threads", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if min(args.threads, args.rounds, args.iterations) < 1 or args.timeout <= 0:
        parser.error("thread, repetition, and timeout values must be positive")
    repo, out = args.repo.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "a2-results.json").exists():
        parser.error("output already contains a2-results.json; choose a new directory")

    source_files = [repo / "asst2" / part / name
                    for part in ("part_a", "part_b")
                    for name in ("tasksys.cpp", "tasksys.h", "itasksys.h", "Makefile")]
    source_files += list((repo / "asst2/common").glob("*"))
    source_files += [repo / "asst2/tests" / name
                     for name in ("main.cpp", "tests.h", "reference_timer.py")]
    source_files = [p for p in source_files if p.is_file()]
    hashes = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source_files}
    compiler_paths = {"gcc9": str(Path(shutil.which(args.cxx9) or args.cxx9).resolve()),
                      "current": str(Path(shutil.which(args.cxx) or args.cxx).resolve())}
    versions = {key: subprocess.check_output([path, "--version"], text=True).splitlines()[0]
                for key, path in compiler_paths.items()}
    if "9.3.0" not in versions["gcc9"]:
        parser.error("--cxx9 must identify GCC 9.3.0 for this comparison")
    spec = importlib.util.spec_from_file_location(
        "a2_reference_timer", repo / "asst2/tests/reference_timer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    timer = module.ReferenceTimerCalibration()
    result = {"collected_at_utc": datetime.now(timezone.utc).isoformat(),
              "reference_sha256": {
                  part: hashlib.sha256((repo / "asst2" / part / "runtasks_ref_linux").read_bytes()).hexdigest()
                  for part in ("part_a", "part_b")},
              "environment": {"platform": platform.platform(),
                              "cpu": subprocess.check_output(["lscpu"], text=True),
                              "compilers": versions, "threads": args.threads,
                              "flags": "Makefile: -O3 -std=c++11 -Wall, x86-64",
                              "outer_rounds": args.rounds,
                              "inner_iterations": args.iterations,
                              "statistic": "minimum of outer runs, each reporting its inner minimum",
                              "cpu_affinity": sorted(os.sched_getaffinity(0)),
                              "reference_timer": "TSC calibrated against CLOCK_MONOTONIC"},
              "source_sha256": hashes, "records": []}

    def save():
        (out / "a2-results.json").write_text(json.dumps(result, indent=2) + "\n")

    with tempfile.TemporaryDirectory(prefix="a2-measure-") as temp, \
            (out / "a2-raw.log").open("w") as log:
        temp = Path(temp)

        def run(command, cwd=None):
            process = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                                     timeout=args.timeout)
            log.write("\n$ " + " ".join(map(str, command)) + "\n" + process.stdout + process.stderr)
            log.flush()
            if process.returncode or "ERROR:" in process.stdout:
                raise RuntimeError(process.stdout[-2000:] + process.stderr[-2000:])
            return process.stdout

        builds = {}
        for compiler, path in compiler_paths.items():
            for part in (("part_a", "part_b") if compiler == "gcc9" else ("part_b",)):
                parent = temp / compiler
                for shared in ("common", "tests"):
                    if not (parent / shared).exists():
                        shutil.copytree(repo / "asst2" / shared, parent / shared,
                                        ignore=shutil.ignore_patterns("__pycache__"))
                dest = parent / part
                dest.mkdir()
                for name in ("tasksys.cpp", "tasksys.h", "itasksys.h", "Makefile"):
                    shutil.copy2(repo / "asst2" / part / name, dest / name)
                run(["make", "CXX=" + path + " -m64"], cwd=dest)
                builds[compiler, part] = dest / "runtasks"
        save()
        for part in ("part_a", "part_b"):
            names = TESTS if part == "part_a" else [name + suffix for name in TESTS
                                                       for suffix in ("", "_async")]
            ref = repo / "asst2" / part / "runtasks_ref_linux"
            for name in names:
                samples = {"reference": [], "gcc9": []}
                corrections = []
                if part == "part_b" and name in COMPARE:
                    samples["current"] = []
                for _ in range(args.rounds):
                    for compiler in samples:
                        binary = ref if compiler == "reference" else builds[compiler, part]
                        command = [str(binary), "-n", str(args.threads),
                                   "-i", str(args.iterations), name]
                        if compiler == "reference":
                            output, correction = timer.run(command, args.timeout)
                            output = output.decode()
                            corrections.append(correction)
                            log.write("\n$ " + " ".join(command) + "\n" + output)
                            log.flush()
                        else:
                            output, correction = run(command), 1.0
                        times = {key: float(value) * correction
                                 for key, value in TIMING.findall(output)}
                        if len(times) != 4 or "ERROR:" in output:
                            raise RuntimeError("Missing timings or failed correctness: " + output)
                        samples[compiler].append(times)
                minima = {compiler: {key: min(run[key] for run in runs)
                                    for key in runs[0]} for compiler, runs in samples.items()}
                graded = [key for key in minima["gcc9"] if key != "Serial"] \
                    if part == "part_a" else [SLEEP]
                ratios = {key: minima["gcc9"][key] / minima["reference"][key]
                          for key in graded}
                result["records"].append({"part": part, "test": name,
                                          "samples_ms": samples, "min_ms": minima,
                                          "reference_corrections": corrections,
                                          "gcc9_reference_ratios": ratios,
                                          "passed_perf": all(r < (1.2 if part == "part_a" else 1.5)
                                                             for r in ratios.values())})
                save()
                print(part, name, {key: round(value, 3) for key, value in ratios.items()},
                      flush=True)
        result["sources_unchanged"] = all(
            hashlib.sha256((repo / p).read_bytes()).hexdigest() == h for p, h in hashes.items())
        if not result["sources_unchanged"]:
            raise RuntimeError("Assignment sources changed during measurement; rerun before using results")
        result["seconds_per_tsc_tick"] = timer.seconds_per_tick
        save()
    print("Saved", out / "a2-results.json", flush=True)


if __name__ == "__main__":
    main()
