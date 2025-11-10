import math
import random
import sys
import weakref

from PyQt5.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from utils.client_event_helper import ClientEventHelper
from utils.client_helper import ClientHelper
from utils.dart_score_calculator import DartScoreCalculator
from utils.sync_await import sync_await

# Game constants
MAX_THROWS_PER_PLAYER = 3  # Số lượt ném tối đa cho mỗi người chơi


class DartBoardWidget(QWidget):
    # Tín hiệu được phát ra khi người dùng nhấp vào bảng, kèm theo điểm số
    throw_made_signal = pyqtSignal(int)
    # Tín hiệu gửi thông tin chi tiết về cú ném (điểm, vị trí click)
    # score, dx, dy, rotation_angle
    throw_detail_signal = pyqtSignal(int, float, float, float)
    # Tín hiệu gửi thông tin di chuyển chuột (realtime)
    mouse_move_signal = pyqtSignal(float, float)  # x, y relative to center

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rotation_angle = 0
        self.is_enabled = True  # Flag để kiểm tra có cho phép click không
        self.throw_delay_active = False  # Flag để chặn ném trong 5s đầu
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #f0f0f0; border: 2px solid #333; border-radius: 5px;"
        )

        # Khởi tạo score calculator với segments mặc định
        self.score_calculator = DartScoreCalculator()

        # Vị trí chấm đỏ (tọa độ theo hệ tọa độ *chưa xoay* của bảng, tính từ tâm)
        # None nghĩa là chưa có chấm hiển thị
        self.hit_point = None

        # Vị trí cursor của đối thủ (để hiển thị realtime)
        self.opponent_cursor = None

        # Flag để track cursor hide timer
        self.cursor_hide_scheduled = False

        # Animation cho quay bánh xe
        self.rotation_animation = QPropertyAnimation(self, b"rotation_angle")
        self.rotation_animation.setDuration(3000)  # 3 giây
        self.rotation_animation.setEasingCurve(QEasingCurve.OutQuint)

        # Trạng thái quay
        self.is_spinning = False

        # Hệ thống quay liên tục (TẠM THỜI TẮT)
        self.continuous_rotation_timer = QTimer()
        self.continuous_rotation_timer.timeout.connect(self.update_rotation)
        # self.continuous_rotation_timer.start(50)  # Update mỗi 50ms = 20 FPS
        self.rotation_speed = 0  # Tắt rotation (was 1.0)

        # Animation xoay mượt với chậm dần
        self.spin_animation = QPropertyAnimation(self, b"rotation_angle")
        self.spin_animation.setEasingCurve(QEasingCurve.OutCubic)  # Chậm dần tự nhiên
        # Kết nối valueChanged để force update UI
        self.spin_animation.valueChanged.connect(lambda: self.update())

    @pyqtProperty(float)
    def rotation_angle(self):
        return self._rotation_angle

    @rotation_angle.setter
    def rotation_angle(self, value):
        # Lưu giá trị thô để animation hoạt động với góc lớn (>360°)
        # Chỉ normalize khi vẽ
        print(
            f"🔄 rotation_angle setter called: {self._rotation_angle:.1f}° → {value:.1f}°"
        )
        self._rotation_angle = value
        self.update()

    def update_rotation(self):
        """Cập nhật góc xoay liên tục"""
        if not self.is_spinning:
            self._rotation_angle = (self._rotation_angle + self.rotation_speed) % 360
            self.update()

    def trigger_spin(self, rotation_amount=720, duration=3000):
        """
        Kích hoạt xoay mượt với chậm dần tự nhiên
        Args:
            rotation_amount: Số độ sẽ xoay (mặc định 720° = 2 vòng)
            duration: Thời gian xoay tính bằng ms (mặc định 3000ms = 3 giây)
        """
        # Dừng animation hiện tại nếu có
        if self.spin_animation.state() == QPropertyAnimation.Running:
            self.spin_animation.stop()

        # Ngắt kết nối finished signal cũ (nếu có)
        try:
            self.spin_animation.finished.disconnect()
        except:
            pass

        # Thiết lập animation
        start_angle = self._rotation_angle
        # KHÔNG dùng modulo - để animation xoay đủ số độ
        end_angle = start_angle + rotation_amount

        print(
            f"🌀 Spin: {start_angle:.1f}° → {end_angle:.1f}° ({rotation_amount}° in {duration}ms)"
        )

        self.spin_animation.setDuration(duration)
        self.spin_animation.setStartValue(start_angle)
        self.spin_animation.setEndValue(end_angle)

        # Sau khi animation xong, normalize góc về [0, 360)
        def on_finished():
            self._rotation_angle = self._rotation_angle % 360
            print(f"Animation finished. Final angle: {self._rotation_angle:.1f}°")

        self.spin_animation.finished.connect(on_finished)
        self.spin_animation.start()

        print(f"Animation state: {self.spin_animation.state()}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.save()  # Save state trước khi transform

        rect = self.rect()
        side = min(rect.width(), rect.height())
        center_x, center_y = rect.width() / 2, rect.height() / 2
        radius = side / 2 - 20

        # Dịch gốc tọa độ đến tâm và xoay bảng
        # Normalize góc khi vẽ
        painter.translate(center_x, center_y)
        painter.rotate(self._rotation_angle % 360)

        # Vẽ các vùng với góc độ khác nhau
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

        # Vẽ tâm bullseye
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#FFD700")))  # Vàng gold
        # Scale bullseye radius theo tỷ lệ dartboard hiện tại
        bullseye_radius = radius * (
            self.score_calculator.BULLSEYE_RADIUS
            / self.score_calculator.STANDARD_RADIUS
        )
        # Dùng QPointF và radius để vẽ hình tròn hoàn hảo
        painter.drawEllipse(QPointF(0, 0), bullseye_radius, bullseye_radius)

        # Vẽ số "100" ở giữa bullseye
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        text_rect = QRectF(
            -bullseye_radius, -bullseye_radius, bullseye_radius * 2, bullseye_radius * 2
        )
        painter.setPen(QPen(Qt.black, 2))
        painter.drawText(text_rect, Qt.AlignCenter, "100")

        # Vẽ viền ngoài bảng
        painter.setPen(QPen(QColor("#333333"), 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            int(-radius), int(-radius), int(radius * 2), int(radius * 2)
        )

        # --- VẼ cursor của đối thủ (vẽ trước chấm đỏ) ---
        if self.opponent_cursor is not None:
            # Vẽ crosshair cursor của đối thủ
            painter.setPen(QPen(QColor("#FF6B35"), 3))  # Màu cam nổi bật
            cursor_size = 15
            x, y = self.opponent_cursor.x(), self.opponent_cursor.y()

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

        # --- VẼ chấm đỏ nếu có (vẽ sau cùng để nằm trên các vùng) ---
        if self.hit_point is not None:
            # hit_point lưu là QPointF(x, y) tính từ tâm *trước khi xoay bảng* (đã biến đổi inverse khi click)
            # Vẽ viền trắng để nổi bật
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(Qt.black, 2))
            r = 8  # bán kính chấm lớn hơn
            painter.drawEllipse(self.hit_point, r, r)

            # Vẽ chấm đỏ bên trong
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(Qt.NoPen)
            r_inner = 5
            painter.drawEllipse(self.hit_point, r_inner, r_inner)

        painter.restore()  # Reset transform

        # Vẽ chữ số quanh vòng tròn (SAU KHI restore để không bị ảnh hưởng rotation)
        painter.save()
        painter.translate(center_x, center_y)

        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)

        current_angle = 0
        for score, angle_width, color in self.score_calculator.get_segments():
            # Tính vị trí giữa segment để đặt số
            # Cộng thêm rotation_angle để số khớp với segment đã xoay
            mid_angle = current_angle + angle_width / 2 + (self._rotation_angle % 360)
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
            rect_size = 40  # Kích thước rect chứa text
            text_rect = QRectF(-rect_size / 2, -rect_size / 2, rect_size, rect_size)

            # Vẽ chữ với viền đen để dễ đọc
            painter.setPen(QPen(Qt.black, 3))
            painter.drawText(text_rect, Qt.AlignCenter, text)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(text_rect, Qt.AlignCenter, text)
            painter.restore()

            current_angle += angle_width

        painter.restore()

        # Hiển thị thông tin về bảng quay
        self.draw_rotation_info(painter)

    def draw_rotation_info(self, painter):
        """Hiển thị thông tin về trạng thái quay"""
        # Draw info fixed to widget coordinates (not rotated with the board)
        painter.save()
        # Reset any transforms (the paintEvent applied translate+rotate earlier)
        painter.resetTransform()

        # Vẽ khung thông tin ở góc trên phải (widget coords)
        info_x = self.width() - 180
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
        speed_text = f"Tốc độ: {self.rotation_speed:.1f}°/khung"
        painter.drawText(info_x + 10, info_y + 40, speed_text)

        # Góc hiện tại
        angle_text = f"Góc: {int(self._rotation_angle)}°"
        painter.drawText(info_x + 10, info_y + 55, angle_text)

        painter.restore()

    def resizeEvent(self, event):
        # Reposition throw icon at bottom center when resized (if not animating)
        super().resizeEvent(event)
        pass

    def apply_physics_to_throw(self, click_x, click_y, throw_power):
        """Áp dụng physics (độ chính xác) lên vị trí click và trả về final coords"""
        # Lực ném ảnh hưởng đến độ chính xác
        max_power = 100.0
        power_accuracy = min(max(throw_power / max_power, 0.0), 1.0)
        accuracy_factor = 0.3 + (power_accuracy * 0.7)  # 0.3-1.0

        # 3. Random deviation dựa trên độ chính xác
        max_deviation = 30 * (1 - accuracy_factor)
        deviation_x = random.uniform(-max_deviation, max_deviation)
        deviation_y = random.uniform(-max_deviation, max_deviation)

        # Áp dụng hiệu ứng
        final_x = click_x + deviation_x
        final_y = click_y + deviation_y

        return final_x, final_y

    def _simulate_throw_from_center(self, throw_power=100):
        """Simulate a throw that starts from bottom-center aiming to the board center.
        After simulation, this stores hit_point and emits throw signals.
        """
        # Aim at the center (0,0) in board-local coords
        click_x, click_y = 0.0, 0.0
        final_x, final_y = self.apply_physics_to_throw(click_x, click_y, throw_power)

        # Determine score using same logic as mouseReleaseEvent
        side = min(self.width(), self.height())
        max_radius = side / 2 - 20
        distance_from_center = math.sqrt(final_x**2 + final_y**2)

        # 1. Bullseye
        if distance_from_center < max_radius * 0.08:
            score = 100
            # Show score on the dart icon briefly
            try:
                self.display_score_on_icon(score)
            except Exception:
                pass

            self._store_hit_point(final_x, final_y)
            self.throw_made_signal.emit(score)
            self.throw_detail_signal.emit(score, final_x, final_y, self._rotation_angle)
            return

        # 2. Outside board
        if distance_from_center > max_radius:
            score = 0
            try:
                self.display_score_on_icon(score)
            except Exception:
                pass
            self._store_hit_point(final_x, final_y)
            self.throw_made_signal.emit(score)
            self.throw_detail_signal.emit(score, final_x, final_y, self._rotation_angle)
            return

        # 3. Segment based on angle (consider rotation)
        angle_rad = math.atan2(final_y, final_x)
        angle_deg = math.degrees(angle_rad)
        adjusted_angle = (angle_deg + self._rotation_angle) % 360
        if adjusted_angle < 0:
            adjusted_angle += 360

        score = self._get_segment_score(adjusted_angle)

        # 4. Apply ring multipliers
        radius_ratio = distance_from_center / max_radius
        if radius_ratio < 0.3:
            score = score * 2
        elif radius_ratio < 0.7:
            score = score
        elif radius_ratio < 0.9:
            score = score * 3
        else:
            score = max(score // 2, 1)

        # Store and emit
        try:
            self.display_score_on_icon(score)
        except Exception:
            pass
        self._store_hit_point(final_x, final_y)
        self.throw_made_signal.emit(score)
        self.throw_detail_signal.emit(score, final_x, final_y, self._rotation_angle)

    def mouseMoveEvent(self, event):
        """Track mouse movement để đồng bộ với đối thủ"""
        center = QPointF(self.width() / 2, self.height() / 2)
        mouse_pos = QPointF(event.x(), event.y())
        dx = mouse_pos.x() - center.x()
        dy = mouse_pos.y() - center.y()

        # Chỉ emit signal nếu trong vùng bảng
        side = min(self.width(), self.height())
        max_radius = side / 2 - 20
        distance = math.sqrt(dx**2 + dy**2)

        if distance <= max_radius * 1.1:  # Cho phép một chút outside bảng
            self.mouse_move_signal.emit(dx, dy)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Chỉ cần xử lý click - không cần charge power nữa
            pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Kiểm tra xem có được phép click không
            if not self.is_enabled:
                return
            # Kiểm tra xem có đang trong thời gian delay không
            if self.throw_delay_active:
                return
            # Tính toán vị trí click
            center = QPointF(self.width() / 2, self.height() / 2)
            click_pos = QPointF(event.x(), event.y())
            dx = click_pos.x() - center.x()
            dy = click_pos.y() - center.y()

            # Xác định bán kính tối đa của bảng
            side = min(self.width(), self.height())
            max_radius = side / 2 - 20

            # Sử dụng score calculator để tính điểm
            score, reason = self.score_calculator.calculate_score(
                dx, dy, self._rotation_angle, max_radius
            )

            # Lưu vị trí chấm nếu không phải miss
            if reason != "miss":
                self._store_hit_point(dx, dy)

            # Emit signals
            self.throw_made_signal.emit(score)
            self.throw_detail_signal.emit(score, dx, dy, self._rotation_angle)

    def _store_hit_point(self, dx, dy):
        """
        Lưu hit_point sao cho khi paintEvent thực hiện translate->rotate(self._rotation_angle)
        thì vị trí chấm sẽ nằm đúng vị trí người click trên màn hình.

        Sử dụng score_calculator để biến đổi tọa độ.
        """
        # Sử dụng score calculator để transform hit point
        self.hit_point = self.score_calculator.transform_hit_point(
            dx, dy, self._rotation_angle
        )
        self.update()
        # Tự động ẩn chấm đỏ sau 2 giây
        QTimer.singleShot(2000, self.clear_hit_point)

    def clear_hit_point(self):
        self.hit_point = None
        self.update()

    def show_opponent_hit(self, dx, dy, rotation_angle):
        """Hiển thị vị trí ném của đối thủ"""
        # Tính toán vị trí hit_point dựa trên thông tin từ đối thủ
        theta = math.radians(-rotation_angle)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        x_local = dx * cos_t - dy * sin_t
        y_local = dx * sin_t + dy * cos_t

        self.hit_point = QPointF(x_local, y_local)
        self.update()
        # Tự động ẩn chấm đỏ sau 3 giây (lâu hơn để người xem thấy rõ)
        QTimer.singleShot(3000, self.clear_hit_point)

    def show_opponent_cursor(self, dx, dy):
        """Hiển thị cursor/pointer của đối thủ realtime"""
        self.opponent_cursor = QPointF(dx, dy)
        self.update()
        # Tự động ẩn cursor sau 2 giây
        QTimer.singleShot(2000, self.hide_opponent_cursor)

    def hide_opponent_cursor(self):
        """Ẩn cursor của đối thủ"""
        if hasattr(self, "cursor_hide_scheduled"):
            self.cursor_hide_scheduled = False
        self.opponent_cursor = None
        self.update()

    def rotate(self, angle):
        """Quay bảng ngay lập tức với góc cố định"""
        self.rotation_angle = (self._rotation_angle + angle) % 360

    def spin_wheel(self, min_rotations=3, max_rotations=7):
        """Quay bánh xe với hiệu ứng mượt mà như bánh xe may mắn"""
        if self.is_spinning:
            return

        self.is_spinning = True

        # Tạo số vòng quay ngẫu nhiên
        full_rotations = random.randint(min_rotations, max_rotations)
        # Thêm góc ngẫu nhiên để dừng ở vị trí bất kỳ
        final_angle = random.randint(0, 359)

        # Tổng góc quay
        total_rotation = full_rotations * 360 + final_angle

        # Cấu hình animation
        self.rotation_animation.setStartValue(self._rotation_angle)
        self.rotation_animation.setEndValue(self._rotation_angle + total_rotation)

        # Thay đổi thời gian dựa trên số vòng quay
        duration = 2000 + (full_rotations - 3) * 500  # 2-4 giây tùy vào số vòng
        self.rotation_animation.setDuration(duration)

        # Ngắt kết nối cũ trước khi kết nối mới để tránh multiple connections
        try:
            self.rotation_animation.finished.disconnect()
        except TypeError:
            pass

        # Kết nối signal mới
        self.rotation_animation.finished.connect(self._on_spin_finished)

        # Bắt đầu quay
        self.rotation_animation.start()

    def _on_spin_finished(self):
        """Được gọi khi animation quay kết thúc"""
        self.is_spinning = False
        # Ngắt kết nối signal an toàn
        try:
            self.rotation_animation.finished.disconnect(self._on_spin_finished)
        except TypeError:
            # Signal có thể đã được ngắt kết nối rồi
            pass

    def spin_wheel_with_params(
        self, min_rotations, max_rotations, final_angle, duration
    ):
        """Quay bánh xe với tham số cụ thể để đồng bộ hóa giữa các client"""
        if self.is_spinning:
            return

        self.is_spinning = True

        # Sử dụng tham số được truyền vào thay vì random
        full_rotations = min_rotations

        # Tổng góc quay
        total_rotation = full_rotations * 360 + final_angle

        # Cấu hình animation
        self.rotation_animation.setStartValue(self._rotation_angle)
        self.rotation_animation.setEndValue(self._rotation_angle + total_rotation)

        # Sử dụng duration được truyền vào
        self.rotation_animation.setDuration(duration)

        # Ngắt kết nối cũ trước khi kết nối mới để tránh multiple connections
        try:
            self.rotation_animation.finished.disconnect()
        except TypeError:
            pass

        # Kết nối signal mới
        self.rotation_animation.finished.connect(self._on_spin_finished)

        # Bắt đầu quay
        self.rotation_animation.start()

    def quick_spin(self):
        """Quay nhanh với 1-2 vòng"""
        self.spin_wheel(min_rotations=1, max_rotations=2)

    def cleanup(self):
        """Dọn dẹp animation và signal khi widget bị hủy"""
        if self.rotation_animation:
            self.rotation_animation.stop()
            try:
                self.rotation_animation.finished.disconnect()
            except TypeError:
                pass
            self.is_spinning = False

        # Dọn dẹp cursor state
        if hasattr(self, "cursor_hide_scheduled"):
            self.cursor_hide_scheduled = False
        self.opponent_cursor = None

    def set_rotation_speed(self, speed):
        """Thiết lập tốc độ quay mới (độ/khung hình)"""
        self.rotation_speed = max(0.1, min(5.0, speed))  # Giới hạn 0.1-5.0 độ/khung

    def pause_rotation(self):
        """Tạm dừng quay liên tục"""
        self.continuous_rotation_timer.stop()

    def resume_rotation(self):
        """Tiếp tục quay liên tục"""
        if not self.continuous_rotation_timer.isActive():
            self.continuous_rotation_timer.start(50)

    def closeEvent(self, event):
        """Override closeEvent để dọn dẹp"""
        self.cleanup()
        super().closeEvent(event)


# --- Lớp giao diện chính của trò chơi ---


class DartBoardView(QWidget):
    # Tín hiệu để thông báo cho cửa sổ cha (ChallengeView) biết khi trò chơi kết thúc
    game_ended_signal = pyqtSignal()

    # Signals để xử lý UI updates từ main thread (tránh threading issues)
    show_game_over_signal = pyqtSignal(str)  # winner name
    show_opponent_quit_signal = pyqtSignal(str)  # opponent name

    check_game_end_signal = pyqtSignal()  # trigger game end check

    # Signal cho xoay dartboard
    opponent_spin_signal = pyqtSignal(float, int)  # rotation_amount, duration

    # Signal cho xử lý opponent threw từ main thread
    opponent_threw_signal = pyqtSignal(dict)  # body

    def __init__(self, client, username, opponent, is_first, match_id):
        super().__init__()
        self.tcp_client = client
        self.username = username
        self.opponent = opponent
        self.is_my_turn = is_first
        self.match_id = match_id
        self.setWindowTitle(f"Trận đấu: {self.username} vs {self.opponent}")
        self.resize(900, 600)

        # Trạng thái trò chơi
        self.scores = {self.username: 0, self.opponent: 0}
        self.throw_history = []
        self.throws_count = {self.username: 0, self.opponent: 0}  # Đếm số lần ném
        self.game_ended = False  # Flag để kiểm tra game đã kết thúc chưa

        # Timer cho lượt chơi (thread-safe)
        self.time_left = 30
        self.timer_active = False
        # Flag set when the current turn has expired (time ran out)
        self.turn_expired = False

        self.setup_ui()
        self.connect_signals()

        # Connect spin signal to safe handler
        self.opponent_spin_signal.connect(self._trigger_spin_safe)

        # Connect opponent threw signal to safe handler
        self.opponent_threw_signal.connect(self._handle_other_threw_safe)

        # Setup client helpers
        self.client_helper = ClientHelper(self.tcp_client)
        self.event_helper = ClientEventHelper(self.tcp_client)

        # Setup event handlers
        print("🔌 Đăng ký event handlers...")
        self.event_helper.on_other_threw(self._handle_other_threw)
        self.event_helper.on_player_forfeited(self._handle_player_forfeited)
        spin_id = self.event_helper.on_opponent_spin(self._handle_opponent_spin)
        print(f"✅ Đã đăng ký on_opponent_spin với ID: {spin_id}")

        # Bắt đầu lượt đầu tiên
        self.update_turn_status()

    def setup_ui(self):
        main_layout = QHBoxLayout()

        # Bảng phi tiêu bên trái
        self.dart_board = DartBoardWidget()
        main_layout.addWidget(self.dart_board, 3)

        # Bảng thông tin bên phải
        right_panel_layout = QVBoxLayout()

        # Khởi tạo biến cho cơ chế xoay (sẽ thêm widget sau)
        self.spin_power = 0
        self.max_power = 100
        self.is_charging = False
        self.charge_timer = QTimer()
        self.charge_timer.timeout.connect(self._update_charge)
        self.charge_rate = 2  # Tăng 2% mỗi 50ms

        # Tiêu đề
        title = QLabel("BẢNG ĐIỂM")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        right_panel_layout.addWidget(title)

        # Điểm số người chơi
        self.player1_label = QLabel(f"{self.username}: 0 (0/5)")
        self.player1_label.setStyleSheet(
            "font-size: 16px; padding: 5px; background-color: #e0f0ff;"
        )
        right_panel_layout.addWidget(self.player1_label)

        self.player2_label = QLabel(f"{self.opponent}: 0 (0/5)")
        self.player2_label.setStyleSheet(
            "font-size: 16px; padding: 5px; background-color: #fff0e0;"
        )
        right_panel_layout.addWidget(self.player2_label)

        # Hiển thị tổng điểm tích lũy
        self.total_score_label = QLabel("📊 Tổng điểm: Bạn 0 - Đối thủ 0")
        self.total_score_label.setAlignment(Qt.AlignCenter)
        self.total_score_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 8px; "
            "background-color: #f0f8ff; border: 2px solid #4682b4; border-radius: 5px;"
        )
        right_panel_layout.addWidget(self.total_score_label)

        # Hiển thị lượt chơi
        self.turn_label = QLabel("🎯 Lượt bạn")
        self.turn_label.setAlignment(Qt.AlignCenter)
        self.turn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: blue; padding: 10px;"
        )
        right_panel_layout.addWidget(self.turn_label)

        # Timer
        self.timer_label = QLabel("Thời gian còn lại: 30s")
        self.timer_label.setAlignment(Qt.AlignCenter)
        right_panel_layout.addWidget(self.timer_label)

        # Lịch sử ném
        right_panel_layout.addWidget(QLabel("Lịch sử ném:"))
        self.history_list = QListWidget()
        right_panel_layout.addWidget(self.history_list)

        # Các nút điều khiển
        # Thanh tích lũy lực xoay
        self.spin_power_bar = QProgressBar()
        self.spin_power_bar.setMaximum(100)
        self.spin_power_bar.setValue(0)
        self.spin_power_bar.setFormat("💪 Lực xoay: %p%")
        self.spin_power_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                background-color: #E3F2FD;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:0.5 #FFC107, stop:1 #F44336);
                border-radius: 3px;
            }
        """)

        # Nút xoay (giữ để tích lực)
        self.spin_btn = QPushButton("🌀 Giữ để Xoay Dartboard Đối Thủ")
        self.spin_btn.pressed.connect(self._start_charging_spin)
        self.spin_btn.released.connect(self._release_spin)
        self.spin_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        self.quit_btn = QPushButton("❌ Đầu hàng")
        self.quit_btn.clicked.connect(self.quit_game)
        self.quit_btn.setStyleSheet("""
      QPushButton {
        background-color: #f44336;
        color: white;
        border: none;
        padding: 8px;
        border-radius: 5px;
        font-weight: bold;
      }
      QPushButton:hover {
        background-color: #d32f2f;
      }
    """)

        right_panel_layout.addWidget(self.spin_power_bar)
        right_panel_layout.addWidget(self.spin_btn)
        right_panel_layout.addStretch()
        right_panel_layout.addWidget(self.quit_btn)

        main_layout.addLayout(right_panel_layout, 1)
        self.setLayout(main_layout)

    def connect_signals(self):
        self.dart_board.throw_detail_signal.connect(self.send_throw_detail_to_server)

        # Connect UI signals để tránh threading issues
        self.show_game_over_signal.connect(self._show_game_over_dialog)
        self.show_opponent_quit_signal.connect(self._show_opponent_quit_dialog)
        self.check_game_end_signal.connect(self._check_game_end_safe)

    def update_turn_status(self):
        if self.is_my_turn:
            self.turn_label.setText(f"Lượt của bạn")
            self.turn_expired = False
            self.spin_btn.setEnabled(False)  # Tắt nút xoay khi đến lượt mình
            self.dart_board.is_enabled = True  # Bật click vào dartboard
            # Thêm delay 5 giây trước khi cho phép ném
            self.dart_board.throw_delay_active = True
            self.turn_label.setText("⏳ Chờ 5s...")

            # Ẩn timer trong 5 giây đầu
            self.timer_label.hide()

            # Countdown từ 5 đến 1
            self.throw_delay_countdown = 5
            self._update_throw_delay_countdown()
        else:
            self.turn_label.setText(f"⏸️ Lượt đối thủ")
            self.spin_btn.setEnabled(True)  # Bật nút xoay khi đến lượt đối thủ
            self.dart_board.is_enabled = False  # Tắt click vào dartboard
            self.dart_board.throw_delay_active = False  # Reset delay flag
            self.stop_turn_timer()
            self.timer_label.setText("Đợi...")

    def _update_throw_delay_countdown(self):
        """Cập nhật countdown cho throw delay"""
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"⏱️ Game ended, stopping throw delay countdown")
            return

        if self.throw_delay_countdown > 0:
            self.turn_label.setText(f"⏳ Chờ {self.throw_delay_countdown}s...")
            self.throw_delay_countdown -= 1
            QTimer.singleShot(1000, self._update_throw_delay_countdown)
        else:
            self.dart_board.throw_delay_active = False
            self.turn_label.setText("🎯 Lượt bạn - Click để ném!")
            # Hiện timer và bắt đầu đếm ngược
            self.timer_label.show()
            self.start_turn_timer()

    def start_turn_timer(self):
        self.time_left = 30
        self.timer_active = True
        self.timer_label.setText(f"Thời gian còn lại: {self.time_left}s")
        print(
            f"⏰ start_turn_timer: time_left={self.time_left}, timer_active={self.timer_active}"
        )
        self._schedule_timer_tick()

    def stop_turn_timer(self):
        print(f"⏹️ stop_turn_timer called")
        self.timer_active = False

    def _schedule_timer_tick(self):
        """Schedule next timer tick using QTimer.singleShot for thread safety"""
        # Check if game has ended before scheduling
        if hasattr(self, "game_ended") and self.game_ended:
            return

        if self.timer_active and hasattr(self, "timer_active"):
            QTimer.singleShot(1000, self.on_time_out)

    def on_time_out(self):
        print(
            f"⏱️ on_time_out: timer_active={self.timer_active}, time_left={self.time_left}"
        )
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"⏱️ Game ended, stopping timer")
            return

        if not self.timer_active or not hasattr(self, "timer_active"):
            print(f"⏱️ Timer not active, returning")
            return

        self.time_left -= 1
        self.timer_label.setText(f"Thời gian còn lại: {self.time_left}s")

        if self.time_left <= 0:
            self.stop_turn_timer()
            # Mark the turn expired and send exactly one 0-point throw to server
            self.turn_expired = True
            try:
                # Send detailed 0-point throw (dx/dy unknown) so server can show hit marker as needed
                self.send_throw_detail_to_server(
                    0, 0.0, 0.0, getattr(self.dart_board, "_rotation_angle", 0.0)
                )
            except Exception as e:
                print(f"Lỗi khi gửi điểm timeout: {e}")
            self.add_to_history(f"Hết giờ! {self.username} được (0 điểm)")
        else:
            # Continue timer
            self._schedule_timer_tick()

    def send_throw_detail_to_server(self, score, dx, dy, rotation_angle):
        """Gửi thông tin chi tiết về cú ném bao gồm vị trí click"""
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"Game ended, not sending throw")
            return

        if not self.is_my_turn:
            return

        self.stop_turn_timer()

        try:
            sync_await(
                self.client_helper.throw_dart(
                    match_id=self.match_id,
                    score=score,
                    dx=dx,
                    dy=dy,
                    rotation_angle=rotation_angle,
                )
            )

            self.update_scores(self.username, score)
            self.add_to_history(f"{self.username} ném được {score} điểm")

            self.is_my_turn = False
            self.update_turn_status()

        except Exception as e:
            print(f"Lỗi khi gửi điểm: {e}")
            self.start_turn_timer()

    def _handle_other_threw(self, body: dict):
        """Xử lý khi đối thủ ném phi tiêu (từ event thread)"""
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"Game ended, ignoring opponent throw")
            return

        print(f"📥 _handle_other_threw: Emitting signal to main thread")
        # Emit signal để xử lý trong main thread
        self.opponent_threw_signal.emit(body)

    def _handle_other_threw_safe(self, body: dict):
        """Xử lý khi đối thủ ném phi tiêu (từ main thread)"""
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"Game ended, not processing opponent throw")
            return

        score = body["score"]
        dx = body.get("dx")
        dy = body.get("dy")
        rotation_angle = body.get("rotationAngle", 0)

        self.update_scores(self.opponent, score)
        self.add_to_history(f"{self.opponent} ném được {score} điểm")

        # Hiển thị vị trí ném của đối thủ nếu có tọa độ
        # Sử dụng rotation_angle từ đối thủ để hiển thị chính xác
        if dx is not None and dy is not None:
            print(
                f"📍 Opponent hit at dx={dx:.1f}, dy={dy:.1f}, rotation={rotation_angle:.1f}°"
            )
            self.dart_board.show_opponent_hit(dx, dy, rotation_angle)

        print(f"🎯 _handle_other_threw_safe: Switching to my turn")
        self.is_my_turn = True
        self.update_turn_status()

    def _start_charging_spin(self):
        """Bắt đầu tích lũy lực xoay"""
        print("⚡ Bắt đầu tích lực xoay...")
        self.is_charging = True
        self.spin_power = 0
        self.spin_power_bar.setValue(0)
        self.charge_timer.start(50)  # Update mỗi 50ms

    def _update_charge(self):
        """Cập nhật thanh lực xoay"""
        if self.is_charging and self.spin_power < self.max_power:
            self.spin_power = min(self.max_power, self.spin_power + self.charge_rate)
            self.spin_power_bar.setValue(int(self.spin_power))

    def _release_spin(self):
        """Thả nút - gửi lệnh xoay đến đối thủ"""
        print(f"🛑 Thả nút với lực {self.spin_power:.0f}%")
        self.is_charging = False
        self.charge_timer.stop()

        if self.spin_power < 5:
            print("❌ Lực quá yếu, không gửi lệnh xoay")
            self.spin_power_bar.setValue(0)
            return

        # Tính toán rotation dựa trên lực (5-100%)
        min_rotation = 360
        max_rotation = 3600
        rotation_amount = min_rotation + (max_rotation - min_rotation) * (
            self.spin_power / 100
        )

        # Thời gian xoay: lực càng mạnh càng lâu (2-6 giây)
        min_duration = 2000
        max_duration = 6000
        duration = min_duration + (max_duration - min_duration) * (
            self.spin_power / 100
        )

        print(
            f"🌀 Gửi lệnh xoay với lực {self.spin_power:.0f}%: {rotation_amount:.0f}° trong {duration:.0f}ms"
        )

        # Xoay dartboard của chính mình
        self.dart_board.trigger_spin(
            rotation_amount=rotation_amount, duration=int(duration)
        )

        # Gửi lệnh xoay đến server (để đối thủ cũng xoay)
        try:
            # Check if game has ended before sending spin
            if hasattr(self, "game_ended") and self.game_ended:
                print(f"Game ended, not sending spin")
                return

            sync_await(
                self.client_helper.spin_dartboard(
                    match_id=self.match_id,
                    rotation_amount=rotation_amount,
                    duration=duration,
                )
            )
        except Exception as e:
            print(f"Lỗi khi gửi lệnh xoay: {e}")

        # Reset thanh lực sau 1 giây
        QTimer.singleShot(1000, lambda: self.spin_power_bar.setValue(0))

    def _handle_opponent_spin(self, body: dict):
        """Xử lý khi đối thủ gửi lệnh xoay (từ event thread)"""
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"Game ended, ignoring opponent spin")
            return

        print(f"📥 _handle_opponent_spin được gọi với body: {body}")
        rotation_amount = body.get("rotationAmount", 720)
        duration = body.get("duration", 3000)
        print(
            f"🌀 Nhận lệnh xoay từ đối thủ: {rotation_amount:.0f}° trong {duration:.0f}ms"
        )
        # Emit signal để xử lý trong main thread
        self.opponent_spin_signal.emit(float(rotation_amount), int(duration))

    def _trigger_spin_safe(self, rotation_amount: float, duration: int):
        """Trigger spin từ main thread (được gọi bởi signal)"""
        # Check if game has ended
        if hasattr(self, "game_ended") and self.game_ended:
            print(f"Game ended, not triggering spin")
            return

        print(f"🎯 _trigger_spin_safe: Gọi trigger_spin trên dartboard...")
        self.dart_board.trigger_spin(rotation_amount=rotation_amount, duration=duration)
        print(f"✅ trigger_spin đã được gọi")

    def _handle_player_forfeited(self, body: dict):
        """Xử lý khi có người đầu hàng"""
        username = body["username"]
        if username == self.opponent:
            self.show_opponent_quit_signal.emit(self.opponent)
        else:
            self.end_game()

    def add_to_history(self, text):
        self.throw_history.append(text)
        self.history_list.addItem(text)
        self.history_list.scrollToBottom()

    def update_scores(self, player, new_score):
        # Lưu điểm lượt này và tăng tổng điểm tích lũy
        if player not in self.scores:
            self.scores[player] = 0
        self.scores[player] += new_score  # Tích lũy điểm

        # Tăng số lần ném của người chơi
        self.throws_count[player] += 1

        # Cập nhật hiển thị điểm lượt này và số lượt
        if player == self.username:
            self.player1_label.setText(
                f"{self.username}: +{new_score} = {self.scores[player]} ({self.throws_count[player]}/{MAX_THROWS_PER_PLAYER})"
            )
        else:
            self.player2_label.setText(
                f"{self.opponent}: +{new_score} = {self.scores[player]} ({self.throws_count[player]}/{MAX_THROWS_PER_PLAYER})"
            )

        # Cập nhật tổng điểm
        my_total = self.scores.get(self.username, 0)
        opponent_total = self.scores.get(self.opponent, 0)
        self.total_score_label.setText(
            f"📊 Tổng điểm: Bạn {my_total} - Đối thủ {opponent_total}"
        )

        # Kiểm tra xem cả hai người đã ném đủ lượt chưa (emit signal để tránh threading issue)
        if (
            self.throws_count[self.username] >= MAX_THROWS_PER_PLAYER
            and self.throws_count[self.opponent] >= MAX_THROWS_PER_PLAYER
        ):
            self.check_game_end_signal.emit()

    def check_game_end(self):
        """Kiểm tra và xử lý kết thúc trận đấu sau đủ số lượt ném"""
        player1_score = self.scores[self.username]
        player2_score = self.scores[self.opponent]

        if player1_score > player2_score:
            winner = self.username
        elif player2_score > player1_score:
            winner = self.opponent
        else:
            winner = None  # Hòa

        self._show_game_over_dialog(winner if winner else "")

    def _show_game_over_dialog(self, winner: str):
        """Hiển thị dialog kết thúc game"""
        if winner == "":
            message = "Trận đấu hòa!"
        elif winner == self.username:
            message = "🎉 Chúc mừng! Bạn đã thắng!"
        else:
            message = f"Đối thủ {winner} đã thắng!"

        QMessageBox.information(self, "Kết thúc trận đấu", message)
        self.end_game()

    def _show_opponent_quit_dialog(self, opponent_name: str):
        """Hiển thị dialog khi đối thủ đầu hàng"""
        QMessageBox.information(
            self, "Đối thủ đầu hàng", f"{opponent_name} đã đầu hàng. Bạn thắng!"
        )
        self.end_game()

    def _check_game_end_safe(self):
        """Thread-safe version of check_game_end"""
        self.check_game_end()

    def quit_game(self):
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc muốn đầu hàng?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                sync_await(self.client_helper.forfeit_match(self.match_id))
                self.end_game()
            except Exception as e:
                print(f"Lỗi khi đầu hàng: {e}")
                QMessageBox.warning(self, "Lỗi", f"Không thể đầu hàng: {e}")

    def end_game(self):
        # Đánh dấu game đã kết thúc
        self.game_ended = True

        # Dọn dẹp dart board trước khi đóng
        if hasattr(self, "dart_board"):
            self.dart_board.cleanup()

        # Dọn dẹp timer
        if hasattr(self, "timer_active"):
            self.timer_active = False

        self.game_ended_signal.emit()
        self.close()

    def closeEvent(self, event):
        """Override closeEvent để dọn dẹp khi đóng cửa sổ"""
        # Đánh dấu game đã kết thúc
        self.game_ended = True

        if hasattr(self, "dart_board"):
            self.dart_board.cleanup()

        if hasattr(self, "timer_active"):
            self.timer_active = False

        super().closeEvent(event)
