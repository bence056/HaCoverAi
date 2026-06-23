from influxdb_client import InfluxDBClient

import const


def query_weather(db_client: InfluxDBClient, start_date, end_date):
    query_api = db_client.query_api()
    w_query = f"""from(bucket: "homeassistant-prod")
      |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
            |> filter(fn: (r)=>
  (
    r._measurement == "weather.home"
  )
  )
  

  |> aggregateWindow(
      every: 1h,
      fn: last,
      offset: 0h,
      createEmpty: true,
  )

 |> fill(usePrevious: true)

|> filter(fn: (r)=>
      (
      exists r._value
      )
      )

|> pivot(
      rowKey: ["_time"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
    """
    tables = query_api.query(w_query, org=const.ORG)
    return tables

class WeatherData:
    device_id: str
    name: str
    temperature: float
    cloud_coverage: float
    state_string: str

    def __init__(self, device_id: str, name: str, temperature: float, cloud_coverage: float, state_string: str):
        self.device_id = device_id
        self.name = name
        self.temperature = temperature
        self.cloud_coverage = cloud_coverage
        self.state_string = state_string