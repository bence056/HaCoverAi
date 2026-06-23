from load_data import query_influx
from model.module import CoverModel
from model.tensor import parse_input_tensor, parse_output_tensor
from model.train import train_epochs

data_dict = query_influx()
x = parse_input_tensor(data_dict)
y_true = parse_output_tensor(data_dict)

model = CoverModel(x.shape[1], y_true.shape[1])
train_epochs(model, x, y_true, 5000)

print(model.linear_stack[0].weight)