// flash_attention.cu
// Template for FlashAttention CUDA Kernel Submission

#include <cuda.h>
#include <cuda_runtime.h>
#include <torch/extension.h>

#include <cmath>
#include <vector>

// Constants
#define TILE_SIZE 16

// ------------------------------------------------------------------------
// CUDA Kernel Implementation
// ------------------------------------------------------------------------

template <typename scalar_t>
__global__ void naive_flash_attention_kernel(
    const scalar_t* __restrict__ Q, const scalar_t* __restrict__ K,
    const scalar_t* __restrict__ V, scalar_t* __restrict__ O,
    const int batch_size, const int num_heads, const int seq_len,
    const int head_dim, const float scale) {
  // 1. Calculate Thread Indices
  // We map one block to one row of the Query (one token's attention)
  int bx = blockIdx.x;

  // Map linear block index to (Batch, Head, Token)
  int q_idx = bx;
  int token_idx = q_idx % seq_len;
  int head_idx = (q_idx / seq_len) % num_heads;
  int batch_idx = q_idx / (seq_len * num_heads);

  // 2. Calculate Global Memory Offsets
  // Standard layout: (Batch, Head, Seq, Dim)
  int base_offset = (batch_idx * num_heads * seq_len * head_dim) +
                    (head_idx * seq_len * head_dim);

  // Pointers to the specific row/vector for this thread
  const scalar_t* q_vec = Q + base_offset + (token_idx * head_dim);
  scalar_t* o_vec = O + base_offset + (token_idx * head_dim);

  // 3. Online Softmax State (Keep in float32 for numerical stability)
  float m_i = -INFINITY;  // Running max
  float l_i = 0.0f;       // Running sum of exponentials

  // Temporary Output Accumulator (in float32)
  // Since we can't dynamically allocate registers, we reuse the global output
  // buffer for storage, but we must be careful to read/write it as we go.
  // For this implementation, we simply assume we can overwrite O_vec.
  // Initialize Output to 0
  for (int d = 0; d < head_dim; ++d) {
    o_vec[d] = static_cast<scalar_t>(0.0f);
  }

  // 4. Iterate over Key/Value Blocks (Tiling)
  for (int j_block = 0; j_block < seq_len; j_block += TILE_SIZE) {
    // Handle edge case for last tile
    int valid_tile_size = min(TILE_SIZE, seq_len - j_block);

    // Process Tile
    for (int j = 0; j < valid_tile_size; ++j) {
      int k_idx = j_block + j;
      const scalar_t* k_vec = K + base_offset + (k_idx * head_dim);
      const scalar_t* v_vec = V + base_offset + (k_idx * head_dim);

      // A. Compute Dot Product: Q_i . K_j
      float score = 0.0f;
      for (int d = 0; d < head_dim; ++d) {
        // Cast to float for accumulation precision
        score += static_cast<float>(q_vec[d]) * static_cast<float>(k_vec[d]);
      }
      score *= scale;

      // B. Online Softmax Updates
      float m_prev = m_i;
      m_i = fmaxf(m_i, score);

      float alpha = expf(m_prev - m_i);
      float beta = expf(score - m_i);

      l_i = (l_i * alpha) + beta;

      // C. Update Output Accumulator
      // O_new = (O_old * alpha) + (V_j * beta)
      for (int d = 0; d < head_dim; ++d) {
        float o_val = static_cast<float>(o_vec[d]);
        float v_val = static_cast<float>(v_vec[d]);

        o_val = o_val * alpha + v_val * beta;

        o_vec[d] = static_cast<scalar_t>(o_val);
      }
    }
  }

  // 5. Final Normalization
  // O_final = O_acc / l_i
  for (int d = 0; d < head_dim; ++d) {
    float o_val = static_cast<float>(o_vec[d]);
    o_vec[d] = static_cast<scalar_t>(o_val / l_i);
  }
}

// ------------------------------------------------------------------------
// C++ / Python Interface
// ------------------------------------------------------------------------

// Required: Main function that will be called from Python
torch::Tensor flash_attention_forward(torch::Tensor Q, torch::Tensor K,
                                      torch::Tensor V) {
  // 1. Setup Output Tensor
  auto O = torch::empty_like(Q);

  // 2. Extract Dimensions
  const int batch_size = Q.size(0);
  const int num_heads = Q.size(1);
  const int seq_len = Q.size(2);
  const int head_dim = Q.size(3);
  const float scale = 1.0f / sqrtf(head_dim);

  // 3. Configure Kernel Launch Parameters
  // Grid: One block per query token (Total threads = B * H * L)
  // Block: 1 thread (This is a simplified naive kernel)
  int total_threads = batch_size * num_heads * seq_len;
  dim3 blocks(total_threads);
  dim3 threads(1);

  // 4. Dispatch and Launch
  AT_DISPATCH_FLOATING_TYPES_AND_HALF(
      Q.scalar_type(), "naive_flash_attention_kernel", ([&] {
        naive_flash_attention_kernel<scalar_t><<<blocks, threads>>>(
            Q.data_ptr<scalar_t>(), K.data_ptr<scalar_t>(),
            V.data_ptr<scalar_t>(), O.data_ptr<scalar_t>(), batch_size,
            num_heads, seq_len, head_dim, scale);
      }));

  // 5. Check for kernel launch errors
  cudaError_t err = cudaGetLastError();
  if (err != cudaSuccess) {
    throw std::runtime_error(cudaGetErrorString(err));
  }

  // 6. Synchronize to ensure kernel completion
  // (Optional for standard PyTorch usage as generic stream syncs automatically,
  // but good for strict benchmarking boundaries)
  cudaDeviceSynchronize();

  return O;
}