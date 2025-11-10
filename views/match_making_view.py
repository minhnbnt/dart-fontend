from threading import Lock
from typing import Any

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot
from utils.client_event_helper import ClientEventHelper
from utils.client_helper import ClientHelper
from utils.sync_await import sync_await
from utils.tcp_client import TCPClient


class PlayerTable(QTableWidget):
    new_player_signal: Any = pyqtSignal(dict)
    player_offline_signal: Any = pyqtSignal(dict)

    def __init__(self, client: TCPClient, username: str, on_challenge_sent=None):
        super().__init__()
        self._current_username = username
        self._on_challenge_sent = on_challenge_sent

        self._client_helper = ClientHelper(client)
        self._client_event_helper = ClientEventHelper(client)

        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(
            ["Tên", "Trận", "Thắng", "Thua", "Điểm", "Thách đấu"]
        )
        # Set column widths
        self.setColumnWidth(0, 120)  # Username
        self.setColumnWidth(1, 50)  # Total matches
        self.setColumnWidth(2, 50)  # Wins
        self.setColumnWidth(3, 50)  # Losses
        self.setColumnWidth(4, 70)  # Score
        self.setColumnWidth(5, 100)  # Challenge button

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

    def _refresh_content(self, players: list[dict]):
        self.setRowCount(len(players))

        for index, player in enumerate(players):
            username = player["username"]
            total_matches = player.get("totalMatches", 0)
            wins = player.get("wins", 0)
            losses = player.get("losses", 0)
            total_score = player.get("totalScore", 0)
            win_rate = player.get("winRate", 0)

            challenge_button = QPushButton("Thách đấu")
            challenge_button.clicked.connect(
                lambda checked=False, u=username: self.send_challenge(u),
            )

            # Set player info
            self.setItem(index, 0, QTableWidgetItem(username))
            self.setItem(index, 1, QTableWidgetItem(str(total_matches)))
            self.setItem(index, 2, QTableWidgetItem(f"{wins} ({win_rate}%)"))
            self.setItem(index, 3, QTableWidgetItem(str(losses)))
            self.setItem(index, 4, QTableWidgetItem(str(total_score)))
            self.setCellWidget(index, 5, challenge_button)

            # Center align numeric columns
            for col in [1, 2, 3, 4]:
                item = self.item(index, col)
                if item:
                    item.setTextAlignment(4 | 128)  # AlignCenter

    @asyncSlot()
    async def send_challenge(self, username: str):
        await self._client_helper.send_challenge(username)
        if self._on_challenge_sent:
            self._on_challenge_sent(username)

    def _init_content(self):
        online_players = sync_await(self._client_helper.get_online_players())
        with self._table_lock:
            # Filter out current user and store full player objects
            filtered_players = [
                player
                for player in online_players
                if player["username"] != self._current_username
            ]

            self._table_content = {player["username"] for player in filtered_players}

            # Sort by win rate descending, then by total score
            sorted_players = sorted(
                filtered_players,
                key=lambda p: (p.get("winRate", 0), p.get("totalScore", 0)),
                reverse=True,
            )

            self._refresh_content(sorted_players)

    def _on_new_player(self, player: dict):
        # Refresh full list to get updated stats
        self._init_content()

    def _on_player_offline(self, player: dict):
        # Refresh full list to get updated stats
        self._init_content()

    def cleanup(self):
        self._client_event_helper.remove_event(self._player_offline_event)
        self._client_event_helper.remove_event(self._new_player_online_event)


