import asyncio
import datetime
import json
import os
from typing import Any

import torch
import websockets

from db.load_data import DatasetEntry
from db.shutters import ShutterData
from model.module import CoverModel, load_cover_model
from model.tensor import parse_input_tensor, convert_from_prediction
from util import const
from util.websocket import WSClient


async def async_prod_main():
    print("async main event loop started.")
    ai = CoverIntelligence()
    await ai.async_ws_connect()


class CoverIntelligence:
    options: Any
    HA_URL: str
    HA_TOKEN: str
    model: CoverModel
    ws_event_string: str
    pos_trigger_delta: int
    tilt_trigger_delta: int
    ws_id: int

    def __init__(self):
        print("Initializing CoverIntelligence...")
        self.HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
        self.HA_URL = "ws://supervisor/core/websocket"
        self.ws_id = 1
        with open("/data/options.json") as f:
            self.options = json.load(f)
            self.ws_event_string = self.options["custom_trigger_event"]
            if self.ws_event_string == "":
                self.ws_event_string = const.WS_EVENT_HANDLE
            self.pos_trigger_delta =  min(100, max(int(self.options["position_trigger_delta"]), 0))
            self.tilt_trigger_delta =  min(100, max(int(self.options["tilt_trigger_delta"]), 0))
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
                    custom_ws: WSClient = WSClient(ws)
                    await custom_ws.connect()
                    await custom_ws.subscribe_ha_event(self.ws_event_string, self.handle_ai_trigger)

                    # Event loop
                    while True:
                        await asyncio.sleep(1)

        except (OSError, websockets.InvalidURI, websockets.InvalidHandshake) as ex:
            print(f"Failed to connect to websocket: {ex}")


    async def handle_ai_trigger(self, ws_client: WSClient, event_data):
        print("Event Received!!!")
        states = await self.async_ws_poll_ai_input(ws_client)
        self.fill_schema_from_states(states)
        timestamp = event_data["event"]["time_fired"]
        predicted_shutters = self.evaluate_model(datetime.datetime.fromisoformat(timestamp))
        # for shutter in predicted_shutters:
        #     await self.async_set_shutter(ws, shutter)
        tmp_data = ShutterData("cover.roller_shutter_3_9", "Bedroom TMP", 0, 100)
        await self.async_set_shutter(ws_client, tmp_data)

    async def async_ws_poll_ai_input(self, ws):
        states = await ws.request({
            "type": "get_states"
        })
        print("Future returned")
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
        significant_change: list[ShutterData] = []
        if self.model.data_schema:
            adjusted = time.replace(tzinfo=datetime.timezone.utc, minute=0, second=0, microsecond=0)
            tensor_parse: dict[datetime.datetime, DatasetEntry] = {adjusted: self.model.data_schema}
            in_tensor = parse_input_tensor(tensor_parse)
            print(f"From time: {adjusted}")
            print(in_tensor)
            with torch.no_grad():
                pred = self.model(in_tensor)
                print(f"Model prediction: {pred}")
                new_shutters = convert_from_prediction(pred, self.model.data_schema)
                #data is ready to send back to set value. First check if deltas are big enough to be a significant change.
                for shutter in new_shutters:
                    current_state = self.model.data_schema.shutter_data.get(shutter.entity_id)
                    if current_state is not None:
                        pos_delta = abs(current_state.position - shutter.position)
                        tilt_delta = abs(current_state.tilt_position - shutter.tilt_position)
                        if pos_delta >= self.pos_trigger_delta or tilt_delta >= self.tilt_trigger_delta:
                            significant_change.append(shutter)
                            print(f"Adding significant change: {shutter.entity_id} - DeltaPos: {pos_delta} - DeltaTilt: {tilt_delta}")
        return significant_change

    async def async_set_shutter(self, ws: WSClient, data: ShutterData) -> bool:
        print(f"Setting shutter {data.name} position to {data.position} and tilt to  {data.tilt_position}")
        success = True

        async def cover_state_update(ws_local, event_data):
            await ws.send(
                {
                    "type": "call_service",
                    "domain": "cover",
                    "service": "set_cover_position",
                    "service_data": {
                        "position": data.position,
                    },
                    "target": {
                        "entity_id": data.entity_id
                    }
                }
            )
            print("Sent normal position")

        await ws.subscribe_ha_trigger(
            {
                "platform": "state",
                "entity_id": data.entity_id,
                "attribute": "current_tilt_position"
            },
            cover_state_update
        )
        print("Subscribed")

        await ws.send(
            {
                "type": "call_service",
                "domain": "cover",
                "service": "set_cover_tilt_position",
                "service_data": {
                    "tilt_position": data.tilt_position,
                },
                "target": {
                    "entity_id": data.entity_id
                }

            }
        )
        print("Sent tilt position")

        return True