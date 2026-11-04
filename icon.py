"""Programmatic app icon (no binary assets needed)."""
import sys

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap, QPolygonF, QBrush


def make_pixmap(size=256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#7c83ff"))
    g.setColorAt(1, QColor("#4338ca"))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    p.setBrush(QColor("white"))
    s = size
    p.drawPolygon(QPolygonF([QPointF(s * 0.38, s * 0.28), QPointF(s * 0.38, s * 0.72),
                             QPointF(s * 0.74, s * 0.5)]))
    p.end()
    return pm


def make_icon() -> QIcon:
    return QIcon(make_pixmap())


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    out = sys.argv[1] if len(sys.argv) > 1 else "app.ico"
    print(make_pixmap(256).save(out))

