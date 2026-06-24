import datetime

import torch

from db.load_data import DatasetEntry
from db.shutters import ShutterData


def parse_input_tensor(in_dataset: dict[datetime.datetime, DatasetEntry]) -> torch.Tensor:

    batch = []

    for time,data in in_dataset.items():
        vec = []

        # start with datetime
        month_float = float(time.month) / 12.0
        day_of_year = float(time.timetuple().tm_yday) / 366.0
        hour_float = float(time.hour) / 23.0
        vec.append(month_float)
        vec.append(day_of_year)
        vec.append(hour_float)

        for temperature in data.temperature_data.values():
            vec.append(float(temperature.temperature))

        if data.sun_data:
            vec.append(data.sun_data.azimuth / 360.0)
            vec.append(data.sun_data.elevation / 90.0)

        if data.weather_data:
            vec.append(data.weather_data.temperature)
            vec.append(data.weather_data.cloud_coverage)

        if data.person_data:
            for state in data.person_data.person_states.values():
                vec.append(float(1) if state else 0)
            dict_len = len(data.person_data.person_states)
            if dict_len > 0:
                vec.append(float(data.person_data.home_count / len(data.person_data.person_states)))
            else:
                vec.append(0)

        batch.append(vec)

    tensor = torch.tensor(batch, dtype=torch.float32)
    return tensor


def parse_output_tensor(in_dataset: dict[datetime.datetime, DatasetEntry]) -> torch.Tensor:

    batch = []
    for time, data in in_dataset.items():
        vec = []

        for shutter in data.shutter_data.values():
            vec.append(float(shutter.position) / 100.0)
            vec.append(float(shutter.tilt_position) / 100.0)
        batch.append(vec)

    tensor = torch.tensor(batch, dtype=torch.float32)
    return tensor

def convert_from_prediction(prediction: torch.Tensor, data_schema: DatasetEntry) -> list[ShutterData]:
    prediction = prediction.flatten()
    if prediction.size(dim=0) == len(data_schema.shutter_data):
        print("Tensor and shutter size match!")

    pred_shutters: list[ShutterData] = []
    tensor_index = 0
    for shutter in data_schema.shutter_data.values():
        shutter_cpy = ShutterData(
            shutter.entity_id,
            shutter.name,
            int(prediction[tensor_index].item() * 100),
            int(prediction[tensor_index+1].item() * 100)
        )
        pred_shutters.append(shutter_cpy)
        tensor_index += 2

    print("Output shutter prediction:")
    for s in pred_shutters:
        print(f"id: {s.entity_id} - name: {s.name} --- pos: {s.position} - tilt: {s.tilt_position}")

    return pred_shutters


