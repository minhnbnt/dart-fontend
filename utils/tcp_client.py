import asyncio
import json
import socket
from threading import Lock, Thread
from typing import Callable
from uuid import UUID, uuid4

type _Callback = Callable[[dict], None]


class TCPClient:
    def __init__(self, address: tuple[str, int]):
        self.fp_lock = asyncio.Lock()
        self.callbacks_lock = Lock()

        self._address = address
        self.queue_callbacks: dict[UUID, _Callback] = {}

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self._address)

        self.fp = self.socket.makefile(mode="rw", encoding="utf-8")

        self._message_bridge_thread = Thread(target=self._message_bridge)
        self._message_bridge_thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.socket:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()

            if self.fp and not self.fp.closed:
                self.fp.close()

            self._message_bridge_thread.join()

        finally:
            self.socket = self.fp = None

    def _message_bridge(self):
        for message in self.get_fp():
            if len(message) == 0:
                return

            print("[Server]", message, end="")
            json_object = json.loads(message)

            with self.callbacks_lock:
                callbacks = list(self.queue_callbacks.values())

            for callback in callbacks:
                callback(json_object)

    def get_fp(self):
        if self.fp is None:
            raise ValueError("Socket is not initialized.")

        return self.fp

    def add_callback(self, callback: Callable, id: UUID | None = None) -> UUID:
        if id is None:
            id = uuid4()

        self.queue_callbacks[id] = callback

        return id

    def remove_callback(self, id: UUID):
        with self.callbacks_lock:
            self.queue_callbacks.pop(id)

    async def write_object(self, obj: dict):
        fp = self.get_fp()

        message = json.dumps(obj)
        print("[Client]", message)

        async with self.fp_lock:
            fp.write(message)
            fp.write("\n")

            fp.flush()

    async def send_object(self, obj: dict) -> dict:
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        id = uuid4()
        obj["id"] = str(id)

        def callback(response: dict):
            if "id" not in response:
                return

            if UUID(response["id"]) != id:
                return

            loop.call_soon_threadsafe(future.set_result, response)
            self.remove_callback(id)

        self.add_callback(callback, id)

        await self.write_object(obj)
        return await future
