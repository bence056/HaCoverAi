from pathlib import Path

import torch

import const
from model.module import CoverModel


def train_epochs(model: torch.nn.Module, x: torch.Tensor, y_true: torch.Tensor, epochs: int):

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

    torch.save(model.state_dict(), './data/model.pt')
    print(f"Saved model to ./data/model.pt")


def test_model(x_test: torch.Tensor, y_true_test: torch.Tensor) -> float:

    file = Path("./data/model.pt")
    if not file.exists():
        raise FileNotFoundError(f"File {file} not found. Did you forget to train the model?")

    prod_model = CoverModel(x_test.shape[1], y_true_test.shape[1])
    prod_model.load_state_dict(torch.load('./data/model.pt'))
    prod_model.eval()

    with torch.no_grad():
        y_pred = prod_model(x_test)

        loss_fn = torch.nn.MSELoss()
        loss = loss_fn(y_pred, y_true_test)
        return loss.item()