import pickle
from datetime import datetime,timezone
from pathlib import Path

import torch

import const
from load_data import query_influx, DatasetEntry
from model.module import CoverModel
from model.prod import CoverIntelligence
from model.tensor import parse_input_tensor, parse_output_tensor
from model.train import train_epochs,test_model
import sys

if len(sys.argv) == 1 or sys.argv[1] == '--prod':
    cover_ai = CoverIntelligence()


elif '--train' in sys.argv:

    data_dict: dict[datetime, DatasetEntry] = {}
    input_tensor = torch.Tensor()
    output_tensor = torch.Tensor()
    data_file = Path('./data/training_data.pkl')

    if '--fresh' in sys.argv or not data_file.exists():
        print("Pulling fresh training data from InfluxDB")
        start_date = datetime.fromisoformat(const.START_DATE)
        end_date = datetime.fromisoformat(const.END_DATE)

        if '--start' in sys.argv:
            start_date = datetime.fromisoformat(sys.argv[sys.argv.index('--start') + 1])
        if '--end' in sys.argv:
            end_date = datetime.fromisoformat(sys.argv[sys.argv.index('--end') + 1])

        end_date = min(end_date, datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0))
        if start_date > end_date:
            raise Exception(f"Start date must be before end date!")

        data_dict = query_influx(start_date, end_date)

    elif data_file.exists():
        #Load the data file from disk
        with open(data_file, 'rb') as f:
            data_dict = pickle.load(f)

    input_tensor = parse_input_tensor(data_dict)
    output_tensor = parse_output_tensor(data_dict)

    # shuffle the data

    perm = torch.randperm(len(output_tensor))
    input_tensor = input_tensor[perm]
    output_tensor = output_tensor[perm]

    # Separate train from test

    n = len(input_tensor)
    split = int(n * const.TRAIN_TEST_SPLIT)

    x_train = input_tensor[:split]
    x_test = input_tensor[split:]

    y_true_train = output_tensor[:split]
    y_true_test = output_tensor[split:]

    # Train the model
    model = CoverModel(x_train.shape[1], y_true_train.shape[1])
    train_epochs(model, x_train, y_true_train, 5000)


    # Now test the train data.
    loss = test_model(x_test, y_true_test)
    print(f"Loss value for unseen data: {loss}")


