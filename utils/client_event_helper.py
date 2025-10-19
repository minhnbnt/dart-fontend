from typing import Callable
from uuid import UUID

from .message_filter import (
    is_new_player_online_event,
    is_player_go_offline_event,
    is_new_challenger_event,
)
from .tcp_client import TCPClient

type NewPlayerOnlineCallback = Callable[[dict], None]
type PlayerGoOfflineCallback = NewPlayerOnlineCallback


class ClientEventHelper:
    def __init__(self, client: TCPClient) -> None:
        self._client = client

    def remove_event(self, id: UUID):
        self._client.remove_callback(id)

    def on_new_player_online(self, callback: NewPlayerOnlineCallback):
        def client_callback(message: dict):
            if not is_new_player_online_event(message):
                return

            username = message["body"]
            callback(username)

        return self._client.add_callback(client_callback)

    def on_player_go_offline(self, callback: PlayerGoOfflineCallback):
        def client_callback(message: dict):
            if not is_player_go_offline_event(message):
                return

            username = message["body"]
            callback(username)

        return self._client.add_callback(client_callback)

    def on_received_challenge(self, callback: PlayerGoOfflineCallback):
        def client_callback(message: dict):
            if not is_new_challenger_event(message):
                return

            username = message["body"]
            callback(username)

        return self._client.add_callback(client_callback)
