# Implementing FlashAttention

## 1. Why This Problem Matters
Standard self-attention scales poorly with sequence length, creating a major bottleneck for modern large language models (LLMs).* **The Complexity Problem:** Standard attention has $O(N^2)$ compute and memory complexity.
* **The Memory Wall Problem:** Modern GPUs such as H100 have massive compute power but relatively limited memory bandwidth. Standard attention is **memory-bound**; it can spend more time moving data between High Bandwidth Memory (HBM) and on-chip SRAM than actually computing.

FlashAttention addresses these challenges by being I/O-aware. It minimizes HBM accesses by keeping data resident in fast on-chip SRAM, improving data locality, keeping compute units busy, and delivering substantially higher performance.

## 2. High-Level Idea of FlashAttention
FlashAttention avoids materializing the full attention matrix by computing the output block by block entirely within the GPU’s limited on-chip SRAM.

### Key Concepts
1.  **Tiling:** Loads small blocks of $Q$, $K$, and $V$ from HBM into SRAM and computes partial attention results locally.
2.  **Fusion:** Instead of writing the full $N \times N$ attention matrix to HBM and reading it back, FlashAttention fuses multiple operations directly inside a single kernel.
3.  **Online Softmax:** Uses running statistics (row-wise maximum and cumulative sum) to normalize softmax scores incrementally across blocks, without requiring the full row to be in memory at once.

**Recommend Reading:**
> **FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness** --*Tri Dao et al.*
> [Read the Paper on arXiv](https://arxiv.org/abs/2205.14135)

> [From Online Softmax to FlashAttention](https://courses.cs.washington.edu/courses/cse599m/23sp/notes/flashattn.pdf) (UW lecture notes by the author of [FlashInfer](https://github.com/flashinfer-ai/flashinfer))


## 3. Input/Output and Testing Strategy
You will implement a CUDA kernel or use a DSL of your choice (exposed through a PyTorch extension) with the following interface.

### Arguments

Your function should accept the following tensors (assumed to be in FP16 format):

* **`Q` (Query):** Shape $(B, N, S, D)$
* **`K` (Key):** Shape $(B, N, S, D)$
* **`V` (Value):** Shape $(B, N, S, D)$

**Where:**
* $B$: Batch size
* $N$: Number of heads
* $S$: Sequence Length
* $D$: Head dimension

**Output:**
* **`O` (Output):** Shape $(B, N, S, D)$
    * This should be the result of $\text{softmax}\left(\frac{Q K^T}{\sqrt{D}}\right)V$.

### Testing Protocol
We provide three input shapes in `test_cases/test.txt``. We recommend using the smaller cases for correctness testing, while only the largest case will be used on the remote server for benchmarking and profiling (you may encounter out-of-memory errors locally with the largest configuration).

## 4. Performance Reference
Below are performance numbers for your reference. You should also consult the leaderboard to see the best efforts from your classmates.

| Configuration $(B, N, H, D)$ | Implementation | Latency (ms) | Speedup vs. Baseline |
| :--- | :--- | :--- | :--- |
| **Small** $(1, 64, 1024, 128)$ (on RTX 5090) | PyTorch (Reference) | 0.61 | 1.0x |
| | **PyTorch (FlashAttention)** | **0.23** | **2.6x** |
| **Medium** $(2, 64, 4096, 128)$ (on RTX 5090) | PyTorch (Reference) | 24.7 | 1.0x |
| | **PyTorch (FlashAttention)** | **6.3** | **3.9x** |
| **Large** $(4, 64, 8192, 128)$ (on H100) | PyTorch (Reference) | 127 | 1.0x |
| | **PyTorch (FlashAttention)** | **28** | **4.5x** |