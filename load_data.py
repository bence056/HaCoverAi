import datetime

import influxdb_client, os, time

import const
from person import query_person, PersonData
from shutters import query_shutters, ShutterData
from sun import query_sun, SunData
from temperature import query_temps, TemperatureData
from weather import query_weather, WeatherData


class DatasetEntry:

    shutter_data: dict[str, ShutterData]
    temperature_data: dict[str, TemperatureData]
    sun_data: SunData | None
    weather_data: WeatherData | None
    person_data: PersonData | None

    def __init__(self):
        self.shutter_data = {}
        self.temperature_data = {}
        self.sun_data = None
        self.weather_data = None
        self.person_data = None


def query_influx() -> dict[datetime.datetime, DatasetEntry]:

    db_client = influxdb_client.InfluxDBClient(url=const.URL, token=const.INFLUXDB_TOKEN, org=const.ORG)

    connected = db_client.ping()
    print(f"Connected: {connected}")
    if connected:
        print(f"Version: {db_client.version()}")

    shutter_tables = query_shutters(db_client)
    temperature_tables = query_temps(db_client)
    sun_tables = query_sun(db_client)
    weather_tables = query_weather(db_client)
    person_tables = query_person(db_client)


    dataset_dict: dict[datetime.datetime, DatasetEntry] = {}

    start_time: datetime.datetime = datetime.datetime.fromisoformat(const.START_DATE)
    end_time: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    #find the first common timestamp across the entry set.

    for table_set in (shutter_tables, temperature_tables, sun_tables, weather_tables, person_tables):
        test = max(
            table.records[0].get_time()
            for table in table_set
            if table.records
        )
        if start_time is None:
            start_time = test
        elif test > start_time:
            start_time = test

        test = min(
            table.records[-1].get_time()
            for table in table_set
            if table.records
        )
        if end_time is None:
            end_time = test
        elif test < end_time:
            end_time = test

    # Parse shutter dataset
    for table in shutter_tables:
        for record in table.records:

            if start_time <= record.get_time() < end_time:
                entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
                entry.shutter_data[record["entity_id"]] = ShutterData(record["entity_id"], record["friendly_name_str"],
                                                                      record["current_position"], record["current_tilt_position"])


    #parse temperature dataset
    for table in temperature_tables:
        for record in table.records:

            if start_time <= record.get_time() < end_time:
                entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
                entry.temperature_data[record["entity_id"]] = TemperatureData(record["entity_id"], record["friendly_name_str"],
                                                                      record["value"])

    for record in sun_tables[0].records:

        if start_time <= record.get_time() < end_time:
            entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
            entry.sun_data = SunData(record["entity_id"], record["friendly_name_str"],
                                                                      record["azimuth"], record["elevation"])

    for record in weather_tables[0].records:

        if start_time <= record.get_time() < end_time:
            entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
            entry.weather_data = WeatherData(record["entity_id"], record["friendly_name_str"],
                                                                      record["temperature"], record["cloud_coverage"], record["state"])

    for record in person_tables[0].records:

        if start_time <= record.get_time() < end_time:
            entry = dataset_dict.setdefault(record.get_time(), DatasetEntry())
            entry.person_data = PersonData(record["person.bence_varga_bence_varga"],record["person.csaba_varga_csaba_varga"])

    print("Data loaded")
    return dataset_dict