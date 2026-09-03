from typing import TypedDict, TypeVar, Tuple
import torch

input_t = TypeVar("input_t", bound=Tuple[torch.Tensor, torch.Tensor, torch.Tensor])
output_t = TypeVar("output_t", bound=torch.Tensor)


class TestSpec(TypedDict):
    batch_size: int
    num_heads: int
    seq_len: int
    head_dim: int
    seed: int
