from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
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
    pass
