from influxdb_client import InfluxDBClient
import util.const as const


def query_shutters(db_client: InfluxDBClient, start_date, end_date):
    query_api = db_client.query_api()
    shutters_query = f"""from(bucket: "homeassistant-prod")
      |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
      |> filter(fn: (r)=>
      (
        r._measurement =~ /cover/ and
        r._measurement != "cover.bottom_floor_covers" and 
        r._measurement != "cover.top_floor_covers" and
        r._measurement != "cover.bottom_floor_covers_primitive" and 
        r._measurement != "cover.top_floor_covers_primitive"
      )
      )
      |> filter(fn: (r)=>
      (
        r._field == "current_position" or
        r._field == "current_tilt_position" or
        r._field == "friendly_name_str"
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
    tables = query_api.query(shutters_query, org=const.ORG)
    return tables



class ShutterData:
    entity_id: str
    name: str
    position: int
    tilt_position: int

    def __init__(self, entity_id, name, position, tilt_position):
        self.entity_id = entity_id
        self.name = name
        self.position = position
        self.tilt_position = tilt_position