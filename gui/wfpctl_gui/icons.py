from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygon


def _asset_dirs() -> list[Path]:
    dirs: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(Path(meipass) / "wfpctl_gui" / "assets")
    dirs.append(Path(__file__).resolve().parent / "assets")
    return dirs


def _make_shield_icon() -> QIcon:
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setBrush(QColor(0, 120, 215))
    p.setPen(QPen(QColor(0, 80, 160), 2))

    pts = [
        (32, 4),
        (56, 14),
        (56, 32),
        (56, 44),
        (44, 56),
        (32, 60),
        (20, 56),
        (8, 44),
        (8, 32),
        (8, 14),
    ]
    polygon = QPolygon([QPoint(x, y) for x, y in pts])
    p.drawPolygon(polygon)

    p.setPen(QColor(255, 255, 255))
    p.setBrush(QColor(255, 255, 255))
    font = p.font()
    font.setPixelSize(28)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    p.end()

    return QIcon(pix)


def app_icon() -> QIcon:
    for d in _asset_dirs():
        ico = d / "wfpctl.ico"
        if ico.is_file():
            return QIcon(str(ico))
    return _make_shield_icon()