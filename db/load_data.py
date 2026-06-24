import datetime
import pickle

import influxdb_client

import util.const as const
from db.person import query_person, PersonData
from db.shutters import query_shutters, ShutterData
from db.sun import query_sun, SunData
from db.temperature import query_temps, TemperatureData
from db.weather import query_weather, WeatherData


class DatasetEntry:

    shutter_data: dict[str, ShutterData]
    temperature_data: dict[str, TemperatureData]
    sun_data: SunData | None
    weather_data: WeatherData | None
    person_data: PersonData | None
    data_validity: bool = False

    def __init__(self):
        self.shutter_data = {}
        self.temperature_data = {}
        self.sun_data = None
        self.weather_data = None
        self.person_data: PersonData = PersonData()
        self.data_validity = True

    def invalidate(self):
        self.data_validity = False

    def get_entity_id_list(self) -> list[str]:
        ids: list[str] = []
        ids.extend(self.shutter_data.keys())
        ids.extend(self.temperature_data.keys())
        if self.sun_data:
            ids.append(self.sun_data.entity_id)
        if self.weather_data:
            ids.append(self.weather_data.entity_id)
        ids.extend(self.person_data.person_states.keys())
        return ids


def query_influx(start_date, end_date) -> dict[datetime.datetime, DatasetEntry]:

    db_client = influxdb_client.InfluxDBClient(url=const.URL, token=const.INFLUXDB_TOKEN, org=const.ORG)

    connected = db_client.ping()
    print(f"Connected: {connected}")
    if connected:
        print(f"Version: {db_client.version()}")

    shutter_tables = query_shutters(db_client, start_date, end_date)
    temperature_tables = query_temps(db_client, start_date, end_date)
    sun_tables = query_sun(db_client, start_date, end_date)
    weather_tables = query_weather(db_client, start_date, end_date)
    person_tables = query_person(db_client, start_date, end_date)


    dataset_dict: dict[datetime.datetime, DatasetEntry] = {}


    # Parse shutter dataset
    for table in shutter_tables:
        for record in table.records:


            entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
            if record["current_position"] is None or record["current_tilt_position"] is None:
                #invalidate entry
                entry.invalidate()
            else:
                entry.shutter_data[record["entity_id"]] = ShutterData(f"{record["domain"]}.{record["entity_id"]}", record["friendly_name_str"],
                                                                  record["current_position"], record["current_tilt_position"])


    #parse temperature dataset
    for table in temperature_tables:
        for record in table.records:


            entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
            if record["value"] is None:
                #invalidate entry
                entry.invalidate()
            else:
                entry.temperature_data[record["entity_id"]] = TemperatureData(f"{record["domain"]}.{record["entity_id"]}", record["friendly_name_str"],
                                                                  record["value"])

    for record in sun_tables[0].records:

        
        entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
        if record["azimuth"] is None or record["elevation"] is None:
            # invalidate entry
            entry.invalidate()
        else:
            entry.sun_data = SunData(f"{record["domain"]}.{record["entity_id"]}", record["friendly_name_str"],
                                                                  record["azimuth"], record["elevation"])

    for record in weather_tables[0].records:


        entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
        if record["temperature"] is None or record["cloud_coverage"] is None\
                or record["state"] is None:
            # invalidate entry
            entry.invalidate()
        else:
          entry.weather_data = WeatherData(f"{record["domain"]}.{record["entity_id"]}", record["friendly_name_str"],
                                                                  record["temperature"], record["cloud_coverage"], record["state"])
    for table in person_tables:
        for record in table.records:


            entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
            if record["_value"] is None:
                # invalidate entry
                entry.invalidate()
            else:
                is_home = record["_value"] == "home"
                entry.person_data.update_states(f"{record["domain"]}.{record["entity_id"]}", is_home)

    print(f"Data loaded - Entries: {len(dataset_dict)}")
    print("Filtering invalid data...")
    invalid_keys = []
    for key, value in dataset_dict.items():
        if not value.data_validity:
            invalid_keys.append(key)
    for key in invalid_keys:
        del dataset_dict[key]
    print(f"Data filtered - Removed: {len(invalid_keys)} - Remaining: {len(dataset_dict)}")
    print(f"First timestamp: {list(dataset_dict.keys())[0]} - Last timestamp: {list(dataset_dict.keys())[-1]}")

    with open('./data/training_data.pkl', 'wb') as out:
        pickle.dump(dataset_dict, out, protocol=pickle.HIGHEST_PROTOCOL)
    return dataset_dict