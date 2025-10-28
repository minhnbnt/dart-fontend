from typing import Literal
from .tcp_client import TCPClient


def _raise_if_not_ok(response: dict):
    is_ok = response.get("ok", False)
    if is_ok:
        return

    message = response.get("message")
    if message is None:
        message = "Unknown error."

    raise ValueError(message)


class ClientHelper:
    def __init__(self, client: TCPClient) -> None:
        self._client = client

    async def login(self, username: str, password: str):
        request = {
            "command": "login",
            "body": {
                "username": username,
                "password": password,
            },
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

    async def sign_up(self, username: str, password: str):
        request = {
            "command": "register",
            "body": {
                "username": username,
                "password": password,
            },
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

    async def get_online_players(self) -> list[dict]:
        request = {"command": "listOnline"}

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

        return response["body"]

    async def send_challenge(self, to: str):
        request = {
            "command": "challengePlayer",
            "body": {"to": to},
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

        return response["body"]

    async def replies_challenge(
        self,
        id: int,
        status: Literal["accepted", "declined"],
    ):
        request = {
            "command": "answerChallenge",
            "body": {
                "challengeId": id,
                "newStatus": status,
            },
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)
