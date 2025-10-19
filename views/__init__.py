from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from utils.tcp_client import TCPClient


class MainView(QWidget):
    def __init__(self, client: TCPClient):
        super().__init__()
        self._add_components()
        self.setWindowTitle("Dart Duel")

        self.tcp_client = client

        self.login_view = None
        self.register_view = None

    def open_login_view(self):
        from .login_view import LoginView

        if self.login_view is None:
            self.login_view = LoginView(self.tcp_client)
            self.login_view.go_to_register.connect(self.open_register_from_login)

        self.hide()
        self.login_view.show()

    def open_register_view(self):
        from .register_view import RegisterView

        if self.register_view is None:
            self.register_view = RegisterView(self.tcp_client)
            self.register_view.go_to_login.connect(self.open_login_from_register)

        self.hide()
        self.register_view.show()

    def open_login_from_register(self):
        self.register_view.close()
        self.open_login_view()

    def open_register_from_login(self):
        self.login_view.close()
        self.open_register_view()

    def _add_components(self):
        self.button_register_view = QPushButton("Đăng ký")
        self.button_register_view.setStyleSheet(
            "background-color: #4CAF50; color: white;"
        )
        self.button_register_view.setFixedWidth(100)
        self.button_register_view.setFixedHeight(40)
        self.button_register_view.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor),
        )
        self.button_register_view.clicked.connect(self.open_register_view)

        self.button_login_view = QPushButton("Đăng nhập")
        self.button_login_view.setStyleSheet("background-color: #2196F3; color: white;")
        self.button_login_view.setFixedWidth(100)
        self.button_login_view.setFixedHeight(40)
        self.button_login_view.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor),
        )

        self.button_login_view.clicked.connect(self.open_login_view)

        layout = QVBoxLayout()
        layout.addStretch(5)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.button_register_view)
        button_row.addSpacing(20)
        button_row.addWidget(self.button_login_view)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        layout.addStretch(1)
        self.setLayout(layout)
