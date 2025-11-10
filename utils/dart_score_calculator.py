import math
from typing import List, Optional, Tuple

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QColor


class DartScoreCalculator:
    """
    Lớp xử lý logic tính điểm cho dartboard.
    Tách biệt logic tính toán khỏi UI để dễ test và maintain.
    """

    # Định nghĩa segments
    # Format: [điểm_số, góc_độ, màu_sắc]
    DEFAULT_SEGMENTS = [
        [1, 36, QColor("#85C1E9")],
        [5, 36, QColor("#FFEAA7")],
        [1, 36, QColor("#96CEB4")],
        [10, 36, QColor("#F7DC6F")],
        [1, 36, QColor("#98D8C8")],
        [25, 36, QColor("#DDA0DD")],
        [1, 36, QColor("#4ECDC4")],
        [10, 36, QColor("#BB8FCE")],
        [1, 36, QColor("#45B7D1")],
        [50, 36, QColor("#FF6B6B")],
    ]

    # Điểm số cho bullseye (tâm)
    BULLSEYE_SCORE = 100

    # Kích thước dartboard chuẩn để tính điểm (logic size)
    STANDARD_RADIUS = 200.0

    # Bán kính bullseye trên dartboard chuẩn (8% của STANDARD_RADIUS)
    BULLSEYE_RADIUS = STANDARD_RADIUS * 0  # 16 pixels

    def __init__(self, segments: Optional[List[List]] = None):
        """
        Khởi tạo calculator với segments tùy chỉnh hoặc mặc định.

        Args:
            segments: List các segment theo format [score, angle_width, color]
                     Nếu None, sử dụng DEFAULT_SEGMENTS
        """
        self.segments = segments if segments is not None else self.DEFAULT_SEGMENTS
        self._validate_segments()

    def _validate_segments(self):
        """Kiểm tra tính hợp lệ của segments"""
        if not self.segments:
            raise ValueError("Segments không được rỗng")

        total_angle = sum(seg[1] for seg in self.segments)
        if not math.isclose(total_angle, 360.0, rel_tol=1e-5):
            raise ValueError(
                f"Tổng góc của segments phải bằng 360°, nhưng là {total_angle}°"
            )

    def calculate_score(
        self, dx: float, dy: float, rotation_angle: float, max_radius: float
    ) -> Tuple[int, str]:
        """
        Tính điểm dựa trên vị trí click (dx, dy) từ tâm.

        Args:
            dx: Khoảng cách x từ tâm (pixel)
            dy: Khoảng cách y từ tâm (pixel)
            rotation_angle: Góc xoay hiện tại của dartboard (degrees)
            max_radius: Bán kính tối đa của dartboard (pixel)

        Returns:
            Tuple (score, reason):
                - score: Điểm số (int)
                - reason: Lý do ("bullseye", "segment", "miss")
        """
        # Normalize tọa độ về dartboard chuẩn để tính điểm nhất quán
        # Scale factor: chuyển từ kích thước hiện tại về kích thước chuẩn
        scale_factor = self.STANDARD_RADIUS / max_radius
        dx_normalized = dx * scale_factor
        dy_normalized = dy * scale_factor

        # Tính khoảng cách từ tâm trên dartboard chuẩn
        distance_from_center = math.sqrt(dx_normalized**2 + dy_normalized**2)

        # 1. Kiểm tra Bullseye (tâm)
        if distance_from_center < self.BULLSEYE_RADIUS:
            return self.BULLSEYE_SCORE, "bullseye"

        # 2. Kiểm tra xem có trượt không (ngoài bảng)
        if distance_from_center > self.STANDARD_RADIUS:
            return 0, "miss"

        # 3. Xác định segment dựa trên góc
        angle_rad = math.atan2(dy_normalized, dx_normalized)
        angle_deg = math.degrees(angle_rad)

        # Chuyển từ [-180, 180] sang [0, 360]
        if angle_deg < 0:
            angle_deg += 360

        # Điều chỉnh góc theo rotation hiện tại của dartboard
        adjusted_angle = (angle_deg - (rotation_angle % 360)) % 360

        # Tìm segment tương ứng và lấy điểm
        base_score = self._get_segment_score(adjusted_angle)

        return base_score, "segment"

    def _get_segment_score(self, angle: float) -> int:
        """
        Lấy điểm của segment dựa trên góc.

        Args:
            angle: Góc đã được normalize [0, 360)

        Returns:
            Điểm số của segment
        """
        current_angle = 0
        for score, angle_width, _ in self.segments:
            if current_angle <= angle < current_angle + angle_width:
                return score
            current_angle += angle_width

        # Fallback - trường hợp góc 360 (do floating point)
        return self.segments[0][0]

    def get_segment_at_angle(self, angle: float) -> Tuple[int, int, QColor]:
        """
        Lấy thông tin segment tại góc cho trước.

        Args:
            angle: Góc [0, 360)

        Returns:
            Tuple (score, angle_width, color) của segment
        """
        current_angle = 0
        for segment in self.segments:
            score, angle_width, color = segment
            if current_angle <= angle < current_angle + angle_width:
                return score, angle_width, color
            current_angle += angle_width

        # Fallback
        return self.segments[0]

    def transform_hit_point(
        self, dx: float, dy: float, rotation_angle: float
    ) -> QPointF:
        """
        Biến đổi tọa độ hit point để hiển thị đúng trên dartboard đã xoay.
        Xoay ngược lại -rotation_angle để tọa độ local đúng với hệ tọa độ vẽ.

        Args:
            dx: Khoảng cách x từ tâm (pixel)
            dy: Khoảng cách y từ tâm (pixel)
            rotation_angle: Góc xoay hiện tại của dartboard (degrees)

        Returns:
            QPointF với tọa độ đã được biến đổi
        """
        theta = math.radians(-rotation_angle)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        x_local = dx * cos_t - dy * sin_t
        y_local = dx * sin_t + dy * cos_t

        return QPointF(x_local, y_local)

    def is_in_bullseye(self, dx: float, dy: float, max_radius: float) -> bool:
        """
        Kiểm tra xem điểm có nằm trong vùng bullseye không.

        Args:
            dx: Khoảng cách x từ tâm
            dy: Khoảng cách y từ tâm
            max_radius: Bán kính tối đa của dartboard

        Returns:
            True nếu trong bullseye, False nếu không
        """
        # Normalize về dartboard chuẩn
        scale_factor = self.STANDARD_RADIUS / max_radius
        dx_normalized = dx * scale_factor
        dy_normalized = dy * scale_factor
        distance = math.sqrt(dx_normalized**2 + dy_normalized**2)
        return distance < self.BULLSEYE_RADIUS

    def is_out_of_bounds(self, dx: float, dy: float, max_radius: float) -> bool:
        """
        Kiểm tra xem điểm có nằm ngoài dartboard không.

        Args:
            dx: Khoảng cách x từ tâm
            dy: Khoảng cách y từ tâm
            max_radius: Bán kính tối đa của dartboard

        Returns:
            True nếu ngoài dartboard, False nếu không
        """
        # Normalize về dartboard chuẩn
        scale_factor = self.STANDARD_RADIUS / max_radius
        dx_normalized = dx * scale_factor
        dy_normalized = dy * scale_factor
        distance = math.sqrt(dx_normalized**2 + dy_normalized**2)
        return distance > self.STANDARD_RADIUS

    def get_segments(self) -> List[List]:
        """Trả về danh sách segments hiện tại"""
        return self.segments

    def set_segments(self, segments: List[List]):
        """
        Cập nhật segments mới.

        Args:
            segments: List mới của segments

        Raises:
            ValueError: Nếu segments không hợp lệ
        """
        self.segments = segments
        self._validate_segments()
