from typing import TypedDict, TypeVar, Tuple
import torch

# Weights dictionary containing all model weights and biases
class ModelWeights(TypedDict):
    # MLPEmbedder (query_in)
    query_in_in_layer_weight: torch.Tensor  # [width, q_in_dim]
    query_in_in_layer_bias: torch.Tensor    # [width]
    query_in_out_layer_weight: torch.Tensor # [width, width]
    query_in_out_layer_bias: torch.Tensor   # [width]
    
    # CrossAttention (attn)
    attn_c_q_weight: torch.Tensor  # [width, width]
    attn_c_q_bias: torch.Tensor    # [width]
    attn_c_k_weight: torch.Tensor  # [width, width]
    attn_c_k_bias: torch.Tensor    # [width]
    attn_c_v_weight: torch.Tensor  # [width, width]
    attn_c_v_bias: torch.Tensor    # [width]
    attn_c_proj_weight: torch.Tensor # [width, width]
    attn_c_proj_bias: torch.Tensor   # [width]
    
    # Output projection
    out_proj_weight: torch.Tensor  # [out_features, width]
    out_proj_bias: torch.Tensor    # [out_features]

# Input type: (queries, latents, weights)
# queries: [batch_size, num_queries, q_in_dim]
# latents: [batch_size, num_latents, width]
# weights: ModelWeights dictionary containing all model weights and biases
input_t = Tuple[torch.Tensor, torch.Tensor, ModelWeights]
output_t = TypeVar("output_t", bound=torch.Tensor)

class TestSpec(TypedDict):
    batch_size: int
    num_queries: int
    num_latents: int
    width: int
    num_heads: int
    q_in_dim: int
    seed: int

