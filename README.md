# parlab

Parallel-computing exercises from Stanford CS149 and CMU 15-418/618,
adapted for local Linux and NVIDIA development.

## Contents

| Directory | Source | Focus |
| --- | --- | --- |
| [asst1](asst1/) | [CS149](https://github.com/stanford-cs149/asst1) | CPU threads, SIMD/ISPC, performance analysis |
| [asst2](asst2/) | [CS149](https://github.com/stanford-cs149/asst2) | Task systems and dependency scheduling |
| [asst3](asst3/) | [CS149](https://github.com/stanford-cs149/asst3) | CUDA SAXPY, prefix sum, circle rendering |
| [cmu-asst4](cmu-asst4/) | [15-418/618, Fall 2025](https://github.com/cmu15418f25/asst4) | MPI wire routing |
| [asst5-kernels](asst5-kernels/) | [CS149](https://github.com/stanford-cs149/asst5-kernels) | GPU kernel optimization |

## Notes

- `asst1` adds missing standard C++ headers.
- `asst3` uses `-arch=native`; rebuild when moving to a different GPU.
- Local environments and generated KMeans data, logs, and plots stay untracked.

Unofficial and unaffiliated with either course. Enrolled students should use the
official starters linked above and follow their course's academic-integrity policy.
