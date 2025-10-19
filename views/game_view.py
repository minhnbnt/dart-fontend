from PyQt5.QtWidgets import QWidget
from utils.constants import WINDOW_WIDTH, WINDOW_HEIGHT, HOST, PORT


class GameView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fighting Game")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
