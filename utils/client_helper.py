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

    async def answer_challenge(
        self,
        challenge_id: int,
        new_status: Literal["accepted", "declined"],
    ):
        request = {
            "command": "answerChallenge",
            "body": {
                "challengeId": challenge_id,
                "newStatus": new_status,
            },
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

    async def throw_dart(
        self,
        match_id: int,
        score: int,
        dx: float = None,
        dy: float = None,
        rotation_angle: float = None,
    ):
        body = {
            "matchId": match_id,
            "score": score,
        }

        # Thêm tọa độ nếu có
        if dx is not None:
            body["dx"] = dx
        if dy is not None:
            body["dy"] = dy
        if rotation_angle is not None:
            body["rotationAngle"] = rotation_angle

        request = {
            "command": "throw",
            "body": body,
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

        return response.get("body")

    async def forfeit_match(self, match_id: int):
        request = {
            "command": "forfeit",
            "body": {
                "matchId": match_id,
            },
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

        return response.get("body")

    async def spin_dartboard(
        self, match_id: int, rotation_amount: float, duration: float
    ):
        """
        Gửi lệnh xoay dartboard đến đối thủ
        Args:
            match_id: ID của trận đấu
            rotation_amount: Số độ xoay (vd: 720 = 2 vòng)
            duration: Thời gian xoay tính bằng ms (vd: 3000 = 3 giây)
        """
        request = {
            "command": "spin",
            "body": {
                "matchId": match_id,
                "rotationAmount": rotation_amount,
                "duration": duration,
            },
        }

        response = await self._client.send_object(request)
        _raise_if_not_ok(response)

        return response.get("body")
