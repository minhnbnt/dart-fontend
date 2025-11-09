from typing import Callable
from uuid import UUID

from .message_filter import (
    is_challenge_canceled_event,
    is_challenge_rejected_event,
    is_new_challenger_event,
    is_new_player_online_event,
    is_other_threw_event,
    is_player_forfeited_event,
    is_player_go_offline_event,
    is_start_game_event,
)
from .tcp_client import TCPClient

type EventCallback = Callable[[dict], None]


class ClientEventHelper:
    def __init__(self, client: TCPClient) -> None:
        self._client = client

    def remove_event(self, id: UUID):
        self._client.remove_callback(id)

    def on_new_player_online(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_new_player_online_event(message):
                return

            username = message["body"]
            callback(username)

        return self._client.add_callback(client_callback)

    def on_player_go_offline(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_player_go_offline_event(message):
                return

            username = message["body"]
            callback(username)

        return self._client.add_callback(client_callback)

    def on_received_challenge(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_new_challenger_event(message):
                return

            body = message["body"]
            callback(body)

        return self._client.add_callback(client_callback)

    def on_challenge_canceled(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_challenge_canceled_event(message):
                return

            body = message["body"]
            callback(body)

        return self._client.add_callback(client_callback)

    def on_challenge_rejected(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_challenge_rejected_event(message):
                return

            body = message["body"]
            callback(body)

        return self._client.add_callback(client_callback)

    def on_start_game(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_start_game_event(message):
                return

            body = message["body"]
            callback(body)

        return self._client.add_callback(client_callback)

    def on_other_threw(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_other_threw_event(message):
                return

            body = message["body"]
            callback(body)

        return self._client.add_callback(client_callback)

    def on_player_forfeited(self, callback: EventCallback):
        def client_callback(message: dict):
            if not is_player_forfeited_event(message):
                return

            body = message["body"]
            callback(body)

        return self._client.add_callback(client_callback)
