from threading import Lock
from typing import Any

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QMessageBox,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from qasync import asyncSlot

from utils.client_event_helper import ClientEventHelper
from utils.client_helper import ClientHelper
from utils.sync_await import sync_await
from utils.tcp_client import TCPClient


class PlayerTable(QTableWidget):
    new_player_signal: Any = pyqtSignal(dict)
    player_offline_signal: Any = pyqtSignal(dict)

    def __init__(self, client: TCPClient, username: str):
        super().__init__()
        self._current_username = username

        self._client_helper = ClientHelper(client)
        self._client_event_helper = ClientEventHelper(client)

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Tên", "Thách đấu"])

        self._table_lock = Lock()
        self._table_content: set[str] = set()

        self._new_player_online_event = self._client_event_helper.on_new_player_online(
            lambda player: self.new_player_signal.emit(player)
        )

        self._player_offline_event = self._client_event_helper.on_player_go_offline(
            lambda player: self.player_offline_signal.emit(player)
        )

        self.new_player_signal.connect(self._on_new_player)
        self.player_offline_signal.connect(self._on_player_offline)

        self._init_content()

    def _refresh_content(self, players: list[str]):
        self.setRowCount(len(players))

        for index, username in enumerate(players):
            challenge_button = QPushButton("Thách đấu")
            challenge_button.clicked.connect(
                lambda: self.send_challenge(username),  # type: ignore
            )

            self.setItem(index, 0, QTableWidgetItem(username))
            self.setCellWidget(index, 1, challenge_button)

    @asyncSlot()
    async def send_challenge(self, username: str):
        await self._client_helper.send_challenge(username)

    def _init_content(self):
        online_players = sync_await(self._client_helper.get_online_players())
        with self._table_lock:
            self._table_content = {
                player["username"]
                for player in online_players  #
                if player["username"] != self._current_username
            }

            self._refresh_content(sorted(self._table_content))

    def _on_new_player(self, player: dict):
        with self._table_lock:
            self._table_content.add(player["username"])
            self._refresh_content(sorted(self._table_content))

    def _on_player_offline(self, player: dict):
        with self._table_lock:
            self._table_content.discard(player["username"])
            self._refresh_content(sorted(self._table_content))

    def cleanup(self):
        self._client_event_helper.remove_event(self._player_offline_event)
        self._client_event_helper.remove_event(self._new_player_online_event)


class MatchMakingView(QWidget):
    new_challenge_signal: Any = pyqtSignal(dict)

    def __init__(self, client: TCPClient, username: str):
        super().__init__()
        self._tcp_client = client
        self.setWindowTitle("Người chơi online")
        self.resize(600, 400)

        self._table = PlayerTable(self._tcp_client, username)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)  # type: ignore

        top_layout = QHBoxLayout()
        top_layout.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self._table)
        self.setLayout(layout)

        self._client_event_helper = ClientEventHelper(self._tcp_client)
        self._client_helper = ClientHelper(self._tcp_client)

        self.new_challenge_signal.connect(self.on_new_challenge)

        self._on_received_challenge_event = (
            self._client_event_helper.on_received_challenge(
                lambda player: self.new_challenge_signal.emit(player)
            )
        )

    def on_new_challenge(self, body: dict):
        from_username, challenge_id = body["from"], body["challengeId"]
        reply = QMessageBox.question(
            self,
            "Lời thách đấu",
            f"Bạn nhận được lời thách đấu từ {from_username}!\nBạn có muốn chấp nhận?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        new_status = "declined"
        if reply == QMessageBox.Yes:
            new_status = "accepted"

        sync_await(self._client_helper.replies_challenge(challenge_id, new_status))

    def cleanup(self):
        self._table.cleanup()
        self._client_event_helper.remove_event(self._on_received_challenge_event)
