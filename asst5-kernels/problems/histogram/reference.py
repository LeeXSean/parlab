from utils import make_match_reference
import torch
from task import input_t, output_t

def ref_kernel(data: input_t) -> output_t:
    """
    Args:
        data:
            Tuple of (array, num_bins) where:
                array:    Tensor of shape [length, num_channels], containing integer
                          values in the range [0, num_bins - 1]
                num_bins: Number of histogram bins (defines allowed value range)
        output_dtype: Data type for the output histogram tensor (default: torch.int32)

    Returns:
        histogram:
            Tensor of shape [num_channels, num_bins], where histogram[c][b]
            contains the count of how many times value b appears in channel c.
    """

    array, num_bins = data

    output_dtype = torch.int32

    length, num_channels = array.shape
    histogram = torch.zeros(num_channels, num_bins, dtype=output_dtype, device=array.device)
    
    # Compute histogram for each channel
    for c in range(num_channels):
        channel_data = array[:, c]
        hist = torch.bincount(channel_data, minlength=num_bins)
        histogram[c] = hist[:num_bins]
    
    return histogram

def generate_input(length: int, num_channels: int, num_bins: int, seed: int) -> input_t:
    """
    Generates random input array with specified dimensions and value range.

    Args:
        length:       Number of elements in the first dimension
        num_channels: Number of channels in the second dimension
        num_bins:     Maximum value range (values will be in [0, num_bins-1])
        seed:         Random seed for reproducibility

    Returns:
        Tuple of (array, num_bins) where:
            array:    Tensor of shape [length, num_channels] with integer values in [0, num_bins-1]
            num_bins: The number of bins (same as input parameter)
    """

    gen = torch.Generator(device="cuda")
    gen.manual_seed(seed)

    input_dtype = torch.uint8

    # Generate random integers in range [0, num_bins-1]
    array = torch.randint(
        low=0,
        high=num_bins,
        size=(length, num_channels),
        generator=gen,
        device="cuda",
        dtype=input_dtype
    ).contiguous()

    return (array, num_bins)

check_implementation = make_match_reference(ref_kernel, rtol=1e-3, atol=1e-3)