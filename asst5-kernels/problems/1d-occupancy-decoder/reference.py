import math
import torch
from task import input_t, output_t, ModelWeights
from model import OneDOccupancyDecoder


def ref_kernel(data: input_t) -> output_t:
    """
    Reference implementation of OneDOccupancyDecoder.
    
    Args:
        data: tuple of (queries, latents, weights) where:
            queries: input tensor of shape (batch_size, num_queries, q_in_dim)
            latents: input tensor of shape (batch_size, num_latents, width)
            weights: ModelWeights dictionary containing all model weights and biases
    Returns:
        Output tensor of shape (batch_size, num_queries, 1)
    """
    queries, latents, weights = data
    
    model = OneDOccupancyDecoder(
        q_in_dim=queries.shape[-1],
        width=latents.shape[-1],
        num_heads=12,
        out_features=1,
    ).to(queries.device, dtype=queries.dtype)
    
    # Load weights into the model
    model.query_in.in_layer.weight.data.copy_(weights['query_in_in_layer_weight'])
    model.query_in.in_layer.bias.data.copy_(weights['query_in_in_layer_bias'])
    model.query_in.out_layer.weight.data.copy_(weights['query_in_out_layer_weight'])
    model.query_in.out_layer.bias.data.copy_(weights['query_in_out_layer_bias'])
    
    model.attn.c_q.weight.data.copy_(weights['attn_c_q_weight'])
    model.attn.c_q.bias.data.copy_(weights['attn_c_q_bias'])
    model.attn.c_k.weight.data.copy_(weights['attn_c_k_weight'])
    model.attn.c_k.bias.data.copy_(weights['attn_c_k_bias'])
    model.attn.c_v.weight.data.copy_(weights['attn_c_v_weight'])
    model.attn.c_v.bias.data.copy_(weights['attn_c_v_bias'])
    model.attn.c_proj.weight.data.copy_(weights['attn_c_proj_weight'])
    model.attn.c_proj.bias.data.copy_(weights['attn_c_proj_bias'])
    
    model.out_proj.weight.data.copy_(weights['out_proj_weight'])
    model.out_proj.bias.data.copy_(weights['out_proj_bias'])
    
    model.eval()
    with torch.no_grad():
        output = model(queries, latents)
    
    return output


def generate_input(
    batch_size: int,
    num_queries: int,
    num_latents: int,
    width: int,
    num_heads: int,
    q_in_dim: int,
    seed: int,
) -> input_t:
    """
    Generates random input tensors for OneDOccupancyDecoder.

    Args:
        batch_size: Batch size
        num_queries: Number of query tokens
        num_latents: Number of latent tokens
        width: Embedding dimension
        q_in_dim: Query input dimension
        seed: Random seed
    Returns:
        Tuple of (queries, latents, weights) where weights is a ModelWeights dictionary
    """
    gen = torch.Generator(device='cuda')
    gen.manual_seed(seed)
    
    precision_dtype = torch.float16
    
    queries = torch.randn(
        batch_size, num_queries, q_in_dim,
        device='cuda', dtype=precision_dtype, generator=gen
    ).contiguous()
    
    latents = torch.randn(
        batch_size, num_latents, width,
        device='cuda', dtype=precision_dtype, generator=gen
    ).contiguous()
    
    # Create model to extract weights
    # Use a separate seed for model weights to ensure reproducibility
    # Set PyTorch's global generator for model initialization
    torch.manual_seed(seed + 1000)
    
    model = OneDOccupancyDecoder(
        q_in_dim=q_in_dim,
        width=width,
        num_heads=num_heads,
        out_features=1,
    ).to('cuda', dtype=precision_dtype)
    
    # Model initialization happens in __init__:
    # - MLPEmbedder uses init_linear (normal init for weights, zeros for bias)
    # - CrossAttention and out_proj use default PyTorch initialization (Kaiming uniform)
    # The seed ensures reproducibility
    # We convert to float16 to match the input dtype
    
    # Extract weights into dictionary
    weights: ModelWeights = {
        'query_in_in_layer_weight': model.query_in.in_layer.weight.data.clone().contiguous(),
        'query_in_in_layer_bias': model.query_in.in_layer.bias.data.clone().contiguous(),
        'query_in_out_layer_weight': model.query_in.out_layer.weight.data.clone().contiguous(),
        'query_in_out_layer_bias': model.query_in.out_layer.bias.data.clone().contiguous(),
        'attn_c_q_weight': model.attn.c_q.weight.data.clone().contiguous(),
        'attn_c_q_bias': model.attn.c_q.bias.data.clone().contiguous(),
        'attn_c_k_weight': model.attn.c_k.weight.data.clone().contiguous(),
        'attn_c_k_bias': model.attn.c_k.bias.data.clone().contiguous(),
        'attn_c_v_weight': model.attn.c_v.weight.data.clone().contiguous(),
        'attn_c_v_bias': model.attn.c_v.bias.data.clone().contiguous(),
        'attn_c_proj_weight': model.attn.c_proj.weight.data.clone().contiguous(),
        'attn_c_proj_bias': model.attn.c_proj.bias.data.clone().contiguous(),
        'out_proj_weight': model.out_proj.weight.data.clone().contiguous(),
        'out_proj_bias': model.out_proj.bias.data.clone().contiguous(),
    }
    
    return (queries, latents, weights)


def check_implementation(data: input_t, output: output_t) -> tuple[bool, str]:
    expected = ref_kernel(data)
    ok = torch.allclose(output, expected, rtol=1e-2, atol=1e-2)
    if not ok:
        return False, f"mismatch found! custom implementation doesn't match reference"
    return True, ""

