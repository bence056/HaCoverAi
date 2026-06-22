from influxdb_client import InfluxDBClient

import const


def query_person(db_client: InfluxDBClient):
    query_api = db_client.query_api()
    person_query = f"""from(bucket: "homeassistant-prod")
      |> range(start: {const.START_DATE})
      |> filter(fn: (r)=>
  (
    r._measurement == "person.csaba_varga" or
    r._measurement == "person.bence_varga"
  )
  )
  |> filter(fn: (r)=>
  (
    r._field == "state"
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
      columnKey: ["_measurement", "entity_id"],
      valueColumn: "_value"
  )
    """
    tables = query_api.query(person_query, org=const.ORG)
    return tables


class PersonData:
    device_id: str
    name: str
    ben_home: bool
    csaba_home: bool
    home_count: int

    def __init__(self, ben_home: str, csaba_home: str):
        self.ben_home = ben_home == "home"
        self.csaba_home = csaba_home == "home"
        self.home_count = self.ben_home + self.csaba_home
