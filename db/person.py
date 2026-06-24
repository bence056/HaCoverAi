from influxdb_client import InfluxDBClient

import util.const as const


def query_person(db_client: InfluxDBClient, start_date, end_date):
    query_api = db_client.query_api()
    person_query = f"""from(bucket: "homeassistant-prod")
      |> range(start: {start_date.isoformat()}, stop: {end_date.isoformat()})
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


    """
    tables = query_api.query(person_query, org=const.ORG)
    return tables


class PersonData:
    person_states: dict[str, bool] = {}
    home_count: int = 0

    def update_states(self, key: str, value: bool):
        self.person_states[key] = value
        home_count = 0
        for value in self.person_states.values():
            home_count += value