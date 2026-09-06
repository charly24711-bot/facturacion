"""
ui/lock_screen_dialog.py
========================
Pantalla de Bloqueo / Pausa de Terminal POS con PIN y Teclado Táctil:
  - Protege la caja durante descansos, refrigerio o relevos momentáneos.
  - Oculta totales y datos de clientes para seguridad física de la tienda.
  - Cronómetro en vivo de tiempo en pausa.
  - Desbloqueo mediante PIN/Contraseña del cajero o credencial de Supervisor/Admin.
  - Teclado numérico táctil integrado para pantallas POS All-in-One.
  - Preservación íntegra e intacta de la venta en curso.
"""

import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QFrame, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from database import SessionLocal
import models


class LockScreenDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user or {
            "id": 1,
            "username": "admin",
            "full_name": "Administrador General",
            "role": "ADMIN"
        }
        self.logout_requested = False
        self.pause_start_time = datetime.datetime.now()
        self.failed_attempts = 0

        self.setWindowTitle("🔒 Terminal POS Pausada")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self.resize(580, 680)

        # Fondo oscuro profundo de máxima seguridad
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                border: 2px solid #334155;
                border-radius: 12px;
            }
            QLabel {
                color: #f8fafc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(14)

        # ── Cabecera: Icono y Estado ───────────────────────────────────────
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel("🔒")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 48px; margin-bottom: 4px;")
        header_layout.addWidget(lbl_icon)

        lbl_status = QLabel("TERMINAL POS EN PAUSA")
        lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_status.setStyleSheet("font-size: 20px; font-weight: 900; letter-spacing: 1.5px; color: #38bdf8;")
        header_layout.addWidget(lbl_status)

        user_name = self.current_user.get("full_name", "Cajero")
        username = self.current_user.get("username", "cajero")
        user_role = self.current_user.get("role", "CAJERO")

        lbl_cajero = QLabel(f"Cajero Activo: {user_name} (@{username}) • Rol: {user_role}")
        lbl_cajero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_cajero.setStyleSheet("font-size: 13px; color: #94a3b8; margin-top: 2px;")
        header_layout.addWidget(lbl_cajero)

        # Cronómetro en vivo
        start_str = self.pause_start_time.strftime("%H:%M:%S")
        self.lbl_timer = QLabel(f"Pausado a las {start_str}  |  Tiempo: 00:00")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet("""
            background-color: #1e293b;
            color: #fbbf24;
            font-weight: bold;
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 6px;
            border: 1px solid #475569;
            margin-top: 6px;
        """)
        header_layout.addWidget(self.lbl_timer)

        main_layout.addLayout(header_layout)

        # Separador horizontal
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #334155; margin: 4px 0;")
        main_layout.addWidget(line)

        # ── Campo de PIN / Contraseña ──────────────────────────────────────
        pin_box = QVBoxLayout()
        lbl_prompt = QLabel("Ingrese su PIN o Contraseña para desbloquear:")
        lbl_prompt.setStyleSheet("font-size: 13px; color: #cbd5e1; font-weight: bold;")
        pin_box.addWidget(lbl_prompt)

        self.txt_pin = QLineEdit()
        self.txt_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pin.setPlaceholderText("••••••••")
        self.txt_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_pin.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 2px solid #38bdf8;
                border-radius: 8px;
                padding: 10px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 4px;
            }
            QLineEdit:focus {
                border: 2px solid #0284c7;
                background-color: #0f172a;
            }
        """)
        self.txt_pin.returnPressed.connect(self.intentar_desbloqueo)
        pin_box.addWidget(self.txt_pin)

        self.lbl_error = QLabel("")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setStyleSheet("color: #f87171; font-weight: bold; font-size: 12px; min-height: 18px;")
        pin_box.addWidget(self.lbl_error)

        main_layout.addLayout(pin_box)

        # ── Teclado Táctil Integrado (Numpad) ──────────────────────────────
        grid_numpad = QGridLayout()
        grid_numpad.setSpacing(8)

        btn_style_num = """
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                padding: 12px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #0284c7;
                color: white;
            }
        """

        btn_style_action = """
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
            QPushButton:pressed {
                background-color: #e2e8f0;
                color: #0f172a;
            }
        """

        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('C', 3, 0), ('0', 3, 1), ('⌫', 3, 2)
        ]

        for text, r, c in buttons:
            btn = QPushButton(text)
            if text in ('C', '⌫'):
                btn.setStyleSheet(btn_style_action)
                if text == 'C':
                    btn.clicked.connect(self.txt_pin.clear)
                else:
                    btn.clicked.connect(self.txt_pin.backspace)
            else:
                btn.setStyleSheet(btn_style_num)
                btn.clicked.connect(lambda _, ch=text: self.txt_pin.insert(ch))
            grid_numpad.addWidget(btn, r, c)

        main_layout.addLayout(grid_numpad)

        # ── Botones Principales de Desbloqueo y Salida ─────────────────────
        btn_unlock = QPushButton("🔓 DESBLOQUEAR CAJA")
        btn_unlock.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 12px;
                margin-top: 6px;
            }
            QPushButton:hover {
                background-color: #10b981;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        btn_unlock.clicked.connect(self.intentar_desbloqueo)
        main_layout.addWidget(btn_unlock)

        foot_bar = QHBoxLayout()
        btn_logout = QPushButton("🚪 Cerrar Turno / Salir")
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #dc2626;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7f1d1d;
                color: white;
            }
        """)
        btn_logout.clicked.connect(self.solicitar_cierre_sesion)
        foot_bar.addWidget(btn_logout)

        lbl_hint = QLabel("💡 F12 para pausar/reanudar")
        lbl_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        foot_bar.addWidget(lbl_hint)

        main_layout.addLayout(foot_bar)
        self.txt_pin.setFocus()

    def setup_timer(self):
        """Timer que actualiza el tiempo transcurrido cada segundo."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_cronometro)
        self.timer.start(1000)

    def actualizar_cronometro(self):
        delta = datetime.datetime.now() - self.pause_start_time
        segundos_totales = int(delta.total_seconds())
        minutos = segundos_totales // 60
        segundos = segundos_totales % 60
        start_str = self.pause_start_time.strftime("%H:%M:%S")
        self.lbl_timer.setText(f"Pausado a las {start_str}  |  Tiempo: {minutos:02d}:{segundos:02d}")

    def intentar_desbloqueo(self):
        pin = self.txt_pin.text().strip()
        if not pin:
            self.lbl_error.setText("⚠️ Ingrese su PIN o contraseña.")
            return

        db = SessionLocal()
        desbloqueado = False
        nombre_autorizo = ""

        try:
            # 1. Verificar si coincide con el usuario activo
            user_id = self.current_user.get("id")
            active_user = db.query(models.User).filter_by(id=user_id).first() if user_id else None
            
            if active_user and models.verify_password(pin, active_user.password_hash):
                desbloqueado = True
                nombre_autorizo = active_user.full_name
            else:
                # 2. Si no coincide, verificar si es un Administrador o Gerente (desbloqueo de emergencia)
                supervisores = db.query(models.User).filter(
                    models.User.role.in_(["ADMIN", "GERENTE"]),
                    models.User.is_active == True
                ).all()
                for sup in supervisores:
                    if models.verify_password(pin, sup.password_hash):
                        desbloqueado = True
                        nombre_autorizo = f"Supervisor: {sup.full_name}"
                        break
        except Exception as e:
            self.lbl_error.setText(f"Error en validación: {e}")
            return
        finally:
            db.close()

        if desbloqueado:
            self.timer.stop()
            self.accept()
        else:
            self.failed_attempts += 1
            self.lbl_error.setText(f"❌ Contraseña incorrecta (Intento {self.failed_attempts}).")
            self.txt_pin.clear()
            self.txt_pin.setFocus()

    def solicitar_cierre_sesion(self):
        res = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Desea cerrar el turno actual y salir del Punto de Venta?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.logout_requested = True
            self.timer.stop()
            self.reject()

    def keyPressEvent(self, event):
        # Impedir cerrar la ventana con Esc para que la pantalla de bloqueo no se evada
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
        elif event.key() == Qt.Key.Key_F12:
            self.intentar_desbloqueo()
        else:
            super().keyPressEvent(event)
