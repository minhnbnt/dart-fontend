import math
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect, pyqtSlot
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

BOARD_RADIUS = 200
BULL_RADIUS = 10
BULL_OUTER_RADIUS = 25
TRIPLE_INNER_RADIUS = 107
TRIPLE_OUTER_RADIUS = 117
DOUBLE_INNER_RADIUS = 170
DOUBLE_OUTER_RADIUS = 180
BOARD_NUMBERS = [6, 13, 4, 18, 1, 20, 5, 12, 9, 14, 11, 8, 16, 7, 19, 3, 17, 2, 15, 10]
SEGMENT_ANGLE = 18


class DartBoardWidget(QWidget):
    dart_thrown_signal = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(BOARD_RADIUS * 2 + 40, BOARD_RADIUS * 2 + 40)
        self.board_rotation = 0
        self.darts_on_board = []
        self.setStyleSheet(
            "background-color: #2E7D32; border: 2px solid #1B5E20; border-radius: 10px;"
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPoint(self.width() // 2, self.height() // 2)

        # Xoay bảng
        painter.translate(center)
        painter.rotate(self.board_rotation)
        painter.translate(-center)

        # Vẽ các vùng điểm
        for i in range(20):
            angle_start = i * SEGMENT_ANGLE - 99
            angle_span = SEGMENT_ANGLE
            color_light = QColor(238, 238, 238)
            color_dark = QColor(30, 30, 30)
            color_red = QColor(220, 20, 60)
            color_green = QColor(34, 139, 34)

            # Double (ngoài cùng)
            painter.setBrush(QBrush(color_red if i % 2 == 0 else color_green))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawPie(
                center.x() - DOUBLE_OUTER_RADIUS,
                center.y() - DOUBLE_OUTER_RADIUS,
                DOUBLE_OUTER_RADIUS * 2,
                DOUBLE_OUTER_RADIUS * 2,
                angle_start * 16,
                angle_span * 16,
            )

            # Single outer
            painter.setBrush(QBrush(color_light if i % 2 == 0 else color_dark))
            painter.drawPie(
                center.x() - TRIPLE_OUTER_RADIUS,
                center.y() - TRIPLE_OUTER_RADIUS,
                TRIPLE_OUTER_RADIUS * 2,
                TRIPLE_OUTER_RADIUS * 2,
                angle_start * 16,
                angle_span * 16,
            )

            # Triple (giữa)
            painter.setBrush(QBrush(color_red if i % 2 == 0 else color_green))
            painter.drawPie(
                center.x() - TRIPLE_OUTER_RADIUS,
                center.y() - TRIPLE_OUTER_RADIUS,
                TRIPLE_OUTER_RADIUS * 2,
                TRIPLE_OUTER_RADIUS * 2,
                angle_start * 16,
                angle_span * 16,
            )

            # Single inner
            painter.setBrush(QBrush(color_light if i % 2 == 0 else color_dark))
            painter.drawPie(
                center.x() - TRIPLE_INNER_RADIUS,
                center.y() - TRIPLE_INNER_RADIUS,
                TRIPLE_INNER_RADIUS * 2,
                TRIPLE_INNER_RADIUS * 2,
                angle_start * 16,
                angle_span * 16,
            )

        # Bull's eye
        painter.setBrush(QBrush(color_green))
        painter.drawEllipse(center, BULL_OUTER_RADIUS, BULL_OUTER_RADIUS)
        painter.setBrush(QBrush(color_red))
        painter.drawEllipse(center, BULL_RADIUS, BULL_RADIUS)

        # Vẽ số
        painter.setPen(QPen(Qt.black, 2))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        for i, number in enumerate(BOARD_NUMBERS):
            angle_rad = math.radians(i * SEGMENT_ANGLE - 90)
            text_x = int(center.x() + (DOUBLE_OUTER_RADIUS + 20) * math.cos(angle_rad))
            text_y = int(center.y() + (DOUBLE_OUTER_RADIUS + 20) * math.sin(angle_rad))
            rect = QRect(text_x - 10, text_y - 10, 20, 20)
            painter.drawText(rect, Qt.AlignCenter, str(number))

        # Phi tiêu đã ném
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(Qt.yellow))
        for dart_pos in self.darts_on_board:
            painter.drawEllipse(dart_pos, 5, 5)

    def mousePressEvent(self, event):
        if self.isEnabled():
            self.dart_thrown_signal.emit(event.x(), event.y())

    def rotate_board(self):
        self.board_rotation = (self.board_rotation + SEGMENT_ANGLE) % 360
        self.update()

    def add_dart(self, x, y):
        self.darts_on_board.append(QPoint(x, y))
        self.update()

    def clear_darts(self):
        self.darts_on_board.clear()
        self.update()

    def reset(self):
        self.clear_darts()
        self.board_rotation = 0
        self.update()


class DartBoardView(QWidget):
    """
    Giao diện chính trận đấu.
    """

    def __init__(self, username, opponent_username, tcp_client, is_challenger=False):
        super().__init__()
        self.username = username
        self.opponent_username = opponent_username
        self.tcp_client = tcp_client
        self.is_challenger = is_challenger

        self.my_turn = is_challenger
        self.is_game_active = True
        self.darts_left_in_turn = 3
        self.turns_played = 0
        self.MAX_TURNS = 3
        self.my_score = 501
        self.opponent_score = 501

        self.setWindowTitle(f"{self.username} vs {self.opponent_username}")
        self.setFixedSize(900, 700)

        # Timer
        self.turn_timer = QTimer(self)
        self.turn_timer.timeout.connect(self.on_time_out)
        self.time_left = 30

        self.timer_display = QTimer(self)
        self.timer_display.timeout.connect(self.update_timer_display)

        # UI
        self.setup_ui()
        self.update_ui_state()

        # TCP
        self.tcp_client.on_message = self.on_server_message

        if self.my_turn:
            self.start_turn_timer()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.addLayout(self.create_score_panel())
        self.dart_board = DartBoardWidget()
        self.dart_board.dart_thrown_signal.connect(self.on_dart_thrown)
        main_layout.addWidget(self.dart_board, alignment=Qt.AlignCenter)
        main_layout.addLayout(self.create_control_panel())
        self.setLayout(main_layout)

    def create_score_panel(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Bạn: {self.username}"))
        self.my_score_label = QLabel(f"Điểm: {self.my_score}")
        self.my_score_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.my_score_label)
        layout.addStretch()
        layout.addWidget(QLabel(f"Đối thủ: {self.opponent_username}"))
        self.opponent_score_label = QLabel(f"Điểm: {self.opponent_score}")
        self.opponent_score_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.opponent_score_label)
        layout.addStretch()
        return layout

    def create_control_panel(self):
        layout = QVBoxLayout()
        self.turn_indicator_label = QLabel()
        layout.addWidget(self.turn_indicator_label)
        self.timer_label = QLabel()
        layout.addWidget(self.timer_label)
        self.darts_left_label = QLabel()
        layout.addWidget(self.darts_left_label)
        layout.addStretch()
        self.throw_btn = QPushButton("Ném")
        self.throw_btn.clicked.connect(self.on_throw_button_click)
        layout.addWidget(self.throw_btn)
        self.rotate_btn = QPushButton("Xoay bảng")
        self.rotate_btn.clicked.connect(self.on_rotate_button_click)
        layout.addWidget(self.rotate_btn)
        layout.addStretch()
        self.exit_btn = QPushButton("Thoát")
        self.exit_btn.clicked.connect(self.on_exit_button_click)
        layout.addWidget(self.exit_btn)
        return layout

    def update_ui_state(self):
        self.turn_indicator_label.setText(
            "Lượt của bạn" if self.my_turn else f"Lượt của {self.opponent_username}"
        )
        self.throw_btn.setEnabled(self.my_turn and self.is_game_active)
        self.rotate_btn.setEnabled(not self.my_turn and self.is_game_active)
        self.dart_board.setEnabled(self.my_turn and self.is_game_active)
        self.darts_left_label.setText(f"Phi tiêu còn lại: {self.darts_left_in_turn}")
        self.my_score_label.setText(f"Điểm: {self.my_score}")
        self.opponent_score_label.setText(f"Điểm: {self.opponent_score}")
        self.timer_label.setText(f"Thời gian: {self.time_left}s")

    def start_turn_timer(self):
        self.time_left = 30
        self.update_ui_state()
        self.turn_timer.start(30000)
        self.timer_display.start(1000)

    def stop_turn_timer(self):
        self.turn_timer.stop()
        self.timer_display.stop()

    def update_timer_display(self):
        self.time_left -= 1
        if self.time_left < 0:
            self.time_left = 0
        self.timer_label.setText(f"Thời gian: {self.time_left}s")

    def on_time_out(self):
        QMessageBox.information(self, "Hết giờ", "Bạn đã hết giờ. Mất lượt này.")
        self.tcp_client.send_object(
            {
                "command": "player_threw",
                "body": {"player": self.username, "x": -1, "y": -1},
            }
        )
        self.switch_turn()

    def switch_turn(self):
        self.my_turn = not self.my_turn
        self.darts_left_in_turn = 3
        if self.my_turn:
            self.dart_board.clear_darts()
            self.start_turn_timer()
        else:
            self.stop_turn_timer()
        self.update_ui_state()

    def on_throw_button_click(self):
        if self.my_turn:
            self.throw_btn.setText("Chọn vị trí...")
            self.throw_btn.setEnabled(False)

    @pyqtSlot(int, int)
    def on_dart_thrown(self, x, y):
        if not self.my_turn or not self.is_game_active:
            return
        self.dart_board.setEnabled(False)
        self.throw_btn.setText("Ném")
        self.throw_btn.setEnabled(True)
        self.tcp_client.send_object(
            {
                "command": "player_threw",
                "body": {"player": self.username, "x": x, "y": y},
            }
        )

    def on_rotate_button_click(self):
        if not self.my_turn and self.is_game_active:
            self.dart_board.rotate_board()
            self.tcp_client.send_object(
                {
                    "command": "board_rotated",
                    "body": {
                        "player": self.username,
                        "rotation": self.dart_board.board_rotation,
                    },
                }
            )

    def on_exit_button_click(self):
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc muốn thoát?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.tcp_client.send_object(
                {"command": "player_exited", "body": {"player": self.username}}
            )
            self.close()

    def on_server_message(self, data: dict):
        """Xử lý server gửi về"""
        command = data.get("command")
        body = data.get("body", {})
        if command == "throw_result":
            player = body.get("player")
            x, y, score = body.get("x", -1), body.get("y", -1), body.get("score", 0)
            if player == self.username:
                self.my_score -= score
            else:
                self.opponent_score -= score
            if x != -1:
                self.dart_board.add_dart(x, y)
            self.darts_left_in_turn -= 1
            if self.darts_left_in_turn <= 0:
                self.switch_turn()
            self.update_ui_state()
        elif command == "opponent_exited":
            QMessageBox.information(
                self,
                "Kết thúc",
                f"{self.opponent_username} đã thoát.",
            )
            self.close()
        elif command == "game_over":
            winner = body.get("winner")
            QMessageBox.information(self, "Kết thúc", f"Người thắng: {winner}")
            self.is_game_active = False
            self.stop_turn_timer()
