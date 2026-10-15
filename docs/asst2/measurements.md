---
title: A2 · Measurements
---

# Assignment 2 · Measurements

## Environment and timing

Local measurements use Ubuntu 24.04, an Intel Core i9-13900H (14 physical cores,
20 logical CPUs), eight worker threads, and default CPU scheduling. Both builds
use the provided Makefile's `-O3 -std=c++11` flags.

The reference Linux x86-64 executable records **GCC 9.3.0-17ubuntu1~20.04** in its
ELF `.comment` section. The comparison rebuilds the student code with that same
compiler package and with the system's GCC 13.3.0. Both use the host's shared
runtime libraries; this is a compiler comparison on the local machine.

Each reported measurement is the minimum of **three independent program runs**,
each invoked with `-i 1`. This uses fewer repetitions than the normal harness,
which takes the minimum of five runs, each with three internal timing iterations.
Correctness checks run on every invocation.

The supplied tests time their launches and synchronization. Pool construction
and destruction happen outside that region; always-spawn creates its workers
inside `run()`, so those launches include thread creation and joining.

The tables use `student time / reference time`: smaller is faster. The local
performance thresholds are `< 1.2` for Part A and `< 1.5` for Part B. Part B grades
only the sleeping pool, including its synchronous `run()` interface.

The course grades on an AWS `c7g.4xlarge` ARM machine. These measurements establish
local behavior and do not predict that machine's grade.

## GCC 9.3 performance results

All 33 Part A comparisons and all 22 Part B sleeping-pool comparisons met the
local performance thresholds. Assignment sources were unchanged during the run.

### Part A

| Workload | Spawn / ref | Spin / ref | Sleep / ref |
| --- | ---: | ---: | ---: |
| Super-super light | 1.005 | 0.966 | 1.012 |
| Super light | 1.017 | 1.010 | 0.898 |
| Ping-pong equal | 0.994 | 1.016 | 0.974 |
| Ping-pong unequal | 1.121 | 1.112 | 1.058 |
| Recursive Fibonacci | 1.000 | 1.007 | 0.920 |
| Math loop | 1.026 | 0.998 | 1.015 |
| Math loop, fewer tasks | 1.023 | 1.035 | 0.982 |
| Math loop, fan-in | 1.001 | 1.043 | 1.004 |
| Math loop, reduction tree | 1.022 | 1.048 | 1.052 |
| Spin between calls | 0.985 | 0.913 | 0.882 |
| Mandelbrot | 1.015 | 1.017 | 1.101 |

??? note "Absolute times (ms): student / reference"

    | Workload | Spawn | Spin | Sleep |
    | --- | ---: | ---: | ---: |
    | Super-super light | 36.060 / 35.866 | 9.479 / 9.809 | 8.343 / 8.243 |
    | Super light | 35.890 / 35.295 | 11.580 / 11.467 | 9.027 / 10.049 |
    | Ping-pong equal | 135.009 / 135.783 | 104.890 / 103.188 | 100.627 / 103.298 |
    | Ping-pong unequal | 273.276 / 243.800 | 244.004 / 219.349 | 259.360 / 245.089 |
    | Recursive Fibonacci | 187.023 / 186.978 | 211.157 / 209.627 | 205.547 / 223.447 |
    | Math loop | 245.550 / 239.265 | 132.786 / 133.078 | 116.773 / 115.084 |
    | Math loop, fewer tasks | 271.246 / 265.115 | 137.753 / 133.151 | 126.133 / 128.388 |
    | Math loop, fan-in | 56.945 / 56.860 | 43.114 / 41.334 | 45.683 / 45.490 |
    | Math loop, reduction tree | 41.822 / 40.905 | 38.493 / 36.742 | 46.626 / 44.334 |
    | Spin between calls | 179.946 / 182.597 | 221.682 / 242.861 | 190.927 / 216.584 |
    | Mandelbrot | 38.620 / 38.041 | 38.158 / 37.519 | 54.652 / 49.622 |

### Part B

| Workload | `run()` / ref | Async / ref |
| --- | ---: | ---: |
| Super-super light | 0.904 | 0.779 |
| Super light | 0.750 | 0.713 |
| Ping-pong equal | 0.730 | 0.677 |
| Ping-pong unequal | 0.737 | 0.722 |
| Recursive Fibonacci | 0.779 | 0.764 |
| Math loop | 0.773 | 0.755 |
| Math loop, fewer tasks | 0.821 | 0.730 |
| Math loop, fan-in | 0.670 | 0.799 |
| Math loop, reduction tree | 0.774 | 0.827 |
| Spin between calls | 0.802 | 0.820 |
| Mandelbrot | 0.698 | 0.744 |

??? note "Absolute times (ms): student / reference"

    | Workload | `run()` | Async |
    | --- | ---: | ---: |
    | Super-super light | 10.834 / 11.986 | 9.036 / 11.607 |
    | Super light | 10.491 / 13.981 | 9.040 / 12.684 |
    | Ping-pong equal | 107.344 / 147.019 | 96.962 / 143.319 |
    | Ping-pong unequal | 176.584 / 239.532 | 172.951 / 239.545 |
    | Recursive Fibonacci | 168.355 / 216.136 | 161.554 / 211.443 |
    | Math loop | 93.043 / 120.382 | 78.524 / 103.943 |
    | Math loop, fewer tasks | 104.469 / 127.301 | 57.602 / 78.927 |
    | Math loop, fan-in | 33.626 / 50.184 | 28.409 / 35.565 |
    | Math loop, reduction tree | 35.814 / 46.246 | 27.940 / 33.771 |
    | Spin between calls | 172.251 / 214.807 | 175.696 / 214.180 |
    | Mandelbrot | 37.719 / 54.033 | 36.523 / 49.058 |

