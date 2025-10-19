from typing import override

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)
from qasync import asyncSlot

from utils.client_helper import ClientHelper
from utils.tcp_client import TCPClient
from views.match_making_view import MatchMakingView
from utils.sync_await import sync_await


class LoginView(QWidget):
    go_to_register = pyqtSignal()

    def __init__(self, client: TCPClient):
        super().__init__()
        self._add_component()

        self.setWindowTitle("Login Form")

        self.button_login.clicked.connect(self.handle_login)  # type: ignore
        self.button_register.clicked.connect(self.go_to_register.emit)  # type: ignore

        self._tcp_client = client
        self._client_helper = ClientHelper(self._tcp_client)

        self.match_making_view = None

    def handle_login(self):
        username = self.input_username.text()
        password = self.input_password.text()

        try:
            sync_await(self._client_helper.login(username, password))

            QMessageBox.information(self, "Success", "Login successful!")

            self.close()

            self.match_making_view = MatchMakingView(self._tcp_client)
            self.match_making_view.show()

        except ValueError as e:
            QMessageBox.warning(self, "Failed", str(e))
            return

    @override
    def resizeEvent(self, a0):
        self.center_container()
        super().resizeEvent(a0)

    def center_container(self):
        parent_width = self.width()
        parent_height = self.height()
        container_x = (parent_width - self.container_width) // 2
        container_y = (parent_height - self.container_height) // 2
        self.container.setGeometry(
            container_x, container_y, self.container_width, self.container_height
        )

    def _add_component(self):
        self.label_username = QLabel("Username:")
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Nhập username")
        self.input_username.setFixedHeight(40)

        self.label_password = QLabel("Password:")
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Nhập password")
        self.input_password.setFixedHeight(40)
        self.input_password.setEchoMode(QLineEdit.Password)

        self.button_login = QPushButton("Đăng nhập")
        self.button_login.setStyleSheet("background-color: #2196F3; color: white;")
        self.button_login.setFixedWidth(100)
        self.button_login.setFixedHeight(40)
        self.button_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.label_button_register = QLabel("Chưa có tài khoản?")
        self.button_register = QPushButton("Đăng ký ngay")
        self.button_register.setStyleSheet("background-color: #4CAF50; color: white;")
        self.button_register.setFixedWidth(100)
        self.button_register.setFixedHeight(40)
        self.button_register.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout()

        username_row = QHBoxLayout()
        username_row.addWidget(self.label_username)
        username_row.addWidget(self.input_username)
        layout.addLayout(username_row)

        password_row = QHBoxLayout()
        password_row.addWidget(self.label_password)
        password_row.addWidget(self.input_password)
        layout.addLayout(password_row)

        login_row = QHBoxLayout()
        login_row.addStretch(1)
        login_row.addWidget(self.button_login)
        login_row.addStretch(1)
        layout.addLayout(login_row)

        register_row = QHBoxLayout()
        register_row.addStretch(1)
        register_row.addWidget(self.label_button_register)
        register_row.addWidget(self.button_register)
        register_row.addStretch(1)
        layout.addLayout(register_row)

        self.container_width = 380
        self.container_height = 250
        self.container = QWidget(self)
        self.container.setObjectName("loginContainer")
        self.container.setStyleSheet("""
            #loginContainer {
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                border-radius: 8px;
            }
            #loginContainer QLabel, #loginContainer QPushButton {
                color: white;
                font-size: 14px;
            }
            #loginContainer QLineEdit {
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.container.setLayout(layout)
        self.center_container()
