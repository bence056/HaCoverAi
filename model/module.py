import torch

from db.load_data import DatasetEntry


def make_layers(in_features: int, out_features: int) -> torch.nn.Module:
    return torch.nn.Sequential(
        torch.nn.Linear(in_features, 200),
        torch.nn.ReLU(),
        torch.nn.Linear(200, 50),
        torch.nn.ReLU(),
        torch.nn.Linear(50, out_features)
    )


def load_cover_model(path: str) -> CoverModel:
    save_data = torch.load(path)
    model = CoverModel(save_data["in_features"], save_data["out_features"], save_data["data_schema"])
    model.load_state_dict(save_data["state_dict"])
    return model


class CoverModel(torch.nn.Module):

    def __init__(self, input_size: int, output_size: int, data_schema: DatasetEntry):
        super().__init__()

        self.in_features = input_size
        self.out_features = output_size
        self.linear_stack = make_layers(self.in_features, self.out_features)
        self.data_schema = data_schema

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear_stack(x)

    def save_cover_model(self, path: str):
        save_data = {
            "state_dict": self.state_dict(),
            "in_features": self.in_features,
            "out_features": self.out_features,
            "data_schema": self.data_schema
        }
        torch.save(save_data, path)
        print(f"Saved model to {path}")

