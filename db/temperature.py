from influxdb_client import InfluxDBClient

import const


def query_temps(db_client: InfluxDBClient, start_date, end_date):
    query_api = db_client.query_api()
    temp_query = f"""from(bucket: "homeassistant-prod")
      |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
      |> filter(fn: (r)=>
  (
    r._measurement == "°C"
  )
  )
  |> filter(fn: (r)=>
  (
    r._field == "value" or
    r._field == "friendly_name_str"
  )
  )
  
  |> filter(fn: (r)=>
  (
    r.entity_id == "bedroom_temperature" or
    r.entity_id == "exterior_temperature" or
    r.entity_id == "guest_room_temperature" or
    r.entity_id == "hallway_temperature" or
    r.entity_id == "living_room_temperature" or
    r.entity_id == "master_bedroom_temperature" or
    r.entity_id == "main_bathroom_temperature"

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
    tables = query_api.query(temp_query, org=const.ORG)
    return tables

class TemperatureData:
    device_id: str
    name: str
    temperature: float

    def __init__(self, device_id: str, name: str, temperature: float):
        self.device_id = device_id
        self.name = name
        self.temperature = temperature
