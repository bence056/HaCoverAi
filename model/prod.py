import json
import os
from typing import Any

import torch
import websockets

from model.module import CoverModel
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

    def __init__(self):
        print("Initializing CoverIntelligence...")
        self.HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
        self.HA_URL = "ws://supervisor/core/websocket"
        prod_model = CoverModel(16, 17) #CHANGE THIS IMPORTANT!
        prod_model.load_state_dict(torch.load('./data/model.pt'))
        prod_model.eval()

    async def async_ws_connect(self) -> None:
        async with websockets.connect(self.HA_URL) as ws:
            msg = json.loads(await ws.recv())
            print(msg)
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
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": const.WS_EVENT_HANDLE
                }))

                result = json.loads(await ws.recv())

                if not result["success"]:
                    raise RuntimeError("Event subscription failed!")

                # Event loop
                while True:
                    event = json.loads(await ws.recv())

                    if event.get("type") == "event" and event["event"]["event_type"] == const.WS_EVENT_HANDLE:
                        print(event)
                        await self.async_ws_poll_ai_input(ws)

    async def async_ws_poll_ai_input(self, ws):
        await ws.send(json.dumps({
            "id": 2,
            "type": "get_states"
        }))

        states = json.loads(await ws.recv())
        print(states)