Across Part B's 22 measurements, student time is lower in every case. The
median time reduction is **24.0%**, with reductions ranging from **9.6% to 33.0%**.
Part A is close to the reference: the median ratios for spawn, spin, and sleep
are 1.015, 1.016, and 1.004, respectively.

The largest ratio is 1.121 in Part A and 0.904 in Part B. These are ratios to the
corresponding reference implementation, not speedups over serial execution.

## What changes with the compiler?

Times below are milliseconds for the same Part B source and eight-worker setup:

| Workload | Serial, GCC 9.3 | Serial, GCC 13.3 | Sleep, GCC 9.3 | Sleep, GCC 13.3 |
| --- | ---: | ---: | ---: | ---: |
| Recursive Fibonacci | 925.630 | 587.485 | 168.355 | 105.484 |
| Math loop | 364.253 | 345.025 | 93.043 | 94.005 |
| Spin between calls | 335.818 | 207.626 | 172.251 | 104.566 |

`spin_between_run_calls` launches two `fib(40)` tasks between two light launches.
Its useful work changes substantially with compiler-generated Fibonacci code.
Switching from GCC 9.3 to GCC 13.3 improves serial time by **1.62×** and sleeping-pool
time by **1.65×**. The pool's speedup over its own serial build stays close to two:
**1.95×** with GCC 9.3 and **1.99×** with GCC 13.3.

The corrected reference sleeping-pool time is 214.807 ms. Comparing GCC 13 to this
GCC 9 reference gives a ratio of 0.487; using GCC 9 for both gives 0.802. A large
part of that apparent advantage comes from the compiler, while the older build
still passes comfortably. The math-loop times change much less.

[Complete samples and source hashes](../assets/benchmarks/a2-results.json) ·
[Compiler package versions and hashes](../assets/benchmarks/a2-toolchain.json)

## Reference timer correction

The current source uses `std::chrono::steady_clock`. The supplied Linux x86-64
reference binary instead converts TSC ticks using a sampled CPU MHz value.
On this machine that conversion can disagree with the constant-rate TSC.

`tests/reference_timer.py` measures seconds per TSC tick against
`CLOCK_MONOTONIC`, using the median of five 100 ms samples. It reads the conversion
factor from its own reference child process and applies:

```text
corrected reference milliseconds
    = reported milliseconds
    × measured seconds per TSC tick / reference seconds per TSC tick
```

The binary and its workload remain unchanged. The correction applies to its
reported times; process startup and shutdown are not substituted for the timed
region. The saved results include each correction factor.

## Correctness checks

The supplied `simple_test_sync`, `simple_test_async`, `strict_diamond_deps_async`,
and `strict_graph_deps_large_async` passed with one and eight workers in the
current GCC 13 build.

The standalone [additional check](../assets/benchmarks/a2_checks.cpp) exercises
the sleeping pool with one, two, and eight workers:

- 300 short `A → B` chains per worker count. A delays briefly so B is likely to
  be submitted before A finishes.
- 50 graphs of 48 launches per worker count, with 1–7 tasks per launch. Each graph
  includes a chain and additional randomly selected predecessor edges.
- Every task ID must execute exactly once, each successor checks its predecessors'
  completed counts, and `sync()` must return with every task finished.
- Repeated `sync()` calls and 30 idle pool construction/destruction cycles.

All checks passed with libstdc++ debug iterators under both GCC 9.3 and GCC 13.3.
They exercise the [queue transitions](part-b.md#3-follow-one-graph-through-the-lists)
and repeated use of the worker pool.

From the repository root:

```sh
g++ -O1 -g -D_GLIBCXX_DEBUG -std=c++11 -pthread \
    -Iasst2/part_b docs/assets/benchmarks/a2_checks.cpp \
    asst2/part_b/tasksys.cpp -o /tmp/a2-checks
timeout 30s /tmp/a2-checks
```

## Reproduce the performance measurements

The [measurement script](../assets/benchmarks/benchmark_a2.py) builds in temporary
copies. Supply a working GCC 9.3.0 compiler and choose a new output directory:

```sh
python3 docs/assets/benchmarks/benchmark_a2.py . /tmp/a2-measurements \
    --cxx9 /path/to/g++-9 -n 8 --rounds 3 --iterations 1
```

Use `--rounds 5 --iterations 3` for the normal harness's repetition counts. The
script records source hashes, compiler versions, raw timings, and corrected
reference timings. An extracted compiler may also need its library directory in
`LD_LIBRARY_PATH`.

For the usual grading report, build the selected part and run the harness from
that directory:

```sh
cd asst2/part_b
make
python3 ../tests/run_test_harness.py -n 8 -a
```

For Part A, run the same commands from `asst2/part_a` and omit `-a`.
