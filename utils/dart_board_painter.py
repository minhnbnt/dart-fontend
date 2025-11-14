"""
DartBoardPainter - Class xử lý việc vẽ dartboard.
Tách biệt logic rendering khỏi widget để dễ test và maintain.
"""

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen


class DartBoardPainter:
    """
    Class xử lý việc vẽ dartboard và các thành phần liên quan.
    """

    def __init__(self, score_calculator):
        """
        Khởi tạo painter với score calculator.

        Args:
            score_calculator: Instance của DartScoreCalculator
        """
        self.score_calculator = score_calculator

    def draw_dartboard(
        self,
        painter: QPainter,
        center_x: float,
        center_y: float,
        radius: float,
        rotation_angle: float,
    ):
        """
        Vẽ toàn bộ dartboard.

        Args:
            painter: QPainter instance
            center_x: Tọa độ x của tâm
            center_y: Tọa độ y của tâm
            radius: Bán kính của dartboard
            rotation_angle: Góc xoay hiện tại
        """
        painter.save()

        # Dịch gốc tọa độ đến tâm và xoay bảng
        painter.translate(center_x, center_y)
        painter.rotate(rotation_angle % 360)

        # Vẽ các segments
        self._draw_segments(painter, radius)

        # Vẽ bullseye
        self._draw_bullseye(painter, radius)

        # Vẽ viền ngoài
        self._draw_outer_border(painter, radius)

        painter.restore()

    def _draw_segments(self, painter: QPainter, radius: float):
        """
        Vẽ các segments của dartboard.

        Args:
            painter: QPainter instance
            radius: Bán kính của dartboard
        """
        current_angle = 0
        for score, angle_width, color in self.score_calculator.get_segments():
            start_angle = current_angle * 16  # PyQt sử dụng 1/16 độ
            span_angle = angle_width * 16

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 2))
            painter.drawPie(
                int(-radius),
                int(-radius),
                int(radius * 2),
                int(radius * 2),
                int(start_angle),
                int(span_angle),
            )

            current_angle += angle_width

    def _draw_bullseye(self, painter: QPainter, radius: float):
        """
        Vẽ bullseye (tâm) của dartboard.

        Args:
            painter: QPainter instance
            radius: Bán kính của dartboard
        """
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFD700")))  # Vàng gold

        # Scale bullseye radius theo tỷ lệ dartboard hiện tại
        bullseye_radius = radius * (
            self.score_calculator.BULLSEYE_RADIUS
            / self.score_calculator.STANDARD_RADIUS
        )

        # Vẽ hình tròn bullseye
        painter.drawEllipse(QPointF(0, 0), bullseye_radius, bullseye_radius)

        # Vẽ số "100" ở giữa bullseye
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        text_rect = QRectF(
            -bullseye_radius, -bullseye_radius, bullseye_radius * 2, bullseye_radius * 2
        )
        painter.setPen(QPen(Qt.black, 2))
        painter.drawText(text_rect, Qt.AlignCenter, "100")

    def _draw_outer_border(self, painter: QPainter, radius: float):
        """
        Vẽ viền ngoài của dartboard.

        Args:
            painter: QPainter instance
            radius: Bán kính của dartboard
        """
        painter.setPen(QPen(QColor("#333333"), 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            int(-radius), int(-radius), int(radius * 2), int(radius * 2)
        )

    def draw_segment_labels(
        self,
        painter: QPainter,
        center_x: float,
        center_y: float,
        radius: float,
        rotation_angle: float,
    ):
        """
        Vẽ các số điểm quanh dartboard.

        Args:
            painter: QPainter instance
            center_x: Tọa độ x của tâm
            center_y: Tọa độ y của tâm
            radius: Bán kính của dartboard
            rotation_angle: Góc xoay hiện tại
        """
        painter.save()
        painter.translate(center_x, center_y)

        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)

        current_angle = 0
        for score, angle_width, color in self.score_calculator.get_segments():
            # Tính vị trí giữa segment để đặt số
            mid_angle = current_angle + angle_width / 2 + (rotation_angle % 360)
            angle_rad = math.radians(mid_angle)
            text_radius = radius - 30
            x = text_radius * math.cos(angle_rad)
            y = text_radius * math.sin(angle_rad)

            text = str(score)

            painter.save()
            painter.translate(x, y)
            # Xoay text để dễ đọc - vuông góc với hướng tâm ra ngoài
            painter.rotate(mid_angle + 90)

            # Sử dụng QRectF để căn giữa text tự động
            rect_size = 40
            text_rect = QRectF(-rect_size / 2, -rect_size / 2, rect_size, rect_size)

            # Vẽ chữ với viền đen để dễ đọc
            painter.setPen(QPen(Qt.black, 3))
            painter.drawText(text_rect, Qt.AlignCenter, text)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(text_rect, Qt.AlignCenter, text)
            painter.restore()

            current_angle += angle_width

        painter.restore()

    def draw_opponent_cursor(
        self,
        painter: QPainter,
        opponent_cursor: QPointF,
        center_x: float,
        center_y: float,
        rotation_angle: float,
    ):
        """
        Vẽ cursor của đối thủ.

        Args:
            painter: QPainter instance
            opponent_cursor: QPointF vị trí cursor
            center_x: Tọa độ x của tâm
            center_y: Tọa độ y của tâm
            rotation_angle: Góc xoay hiện tại
        """
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(rotation_angle % 360)

        # Vẽ crosshair cursor của đối thủ
        painter.setPen(QPen(QColor("#FF6B35"), 3))  # Màu cam nổi bật
        cursor_size = 15
        x, y = opponent_cursor.x(), opponent_cursor.y()

        # Vẽ dấu +
        painter.drawLine(
            int(x - cursor_size), int(y), int(x + cursor_size), int(y)
        )  # Ngang
        painter.drawLine(
            int(x), int(y - cursor_size), int(x), int(y + cursor_size)
        )  # Dọc

        # Vẽ vòng tròn nhỏ ở giữa
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#FF6B35"), 2))
        painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)

        painter.restore()

    def draw_hit_point(
        self,
        painter: QPainter,
        hit_point: QPointF,
        center_x: float,
        center_y: float,
        rotation_angle: float,
    ):
        """
        Vẽ điểm đánh trúng (chấm đỏ).

        Args:
            painter: QPainter instance
            hit_point: QPointF vị trí chấm đỏ
            center_x: Tọa độ x của tâm
            center_y: Tọa độ y của tâm
            rotation_angle: Góc xoay hiện tại
        """
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(rotation_angle % 360)

        # Vẽ viền trắng để nổi bật
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(Qt.black, 2))
        r = 8  # bán kính chấm lớn hơn
        painter.drawEllipse(hit_point, r, r)

        # Vẽ chấm đỏ bên trong
        painter.setBrush(QBrush(Qt.red))
        painter.setPen(Qt.NoPen)
        r_inner = 5
        painter.drawEllipse(hit_point, r_inner, r_inner)

        painter.restore()

    def draw_rotation_info(
        self,
        painter: QPainter,
        width: int,
        height: int,
        rotation_angle: float,
        rotation_speed: float,
    ):
        """
        Vẽ thông tin về trạng thái quay.

        Args:
            painter: QPainter instance
            width: Chiều rộng của widget
            height: Chiều cao của widget
            rotation_angle: Góc xoay hiện tại
            rotation_speed: Tốc độ quay
        """
        painter.save()
        painter.resetTransform()

        # Vẽ khung thông tin ở góc trên phải
        info_x = width - 180
        info_y = 20
        info_width = 160
        info_height = 60

        # Vẽ nền với shadow
        painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(info_x + 2, info_y + 2, info_width, info_height, 8, 8)

        # Vẽ nền chính
        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawRoundedRect(info_x, info_y, info_width, info_height, 8, 8)

        # Vẽ text thông tin
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 10, QFont.Bold))

        # Tên game mode
        painter.drawText(info_x + 10, info_y + 20, "🎯 BẢNG QUAY")

        # Tốc độ quay
        painter.setFont(QFont("Arial", 9))
        speed_text = f"Tốc độ: {rotation_speed:.1f}°/khung"
        painter.drawText(info_x + 10, info_y + 40, speed_text)

        # Góc hiện tại
        angle_text = f"Góc: {int(rotation_angle)}°"
        painter.drawText(info_x + 10, info_y + 55, angle_text)

        painter.restore()
