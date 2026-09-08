"""
Genera banderas reales de USA, Brasil, Argentina y Paraguay
como archivos PNG en la carpeta assets/flags/
"""
import sys
import os
sys.path.insert(0, r"c:\ENTORNO LOCAL\Control\venv\Lib\site-packages")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPolygonF, QBrush, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF
import math

app = QApplication(sys.argv)

OUTPUT_DIR = r"c:\ENTORNO LOCAL\Control\assets\flags"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 60, 38  # Tamaño de cada bandera

def save(pixmap, name):
    path = os.path.join(OUTPUT_DIR, name)
    pixmap.save(path, "PNG")
    print(f"Guardada: {path}")

# ── BANDERA USA ──────────────────────────────────────────────────────────────
px = QPixmap(W, H)
p = QPainter(px)
stripe_h = H / 13
for i in range(13):
    color = "#B22234" if i % 2 == 0 else "#FFFFFF"
    p.fillRect(0, int(i * stripe_h), W, int(stripe_h) + 1, QColor(color))
# Canton azul
p.fillRect(0, 0, int(W * 0.4), int(H * 7/13), QColor("#3C3B6E"))
p.end()
save(px, "flag_us.png")

# ── BANDERA BRASIL ───────────────────────────────────────────────────────────
px = QPixmap(W, H)
p = QPainter(px)
p.fillRect(0, 0, W, H, QColor("#009C3B"))  # Verde
# Rombo amarillo
pts = [
    QPointF(W * 0.5, 2),
    QPointF(W - 3, H / 2),
    QPointF(W * 0.5, H - 2),
    QPointF(3, H / 2),
]
p.setBrush(QBrush(QColor("#FEDF00")))
p.setPen(Qt.PenStyle.NoPen)
p.drawPolygon(QPolygonF(pts))
# Círculo azul
cx, cy = W / 2, H / 2
r = H * 0.28
p.setBrush(QBrush(QColor("#002776")))
p.drawEllipse(QPointF(cx, cy), r, r)
# Franja blanca
p.setPen(QPen(QColor("#FFFFFF"), 1.5))
p.drawLine(int(cx - r), int(cy + r * 0.15), int(cx + r), int(cy - r * 0.15))
p.end()
save(px, "flag_br.png")

# ── BANDERA ARGENTINA ────────────────────────────────────────────────────────
px = QPixmap(W, H)
p = QPainter(px)
band = H // 3
p.fillRect(0, 0, W, band, QColor("#74ACDF"))           # Azul celeste
p.fillRect(0, band, W, band, QColor("#FFFFFF"))         # Blanco
p.fillRect(0, band * 2, W, H - band * 2, QColor("#74ACDF"))  # Azul celeste
# Sol de Mayo (simplificado como círculo amarillo)
cx, cy = W // 2, H // 2
r = int(band * 0.55)
p.setBrush(QBrush(QColor("#F6B40E")))
p.setPen(Qt.PenStyle.NoPen)
p.drawEllipse(QPointF(cx, cy), r, r)
p.end()
save(px, "flag_ar.png")

# ── BANDERA PARAGUAY ─────────────────────────────────────────────────────────
px = QPixmap(W, H)
p = QPainter(px)
band = H // 3
p.fillRect(0, 0, W, band, QColor("#D52B1E"))            # Rojo
p.fillRect(0, band, W, band, QColor("#FFFFFF"))          # Blanco
p.fillRect(0, band * 2, W, H - band * 2, QColor("#0038A8"))  # Azul
# Escudo simplificado (círculo)
cx, cy = W // 2, H // 2
r = int(band * 0.4)
p.setBrush(QBrush(QColor("#009B3A")))
p.setPen(Qt.PenStyle.NoPen)
p.drawEllipse(QPointF(cx, cy), r, r)
p.end()
save(px, "flag_py.png")

print("\n✅ Todas las banderas generadas en:", OUTPUT_DIR)
app.quit()
