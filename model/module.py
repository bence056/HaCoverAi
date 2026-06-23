import torch


class CoverModel(torch.nn.Module):

    def __init__(self, input_size: int, output_size: int):
        super().__init__()


        self.linear_stack = torch.nn.Sequential(
            torch.nn.Linear(input_size, 200),
            torch.nn.ReLU(),
            torch.nn.Linear(200, 50),
            torch.nn.ReLU(),
            torch.nn.Linear(50, output_size)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear_stack(x)