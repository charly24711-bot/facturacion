"""
ui/sync_status_widget.py - Widget de Estado de Sincronización Offline-First para PyQt6
Muestra el estado de conectividad con el servidor central, la cantidad de operaciones
pendientes en el outbox y permite forzar la sincronización manual bajo demanda.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QToolTip
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
import datetime

class SyncStatusWidget(QWidget):
    """
    Widget compacto para incrustar en la barra de estado o toolbar de la ventana principal.
    """
    manual_sync_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_status = 'OFFLINE'
        self.pending_count = 0
        self.last_sync_time = None
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Indicador de estado (LED / Badge)
        self.lbl_status = QLabel("🔴 Offline")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: #3b2020;
                color: #ff6b6b;
                border: 1px solid #702e2e;
            }
        """)

        # Contador de pendientes
        self.lbl_pending = QLabel("0 pendientes")
        self.lbl_pending.setStyleSheet("font-size: 11px; color: #a0a0a0;")

        # Botón de Sincronizar Ahora
        self.btn_sync = QPushButton("🔄 Sincronizar (F11)")
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                font-weight: bold;
                background-color: #2b303c;
                color: #e0e0e0;
                border: 1px solid #3d4455;
                border-radius: 4px;
                padding: 3px 10px;
            }
            QPushButton:hover {
                background-color: #384050;
                border-color: #4f586f;
            }
            QPushButton:pressed {
                background-color: #1f222b;
            }
            QPushButton:disabled {
                background-color: #1a1d24;
                color: #555555;
                border-color: #2a2e39;
            }
        """)
        self.btn_sync.clicked.connect(self._on_sync_clicked)

        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_pending)
        layout.addWidget(self.btn_sync)

        self._update_tooltip()

    def _on_sync_clicked(self):
        self.btn_sync.setEnabled(False)
        self.lbl_status.setText("🟡 Sincronizando...")
        self.lbl_status.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                background-color: #3b361e;
                color: #ffd166;
                border: 1px solid #756828;
            }
        """)
        self.manual_sync_requested.emit()
        # Reactivar botón tras 3 segundos por seguridad
        QTimer.singleShot(3000, lambda: self.btn_sync.setEnabled(True))

    def update_status(self, status: str, pending_count: int):
        """Actualiza el estado visual y el badge de transacciones pendientes."""
        self.current_status = status
        self.pending_count = pending_count

        if status == 'ONLINE':
            self.lbl_status.setText("🟢 En Línea")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    background-color: #1b382b;
                    color: #06d6a0;
                    border: 1px solid #23654b;
                }
            """)
        elif status == 'SYNCING':
            self.lbl_status.setText("🟡 Sincronizando...")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    background-color: #3b361e;
                    color: #ffd166;
                    border: 1px solid #756828;
                }
            """)
        elif status == 'ERROR':
            self.lbl_status.setText("⚠️ Error Sync")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    background-color: #4a2818;
                    color: #f77f00;
                    border: 1px solid #85441a;
                }
            """)
        else: # OFFLINE
            self.lbl_status.setText("🔴 Modo Offline")
            self.lbl_status.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    background-color: #3b2020;
                    color: #ff6b6b;
                    border: 1px solid #702e2e;
                }
            """)

        # Actualizar badge de pendientes
        if pending_count > 0:
            self.lbl_pending.setText(f"📦 {pending_count} pendientes")
            self.lbl_pending.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffd166;")
        else:
            self.lbl_pending.setText("✓ 0 pendientes")
            self.lbl_pending.setStyleSheet("font-size: 11px; color: #80c090;")

        self.btn_sync.setEnabled(True)
        self._update_tooltip()

    def on_sync_completed(self, pushed: int, pulled: int):
        """Registra el timestamp del último ciclo exitoso."""
        self.last_sync_time = datetime.datetime.now().strftime("%H:%M:%S")
        self._update_tooltip()

    def _update_tooltip(self):
        last_sync_str = self.last_sync_time or "Ninguna aún"
        self.setToolTip(
            f"Estado de Conexión: {self.current_status}\n"
            f"Transacciones en cola: {self.pending_count}\n"
            f"Última sincronización: {last_sync_str}\n"
            f"Presione F11 o haga clic para sincronizar ahora."
        )
