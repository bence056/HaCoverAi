import datetime

import torch

from db.load_data import DatasetEntry


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