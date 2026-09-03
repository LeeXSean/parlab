import torch
import triton
import triton.language as tl
from task import input_t, output_t


@triton.jit
def flash_attention_kernel(
    # Pointers to matrices
    Q_ptr, K_ptr, V_ptr, O_ptr,
    # Matrix dimensions
    batch_size, num_heads, seq_len, head_dim,
    # Scaling factor
    scale,
    # Strides for tensor access
    stride_qb, stride_qh, stride_qs, stride_qd,
    stride_kb, stride_kh, stride_ks, stride_kd,
    stride_vb, stride_vh, stride_vs, stride_vd,
    stride_ob, stride_oh, stride_os, stride_od,
    # Block sizes
    BLOCK_SIZE_M: tl.constexpr,  # Number of queries per block
    BLOCK_SIZE_N: tl.constexpr,  # Number of keys/values per block
    BLOCK_SIZE_D: tl.constexpr,  # Head dimension block size
):
    """
    Triton implementation of FlashAttention with online softmax.

    This kernel processes attention in blocks to minimize HBM accesses,
    using online softmax to avoid materializing the full attention matrix.
    """
    # TODO: Your implementation goes here.
    pass

def flash_attention_forward(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Triton-based FlashAttention implementation.

    Args:
        Q: Query tensor of shape (batch_size, num_heads, seq_len, head_dim)
        K: Key tensor of shape (batch_size, num_heads, seq_len, head_dim)
        V: Value tensor of shape (batch_size, num_heads, seq_len, head_dim)

    Returns:
        Output tensor of shape (batch_size, num_heads, seq_len, head_dim)
    """
    # Ensure inputs are on CUDA and in FP16
    Q = Q.contiguous().cuda().half()
    K = K.contiguous().cuda().half()
    V = V.contiguous().cuda().half()

    # Extract dimensions
    batch_size, num_heads, seq_len, head_dim = Q.shape
    scale = 1.0 / (head_dim ** 0.5)

    # Create output tensor
    O = torch.empty_like(Q)

    # Define block sizes for tiling
    # These can be tuned for optimal performance
    BLOCK_SIZE_M = 64  # Number of queries per block (must be power of 2)
    BLOCK_SIZE_N = 64  # Number of keys/values per block (must be power of 2)
    BLOCK_SIZE_D = min(128, head_dim)  # Head dimension block size

    # Calculate grid dimensions
    grid = (
        batch_size,      # batch dimension
        num_heads,       # head dimension
        triton.cdiv(seq_len, BLOCK_SIZE_M),  # query sequence dimension
    )

    # Launch kernel
    flash_attention_kernel[grid](
        Q_ptr=Q, K_ptr=K, V_ptr=V, O_ptr=O,
        batch_size=batch_size, num_heads=num_heads,
        seq_len=seq_len, head_dim=head_dim,
        scale=scale,
        stride_qb=Q.stride(0), stride_qh=Q.stride(1),
        stride_qs=Q.stride(2), stride_qd=Q.stride(3),
        stride_kb=K.stride(0), stride_kh=K.stride(1),
        stride_ks=K.stride(2), stride_kd=K.stride(3),
        stride_vb=V.stride(0), stride_vh=V.stride(1),
        stride_vs=V.stride(2), stride_vd=V.stride(3),
        stride_ob=O.stride(0), stride_oh=O.stride(1),
        stride_os=O.stride(2), stride_od=O.stride(3),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_D=BLOCK_SIZE_D,
    )

    return O


def custom_kernel(data: input_t) -> output_t:
    """
    Wrapper function for FlashAttention using Triton implementation.

    Args:
        data: tuple of (Q, K, V) tensors
            Q: (batch_size, num_heads, seq_len, head_dim)
            K: (batch_size, num_heads, seq_len, head_dim)
            V: (batch_size, num_heads, seq_len, head_dim)

    Returns:
        Output tensor of shape (batch_size, num_heads, seq_len, head_dim)
    """
    q, k, v = data
    return flash_attention_forward(q, k, v)
