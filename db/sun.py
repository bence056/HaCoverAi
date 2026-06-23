from influxdb_client import InfluxDBClient

import util.const as const


def query_sun(db_client: InfluxDBClient, start_date, end_date):
    query_api = db_client.query_api()
    sun_query = f"""
    from(bucket: "homeassistant-prod")
      |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
      |> filter(fn: (r)=>
  (
    r._measurement == "sun.sun"
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
    tables = query_api.query(sun_query, org=const.ORG)
    return tables


class SunData:
    device_id: str
    name: str
    azimuth: float
    elevation: float

    def __init__(self, device_id: str, name: str, azimuth: float, elevation: float):
        self.device_id = device_id
        self.name = name
        self.azimuth = azimuth
        self.elevation = elevation