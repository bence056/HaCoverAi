import asyncio

import itertools
import json
from collections import defaultdict

import websockets
from websockets import InvalidProxy, InvalidURI, InvalidHandshake


class WSClient:

    def __init__(self, ws):
        self.ws = ws
        self.outgoing = asyncio.Queue()
        self._idc = itertools.count(1)
        self._pending = {}

        self._subs = defaultdict(list)
        self._tasks = set()


    async def connect(self):
        #Do the connection first from params.
        self._tasks = {
            asyncio.create_task(self._reader()),
            asyncio.create_task(self._writer())
        }

    async def close(self):
        for t in self._tasks:
            t.cancel()


    async def send(self, msg: dict):
        msg["id"] = next(self._idc)
        await self.outgoing.put(msg)
        return self._idc

    async def request(self, msg: dict, timeout = 10):
        msg_id = next(self._idc)
        msg["id"] = msg_id
        fut = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut
        await self.send(msg)
        print("Waiting for request future")
        return await asyncio.wait_for(fut, timeout=timeout)


    def on(self, event_name: str, callback):
        self._subs[event_name].append(callback)

    def off(self, event_name: str, callback):
        self._subs[event_name].remove(callback)


    async def subscribe_ha_event(self, event_name: str, callback):
        msg = {
            "id": next(self._idc),
            "type": "subscribe_events",
            "event_type": event_name,
        }

        async def handler(event):
            await callback(self, event)

        self.on(event_name, handler)
        await self.send(msg)
        return msg["id"]

    async def subscribe_ha_trigger(self, trigger: dict, callback):
        msg = {
            "id": next(self._idc),
            "type": "subscribe_trigger",
            "trigger": trigger,
        }

        async def handler(event):
            await callback(self, event)

        self.on(f"trigger_{msg["id"]}", handler)
        await self.send(msg)
        return msg["id"]



    async def wait_for_event(self, event_name: str, predicate = None):

        fut = asyncio.get_running_loop().create_future()

        def handler(event):
            if predicate is None or predicate(event):
                if not fut.done():
                    fut.set_result(event)

        self.on(event_name, handler)
        try:
            return await fut
        finally:
            self.off(event_name, handler)



    async def _writer(self):
        while True:
            msg = await self.outgoing.get()
            await self.ws.send(json.dumps(msg))

    async def _reader(self):
        while True:
            msg = json.loads(await self.ws.recv())
            if len(self._pending) > 0:
                print(self._pending)
            if msg["id"] in self._pending:
                fut = self._pending.pop(msg["id"])
                if not fut.done():
                    fut.set_result(msg)
                continue

            if msg.get("type") == "event":
                for sub in self._subs[msg["event"]["event_type"]]:
                    asyncio.create_task(sub(msg))
                continue

            if msg.get("type") == "trigger":
                event_id = f"trigger_{msg["id"]}"
                for sub in self._subs[event_id]:
                    asyncio.create_task(sub(msg))