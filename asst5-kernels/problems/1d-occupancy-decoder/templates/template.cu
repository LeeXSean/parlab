// Template for OneDOccupancyDecoder CUDA Kernel Submission
//
// This file shows the expected signature for your CUDA implementation.
// You must implement the kernel_body and custom_kernel functions below.

#include <torch/extension.h>
#include <cuda_runtime.h>

// TODO: Implement your CUDA kernel here
// Example kernel signature (you can modify as needed):
// Note: You'll need to pass all weight and bias tensors to your kernel
template <typename scalar_t>
__global__ void kernel_body(
    const scalar_t* __restrict__ queries,
    const scalar_t* __restrict__ latents,
    const scalar_t* __restrict__ query_in_in_layer_weight,
    const scalar_t* __restrict__ query_in_in_layer_bias,
    const scalar_t* __restrict__ query_in_out_layer_weight,
    const scalar_t* __restrict__ query_in_out_layer_bias,
    const scalar_t* __restrict__ attn_c_q_weight,
    const scalar_t* __restrict__ attn_c_q_bias,
    const scalar_t* __restrict__ attn_c_k_weight,
    const scalar_t* __restrict__ attn_c_k_bias,
    const scalar_t* __restrict__ attn_c_v_weight,
    const scalar_t* __restrict__ attn_c_v_bias,
    const scalar_t* __restrict__ attn_c_proj_weight,
    const scalar_t* __restrict__ attn_c_proj_bias,
    const scalar_t* __restrict__ out_proj_weight,
    const scalar_t* __restrict__ out_proj_bias,
    scalar_t* __restrict__ output,
    int64_t batch_size,
    int64_t num_queries,
    int64_t num_latents,
    int64_t q_in_dim,
    int64_t width
) {
    // TODO: Your CUDA kernel implementation
    // 
    // The forward pass should:
    // 1. Project queries through MLP with SiLU: [B, num_queries, q_in_dim] -> [B, num_queries, width]
    //    - Use query_in_in_layer_weight/bias and query_in_out_layer_weight/bias
    // 2. Cross-attention: [B, num_queries, width] attends to [B, num_latents, width]
    //    - Use attn_c_q/k/v/proj weights and biases
    // 3. LayerNorm + output projection: [B, num_queries, width] -> [B, num_queries, 1]
    //    - Use out_proj_weight/bias (LayerNorm has no learnable parameters)
}

// Required: Main function that will be called from Python
// Signature must match the updated input_t format with all weights
torch::Tensor custom_kernel(
    torch::Tensor queries,
    torch::Tensor latents,
    torch::Tensor query_in_in_layer_weight,
    torch::Tensor query_in_in_layer_bias,
    torch::Tensor query_in_out_layer_weight,
    torch::Tensor query_in_out_layer_bias,
    torch::Tensor attn_c_q_weight,
    torch::Tensor attn_c_q_bias,
    torch::Tensor attn_c_k_weight,
    torch::Tensor attn_c_k_bias,
    torch::Tensor attn_c_v_weight,
    torch::Tensor attn_c_v_bias,
    torch::Tensor attn_c_proj_weight,
    torch::Tensor attn_c_proj_bias,
    torch::Tensor out_proj_weight,
    torch::Tensor out_proj_bias
) {
    auto batch_size = queries.size(0);
    auto num_queries = queries.size(1);
    auto q_in_dim = queries.size(2);
    auto num_latents = latents.size(1);
    auto width = latents.size(2);
    
    auto output = torch::empty({batch_size, num_queries, 1}, queries.options());

    // TODO: Configure your kernel launch parameters
    int blocks = 1;
    int threads = 256;

    
    AT_DISPATCH_FLOATING_TYPES_AND_HALF(queries.scalar_type(), "kernel_body", ([&] {
        kernel_body<scalar_t><<<blocks, threads>>>(
            queries.data_ptr<scalar_t>(),
            latents.data_ptr<scalar_t>(),
            query_in_in_layer_weight.data_ptr<scalar_t>(),
            query_in_in_layer_bias.data_ptr<scalar_t>(),
            query_in_out_layer_weight.data_ptr<scalar_t>(),
            query_in_out_layer_bias.data_ptr<scalar_t>(),
            attn_c_q_weight.data_ptr<scalar_t>(),
            attn_c_q_bias.data_ptr<scalar_t>(),
            attn_c_k_weight.data_ptr<scalar_t>(),
            attn_c_k_bias.data_ptr<scalar_t>(),
            attn_c_v_weight.data_ptr<scalar_t>(),
            attn_c_v_bias.data_ptr<scalar_t>(),
            attn_c_proj_weight.data_ptr<scalar_t>(),
            attn_c_proj_bias.data_ptr<scalar_t>(),
            out_proj_weight.data_ptr<scalar_t>(),
            out_proj_bias.data_ptr<scalar_t>(),
            output.data_ptr<scalar_t>(),
            batch_size,
            num_queries,
            num_latents,
            q_in_dim,
            width
        );
    }));

    //

    
    // Check for kernel launch errors
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        throw std::runtime_error(cudaGetErrorString(err));
    }
    
    // Synchronize to ensure kernel completion
    cudaDeviceSynchronize();
    
    return output;
}
