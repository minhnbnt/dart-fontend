from PyQt5.QtGui import QPixmap, QBrush
from PyQt5.QtCore import Qt
from pathlib import Path

ASSET_PATH = Path(__file__) / "../assets"


def _update_background(widget, pixmap: QPixmap):
    scaled = pixmap.scaled(
        widget.size(),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    palette = widget.palette()
    palette.setBrush(widget.backgroundRole(), QBrush(scaled))
    widget.setPalette(palette)
    widget.setAutoFillBackground(True)


def set_background(widget, image_name: str):
    abs_path = ASSET_PATH / image_name
    if not abs_path.exists():
        raise ValueError(f"Background image not found: {abs_path}")

    pixmap = QPixmap(abs_path)
    if pixmap.isNull():
        raise RuntimeError(f"Cannot load pixmap: {abs_path}")

    _update_background(widget, pixmap)
    widget.resizeEvent = lambda event: _update_background(widget, pixmap)
