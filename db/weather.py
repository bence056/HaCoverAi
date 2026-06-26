from influxdb_client import InfluxDBClient
import util.const as const


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



|> pivot(
      rowKey: ["_time"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
    """
    tables = query_api.query(w_query, org=const.ORG)
    return tables

class WeatherData:
    entity_id: str
    name: str
    temperature: float
    cloud_coverage: float
    state_string: str

    def __init__(self, entity_id: str, name: str, temperature: float, cloud_coverage: float, state_string: str):
        self.entity_id = entity_id
        self.name = name
        self.temperature = temperature
        self.cloud_coverage = cloud_coverage
        self.state_string = state_string