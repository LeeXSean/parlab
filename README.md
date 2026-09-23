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

[Read the lab notes](https://leexsean.github.io/parlab/).
Assignment 1's required work is complete; later assignments are pending.

The notes use MkDocs with dependencies in `requirements-docs.txt`.
Run `python3 -m mkdocs serve` to preview them, or
`python3 -m mkdocs build --strict` to validate the site.
Documentation changes pushed to `main` trigger GitHub Actions to build the site
and update `gh-pages`, which GitHub Pages serves.

- `asst1` adds missing standard C++ headers.
- `asst3` uses `-arch=native`; rebuild when moving to a different GPU.
- Local environments and generated KMeans data, logs, and plots stay untracked.

## Local Python (this Ubuntu host)

Python dependencies are installed in the user site for `/usr/bin/python3`.
Use `python3` for all assignment scripts; no `.venv` activation is needed.
For additional packages, use
`python3 -m pip install --user --break-system-packages <package>`.
Keep OS-managed packages under `apt`; do not use `sudo pip`.

Unofficial and unaffiliated with either course. Enrolled students should use the
official starters linked above and follow their course's academic-integrity policy.