class MatchMakingView(QWidget):
    new_challenge_signal: Any = pyqtSignal(dict)
    start_game_signal: Any = pyqtSignal(dict)

    def __init__(self, client: TCPClient, username: str):
        super().__init__()
        self._tcp_client = client
        self._username = username
        self._last_opponent = None  # Track opponent for game start
        self._is_challenger = False  # Track if we sent the challenge
        self.setWindowTitle("Người chơi online")
        self.resize(800, 500)

        self._table = PlayerTable(
            self._tcp_client, username, on_challenge_sent=self._on_challenge_sent
        )
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)  # type: ignore

        # Stats panel for current user
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QGroupBox, QLabel

        stats_group = QGroupBox(f"📊 Thống kê của {username}")
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel("Đang tải...")
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #f0f8ff; border-radius: 5px;"
        )
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)

        layout = QVBoxLayout()
        layout.addWidget(stats_group)
        layout.addWidget(self._table)
        self.setLayout(layout)

        self._client_event_helper = ClientEventHelper(self._tcp_client)
        self._client_helper = ClientHelper(self._tcp_client)

        # Update stats (after _client_helper is initialized)
        self._update_user_stats()

        self.new_challenge_signal.connect(self.on_new_challenge)
        self.start_game_signal.connect(self.on_start_game)

        self._on_received_challenge_event = (
            self._client_event_helper.on_received_challenge(
                lambda player: self.new_challenge_signal.emit(player)
            )
        )

        self._on_start_game_event = self._client_event_helper.on_start_game(
            lambda body: self.start_game_signal.emit(body)
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
            self._last_opponent = from_username  # Store for game start
            self._is_challenger = False  # We are the receiver

        try:
            sync_await(self._client_helper.answer_challenge(challenge_id, new_status))
        except Exception as e:
            print(f"Lỗi khi trả lời thách đấu: {e}")
            QMessageBox.warning(self, "Lỗi", f"Không thể trả lời thách đấu: {e}")

    def _on_challenge_sent(self, opponent: str):
        """Callback khi gửi challenge để lưu opponent info"""
        self._last_opponent = opponent
        self._is_challenger = True  # We sent the challenge

    def on_start_game(self, body):
        from .dart_board_view import DartBoardView

        print(f"[DEBUG] startGame event received")
        print(f"[DEBUG] body = {body}, type = {type(body)}")
        print(f"[DEBUG] _last_opponent = {self._last_opponent}")
        print(f"[DEBUG] _is_challenger = {self._is_challenger}")

        # Backend có thể gửi body dạng dict {"id": match_id} hoặc trực tiếp là match_id
        if isinstance(body, dict):
            match_id = body.get("id")
        else:
            match_id = body

        if match_id is None:
            print(f"[ERROR] No match_id in startGame body: {body}")
            QMessageBox.warning(self, "Lỗi", "Không nhận được ID trận đấu!")
            return

        # Opponent được track từ lúc gửi/nhận challenge
        opponent = self._last_opponent
        if not opponent:
            print(f"[ERROR] No opponent tracked")
            QMessageBox.warning(self, "Lỗi", "Không xác định được đối thủ!")
            return

        # Người gửi challenge (from) sẽ đi trước
        is_first = self._is_challenger

        self.game_view = DartBoardView(
            client=self._tcp_client,
            username=self._username,
            opponent=opponent,
            is_first=is_first,
            match_id=match_id,
        )
        # Kết nối signal để quay lại lobby khi game kết thúc
        self.game_view.game_ended_signal.connect(self._on_game_ended)
        self.game_view.show()
        self.hide()

        # Reset opponent tracking
        self._last_opponent = None
        self._is_challenger = False

    def _update_user_stats(self):
        """Cập nhật thống kê của user hiện tại"""
        try:
            print(f"[DEBUG] Fetching online players for stats...")
            online_players = sync_await(self._client_helper.get_online_players())
            print(f"[DEBUG] Got {len(online_players)} players")

            # Tìm stats của current user
            user_stats = None
            for player in online_players:
                if player.get("username") == self._username:
                    user_stats = player
                    print(f"[DEBUG] Found current user stats: {user_stats}")
                    break

            if user_stats:
                total_matches = user_stats.get("totalMatches", 0)
                wins = user_stats.get("wins", 0)
                losses = user_stats.get("losses", 0)
                total_score = user_stats.get("totalScore", 0)
                win_rate = user_stats.get("winRate", 0)

                stats_text = (
                    f"🎯 Trận: {total_matches} | "
                    f"✅ Thắng: {wins} ({win_rate}%) | "
                    f"❌ Thua: {losses} | "
                    f"⭐ Tổng điểm: {total_score}"
                )
                print(f"[DEBUG] Setting stats text: {stats_text}")
                self.stats_label.setText(stats_text)
            else:
                # User chưa có trong online list hoặc chưa chơi trận nào
                print(
                    f"[DEBUG] User {self._username} not found in online players, showing default"
                )
                self.stats_label.setText(
                    "🎯 Trận: 0 | ✅ Thắng: 0 (0%) | ❌ Thua: 0 | ⭐ Tổng điểm: 0"
                )
        except Exception as e:
            import traceback

            print(f"[ERROR] Error loading user stats: {e}")
            print(traceback.format_exc())
            self.stats_label.setText(f"Lỗi tải thống kê: {str(e)[:50]}")

    def _on_game_ended(self):
        """Xử lý khi game kết thúc - quay lại lobby"""
        print("[DEBUG] Game ended, returning to lobby")
        # Đóng game view
        if hasattr(self, "game_view") and self.game_view:
            self.game_view.close()
            self.game_view = None
        # Hiển thị lại lobby
        self.show()
        # Refresh danh sách người chơi và stats
        self._table._init_content()
        self._update_user_stats()

    def cleanup(self):
        self._table.cleanup()
        self._client_event_helper.remove_event(self._on_received_challenge_event)
        self._client_event_helper.remove_event(self._on_start_game_event)
