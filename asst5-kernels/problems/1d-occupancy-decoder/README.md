# 1D Occupancy Decoder Cross-Attention

The model definitions are in `model.py`.

### 1. Why This Problem Matters
- **Production-relevant context**: This decoder mirrors the module and input sizes used in [Roblox’s open source Cube3D generative model for 3D meshes](https://github.com/Roblox/cube), where dense grids of 3D queries reconstruct occupancy fields from compact latent codes. 
- **Forward-pass structure**: The pipeline embeds raw query coordinates, attends over latent features, normalizes, and produces occupancy logits.
- **Sequence-length imbalance**: Queries (`250,000 × 768`) vastly outnumber latent keys/values (`1,024 × 768`). By contrast, vanilla FlashAttention benchmarks usually feature roughly balanced or moderately skewed lengths (e.g., 2k × 2k or 4k × 1k).

### 2. Shape Accounting and Call Graph
- **Queries**: `[B, 250k, 3]` → `MLPEmbedder` → `[B, 250k, 768]`
- **Latents**: `[B, 1024, 768]`
- **Cross-attention**: `queries × latents → [B, 250k, 768]`
- **LayerNorm + output projection**: `[B, 250k, 768] → [B, 250k, 1]`

### 2.1. Interface Specification

Your implementation must match the following interface:

**Input Type (`input_t`):**
```python
input_t = Tuple[torch.Tensor, torch.Tensor, ModelWeights]
```

The input is a tuple containing:
1. **`queries`**: `torch.Tensor` of shape `[batch_size, num_queries, q_in_dim]`
   - Input query coordinates (typically `q_in_dim=3` for 3D coordinates)
   
2. **`latents`**: `torch.Tensor` of shape `[batch_size, num_latents, width]`
   - Latent feature vectors that queries attend to
   
3. **`weights`**: `ModelWeights` dictionary containing all model weights and biases:
   - **MLPEmbedder (query_in)**:
     - `query_in_in_layer_weight`: `[width, q_in_dim]` - First linear layer weight
     - `query_in_in_layer_bias`: `[width]` - First linear layer bias
     - `query_in_out_layer_weight`: `[width, width]` - Second linear layer weight
     - `query_in_out_layer_bias`: `[width]` - Second linear layer bias
   - **CrossAttention (attn)**:
     - `attn_c_q_weight`: `[width, width]` - Query projection weight
     - `attn_c_q_bias`: `[width]` - Query projection bias
     - `attn_c_k_weight`: `[width, width]` - Key projection weight
     - `attn_c_k_bias`: `[width]` - Key projection bias
     - `attn_c_v_weight`: `[width, width]` - Value projection weight
     - `attn_c_v_bias`: `[width]` - Value projection bias
     - `attn_c_proj_weight`: `[width, width]` - Output projection weight
     - `attn_c_proj_bias`: `[width]` - Output projection bias
   - **Output Projection**:
     - `out_proj_weight`: `[out_features, width]` - Final linear layer weight (typically `[1, width]`)
     - `out_proj_bias`: `[out_features]` - Final linear layer bias (typically `[1]`)

**Output Type (`output_t`):**
```python
output_t = torch.Tensor  # Shape: [batch_size, num_queries, 1]
```

**Function Signature:**

For Python/Triton submissions:
```python
def custom_kernel(data: input_t) -> output_t:
    """
    Your implementation of the OneDOccupancyDecoder forward pass.
    
    Args:
        data: Tuple of (queries, latents, weights)
        
    Returns:
        Output tensor of shape [batch_size, num_queries, 1]
    """
    queries, latents, weights = data
    # Your implementation here
    return output
```

For CUDA submissions (`.cu` file):
If you submit CUDA code, the `wrap_submission.py` will automatically unpack the weights dictionary and pass all 14 weight/bias tensors as separate arguments. Your `custom_kernel` function signature must be:
```cpp
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
);
```

**Important Notes:**

**Precision Requirements (CRITICAL):**
- **All tensors (inputs, weights, biases, and intermediate computations) use `float16` (half precision)**
- **Exception: Softmax operations in attention must be computed in `float32` for numerical stability**
  - Compute attention scores in float16, but convert to float32 before softmax
  - Perform softmax in float32, then convert result back to float16
  - This matches the behavior of PyTorch's `scaled_dot_product_attention` which uses float32 for softmax internally
- All tensors are on CUDA device

**Other Requirements:**
- All weight and bias tensors are provided in the input - you should not initialize or create new model weights
- The LayerNorm layer has `elementwise_affine=False`, so it has no learnable parameters (only normalization)
- Your implementation must produce the same output as the reference implementation for correctness

### 3. Some References
- FlashAttention paper: https://arxiv.org/abs/2205.14135
- Blog + implementation overview: https://tridao.me/blog/2024/flash3/
- Triton: https://triton-lang.org/main/getting-started/tutorials/index.html

### 4. Hardware Context (H100 Reference)
- NVIDIA H100 Tensor Core overview: https://resources.nvidia.com/en-us-tensor-core/nvidia-hopper-architecture
- Even if Triton abstracts away many of these details, understanding tensor cores and TMA will help you reason about ideal data layouts, MMA shapes, and pipelining opportunities.

### 5. CA’s Baseline and Triton Attempts
All measurements use batch size 1, `250k` queries, `1024` latents, `12` heads, width `768` on an H100.

| Variant | Time (ms) | Speedup vs PyTorch |
| --- | --- | --- |
| PyTorch MLPEmbedder + PyTorch CrossAttention | `7.399 ± 0.003` | `1.00×` |
| Triton MLPEmbedder + Triton CrossAttention (no fusion) | `9.158 ± 0.005` | `0.81×` (19% slower) |
| Triton MLPEmbedder + PyTorch CrossAttention | `7.277 ± 0.080` | `1.02×` (2% faster) |

The cross-attention Triton port took ~5–6 hours.
