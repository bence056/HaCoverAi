import torch


def train_epochs(model: torch.nn.Module, x: torch.Tensor, y_true: torch.Tensor, epochs: int):

    optimizer = torch.optim.Adam(model.parameters())
    loss_fn = torch.nn.MSELoss()

    for epoch in range(epochs):
        y_hat = model(x)
        loss = loss_fn(y_hat, y_true)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            print(f"Epoch: {epoch:02d}, Loss: {loss.item():.4f}")