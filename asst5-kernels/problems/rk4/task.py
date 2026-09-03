from typing import TypedDict, TypeVar, Tuple
import torch

input_t = TypeVar( "input_t", bound=Tuple[torch.Tensor, float, float, float, float, int])
output_t = TypeVar("output_t", bound=torch.Tensor)


class TestSpec(TypedDict):
    grid_size: int
    n_steps: int
    seed: int
