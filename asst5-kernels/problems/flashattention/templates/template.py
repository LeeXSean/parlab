import torch.nn.functional as F

from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Reference implementation of Scaled Dot Product Attention.
    Attention(Q, K, V) = softmax(QK^T / sqrt(d)) V

    Args:
        data: tuple of (Q, K, V)
            Q: (batch_size, num_heads, seq_len, head_dim)
            K: (batch_size, num_heads, seq_len, head_dim)
            V: (batch_size, num_heads, seq_len, head_dim)
    Returns:
        Output tensor of shape (batch_size, num_heads, seq_len, head_dim)
    """
    q, k, v = data
    output = F.scaled_dot_product_attention(q, k, v)
    return output
