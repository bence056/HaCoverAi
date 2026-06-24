import datetime
import json
import os
from typing import Any
import websockets

from db.load_data import DatasetEntry
from model.module import CoverModel, load_cover_model
from model.tensor import parse_input_tensor
from util import const


async def async_prod_main():
    print("async main event loop started.")
    ai = CoverIntelligence()
    await ai.async_ws_connect()


class CoverIntelligence:
    options: Any
    HA_URL: str
    HA_TOKEN: str
    model: CoverModel
    ws_id: int

    def __init__(self):
        print("Initializing CoverIntelligence...")
        self.HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
        self.HA_URL = "ws://supervisor/core/websocket"
        self.ws_id = 1
        self.model = load_cover_model(const.MODEL_SAVE_PATH)
        self.model.eval()

    async def async_ws_connect(self) -> None:
        try:
            async with websockets.connect(self.HA_URL) as ws:
                msg = json.loads(await ws.recv())
                if msg["type"] == "auth_required":
                    print("Authenticating with websocket service...")
                    # Auth
                    await ws.send(json.dumps({
                        "type": "auth",
                        "access_token": self.HA_TOKEN,
                    }))

                    msg = json.loads(await ws.recv())

                    if msg["type"] != "auth_ok":
                        raise RuntimeError("Authentication failed!")

                    # Sub to custom event
                    await ws.send(json.dumps({
                        "id": self.ws_id,
                        "type": "subscribe_events",
                        "event_type": const.WS_EVENT_HANDLE
                    }))
                    self.ws_id += 1
                    result = json.loads(await ws.recv())

                    if not result["success"]:
                        raise RuntimeError("Event subscription failed!")

                    # Event loop
                    while True:
                        event = json.loads(await ws.recv())

                        if event.get("type") == "event" and event["event"]["event_type"] == const.WS_EVENT_HANDLE:
                            states = await self.async_ws_poll_ai_input(ws)
                            self.fill_schema_from_states(states)
                            timestamp = event["event"]["time_fired"]
                            self.evaluate_model(datetime.datetime.fromisoformat(timestamp))


        except (OSError, websockets.InvalidURI, websockets.InvalidHandshake) as ex:
            print(f"Failed to connect to websocket: {ex}")


    async def async_ws_poll_ai_input(self, ws):
        await ws.send(json.dumps({
            "id": self.ws_id,
            "type": "get_states"
        }))
        self.ws_id += 1

        states = json.loads(await ws.recv())
        return states["result"]


    def fill_schema_from_states(self, states):
        entity_ids = self.model.data_schema.get_entity_id_list()
        entity_datas: dict[str, dict] = {}
        for state in states:
            if state["entity_id"] in entity_ids:
                entity_datas[state["entity_id"]] = state

        #Load the data into the object
        for entity_id,shutter in self.model.data_schema.shutter_data.items():
            shutter.position = entity_datas[entity_id]["attributes"]["current_position"]
            shutter.tilt_position = entity_datas[entity_id]["attributes"]["current_tilt_position"]
        for entity_id,temperature in self.model.data_schema.temperature_data.items():
            temperature.temperature = entity_datas[entity_id]["state"]

        if self.model.data_schema.sun_data:
            sun_id = self.model.data_schema.sun_data.entity_id
            self.model.data_schema.sun_data.azimuth = entity_datas[sun_id]["attributes"]["azimuth"]
            self.model.data_schema.sun_data.azimuth = entity_datas[sun_id]["attributes"]["elevation"]

        if self.model.data_schema.weather_data:
            weather_id = self.model.data_schema.weather_data.entity_id
            self.model.data_schema.weather_data.state_string = entity_datas[weather_id]["state"]
            self.model.data_schema.weather_data.temperature = entity_datas[weather_id]["attributes"]["temperature"]
            self.model.data_schema.weather_data.cloud_coverage = entity_datas[weather_id]["attributes"]["cloud_coverage"]

        if self.model.data_schema.person_data:
            for entity_id in self.model.data_schema.person_data.person_states.keys():
                is_home = entity_datas[entity_id]["state"] == "home"
                self.model.data_schema.person_data.update_states(entity_id, is_home)


    def evaluate_model(self, time: datetime.datetime):
        if self.model.data_schema:
            adjusted = time.replace(tzinfo=datetime.timezone.utc, minute=0, second=0, microsecond=0)
            tensor_parse: dict[datetime.datetime, DatasetEntry] = {adjusted: self.model.data_schema}
            in_tensor = parse_input_tensor(tensor_parse)
            print(f"From time: {adjusted}")
            print(in_tensor)
