from pathlib import Path

import torch
from torch.distributed.checkpoint import state_dict

import util.const as const
from model.module import CoverModel, load_cover_model


def train_epochs(model: CoverModel, x: torch.Tensor, y_true: torch.Tensor, epochs: int):

    optimizer = torch.optim.Adam(model.parameters(), lr=const.LEARN_RATE)
    loss_fn = torch.nn.MSELoss()

    for epoch in range(epochs):
        y_hat = model(x)
        loss = loss_fn(y_hat, y_true)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            print(f"Epoch: {epoch:02d}, Loss: {loss.item():.4f}")

    model.save_cover_model(const.MODEL_SAVE_PATH)


def test_model(x_test: torch.Tensor, y_true_test: torch.Tensor) -> float:

    file = Path(const.MODEL_SAVE_PATH)
    if not file.exists():
        raise FileNotFoundError(f"File {file} not found. Did you forget to train the model?")

    prod_model = load_cover_model(str(file))

    with torch.no_grad():
        y_pred = prod_model(x_test)

        loss_fn = torch.nn.MSELoss()
        loss = loss_fn(y_pred, y_true_test)
        return loss.item()