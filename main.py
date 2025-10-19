import asyncio
import sys

from PyQt5.QtWidgets import QApplication

from views import MainView
from qasync import QEventLoop

from utils.tcp_client import TCPClient


async def main(app: QApplication):
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    with TCPClient(("localhost", 5000)) as client:
        view = MainView(client)
        view.show()

        await app_close_event.wait()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    asyncio.run(main(app), loop_factory=QEventLoop)
