from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
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
    pass
