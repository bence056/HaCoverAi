import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import websockets

from util import const


async def async_prod_main():
    print("async main event loop started.")
    ai = CoverIntelligence()
    await ai.async_ws_connect()


class CoverIntelligence:
    options: Any
    HA_URL: str
    HA_TOKEN: str

    def __init__(self):
        print("Initializing CoverIntelligence...")
        self.HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
        self.HA_URL = "ws://supervisor/core/websocket"

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
