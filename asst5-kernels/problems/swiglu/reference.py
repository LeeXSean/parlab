# from utils import verbose_allequal
import torch
from task import input_t, output_t


def ref_kernel(data: input_t) -> output_t:
    """
    Reference implementation of SwiGLU activation function.
    SwiGLU(x, W, V, b, c, beta) = Swish(xW + b) ⊙ (xV + c)
    where Swish(x) = x * sigmoid(beta * x)
    
    Args:
        data: tuple of (x, W, V, b, c, beta, seq) where:
            x: input tensor of shape (batch_size, seq_len, in_features)
            W: weight matrix of shape (in_features, hidden_size)
            V: weight matrix of shape (in_features, hidden_size)
            b: bias vector of shape (hidden_size,)
            c: bias vector of shape (hidden_size,)
            beta: scalar value for Swish activation
    Returns:
        Output tensor of shape (batch_size, seq_len, hidden_size)
    """
    x, W, V, b, c, beta = data
    
    # Compute xW + b
    gate = x @ W + b
    
    # Apply Swish activation: x * sigmoid(beta * x)
    swish_gate = gate * torch.sigmoid(beta * gate)
    
    # Compute xV + c
    value = x @ V + c
    
    # Element-wise multiplication
    return swish_gate * value


def generate_input(batch_size: int, in_features: int, hidden_size: int, seed: int, seq: int = None) -> input_t:
    """
    Generates random input tensors for SwiGLU.

    Args:
        batch_size: Batch size
        in_features: Input feature dimension
        hidden_size: Hidden dimension size
        seed: Random seed
        seq: Optional sequence length. If provided, generates 3D input (B, M, N)
    Returns:
        Tuple of (x, W, V, b, c, beta) tensors
    """
    gen = torch.Generator(device='cuda')
    gen.manual_seed(seed)
    
    precision_dtype = torch.float32

    # Always generate 3D input: (batch_size, seq_len, in_features)
    if seq is None:
        seq = 1  # Default to single token
    x = torch.randn(batch_size, seq, in_features, device='cuda', dtype=precision_dtype, generator=gen)
    
    W = torch.randn(in_features, hidden_size, device='cuda', dtype=precision_dtype, generator=gen)
    V = torch.randn(in_features, hidden_size, device='cuda', dtype=precision_dtype, generator=gen)
    
    W = torch.randn(in_features, hidden_size, device='cuda', dtype=precision_dtype, generator=gen)
    V = torch.randn(in_features, hidden_size, device='cuda', dtype=precision_dtype, generator=gen)
    
    b = torch.randn(hidden_size, device='cuda', dtype=precision_dtype, generator=gen)
    c = torch.randn(hidden_size, device='cuda', dtype=precision_dtype, generator=gen)
    
    beta = 1.0  # Standard beta value

    return (x.contiguous(), W.contiguous(), V.contiguous(), b.contiguous(), c.contiguous(), beta)


def check_implementation(data, output):
    expected = ref_kernel(data)
    ok = torch.allclose(output, expected, rtol=1e-2, atol=1e-2)
    if not ok:
        return False, "mismatch found! custom implementation doesn't match reference"
    return True, ""
