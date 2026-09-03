from typing import TypedDict, TypeVar, Tuple
import torch

input_t = TypeVar( "input_t", bound=Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, float])
output_t = TypeVar("output_t", bound=torch.Tensor)

class TestSpec(TypedDict):
    batch_size: int
    in_features: int
    hidden_size: int
    seed: int
    seq_len: int