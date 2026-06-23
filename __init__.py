from load_data import query_influx
from model.tensor import parse_input_tensor

data_dict = query_influx()
parse_input_tensor(data_dict)
