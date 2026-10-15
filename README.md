# parlab

Implementations and performance notes for Stanford CS149 and CMU 15-418/618.

[Read the notes](https://leexsean.github.io/parlab/)

## Contents

| Assignment | Focus | Status |
| --- | --- | --- |
| [A1 · CPU parallelism](https://leexsean.github.io/parlab/asst1/) | CPU threads, SIMD/ISPC, performance analysis | Completed |
| [A2 · Task system](https://leexsean.github.io/parlab/asst2/) | Thread pools and dependency scheduling | Implemented |
| [A3 · CUDA renderer](https://leexsean.github.io/parlab/asst3/) | CUDA SAXPY, prefix sum, circle rendering | Pending |
| [A4 · MPI wire routing](https://leexsean.github.io/parlab/cmu-asst4/) | Distributed routing and MPI communication | Pending |
| [A5 · RK4 kernel](https://leexsean.github.io/parlab/asst5/) | GPU optimization of a 3D heat-equation solver | Pending |

Assignments 1–3 and 5 follow [Stanford CS149](https://github.com/stanford-cs149).
Assignment 4 follows [CMU 15-418/618, Fall 2025](https://github.com/cmu15418f25/asst4).

## Assignment 2 tests

The [test harness](asst2/tests/run_test_harness.py) now uses
[reference_timer.py](asst2/tests/reference_timer.py) to correct the supplied Linux
x86-64 reference executable's legacy timer conversion. It calibrates TSC ticks
against `CLOCK_MONOTONIC` and rescales the reported reference times, preserving
the executable, workloads, and report format.

```sh
cd asst2/part_b
make
python3 ../tests/run_test_harness.py -n 8 -a
```

For Part A, use `asst2/part_a` and omit `-a`. Add `--raw-reference-timer` to use
the reference's uncorrected times. See the [measurement notes](docs/asst2/measurements.md)
for the timing method and compiler comparison.

## Use

To preview the notes locally, with the packages in
[requirements-docs.txt](requirements-docs.txt) installed:

```sh
python3 -m mkdocs serve
```

The site is built from [docs/](docs/) with MkDocs Material and published through
[GitHub Actions](.github/workflows/deploy.yml).

Unofficial and unaffiliated with either course. Enrolled students should use the
official starters linked above and follow their course's academic-integrity policy.
