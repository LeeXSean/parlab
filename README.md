# parlab

A personal parallel-computing self-study workspace combining Stanford CS149 and CMU 15-418/618 labs with minimal compatibility changes for a modern local Linux/NVIDIA system.

## Labs

| Directory | Source | Focus |
| --- | --- | --- |
| `asst1` | Stanford CS149 | CPU multithreading, SIMD/ISPC, and performance analysis |
| `asst2` | Stanford CS149 | Parallel task systems and dependency-aware scheduling |
| `asst3` | Stanford CS149 | CUDA SAXPY, prefix sum, and circle rendering |
| `cmu-asst4` | CMU 15-418/618, Fall 2025 | MPI VLSI wire routing |
| `asst5-kernels` | Stanford CS149 | GPU kernel optimization |

## Local Compatibility Changes

- Added missing standard C++ headers required by modern compilers in `asst1`.
- Added `-arch=native` to the CUDA builds in `asst3`; rebuild after moving to another GPU.
- Local virtual environments and generated KMeans data, logs, and plots remain untracked.

## Upstream Sources

- [Stanford CS149 Assignment 1](https://github.com/stanford-cs149/asst1)
- [Stanford CS149 Assignment 2](https://github.com/stanford-cs149/asst2)
- [Stanford CS149 Assignment 3](https://github.com/stanford-cs149/asst3)
- [Stanford CS149 Assignment 5](https://github.com/stanford-cs149/asst5-kernels)
- [CMU 15-418/618 Fall 2025 Assignment 4](https://github.com/cmu15418f25/asst4)

This repository is unofficial and unaffiliated with either course. If you are enrolled in either course, follow its current academic-integrity policy and use the official starter repositories.
