"""
ui/touch_numpad_dialog.py - Teclado Numérico Táctil para Pesaje y Cantidades
Proporciona una interfaz táctil ergonómica con botones de acceso rápido (+100g, +250g, +500g, +1Kg),
cálculo de subtotal en tiempo real y lectura de balanza integrada.
"""

from decimal import Decimal, ROUND_HALF_UP
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent

from database import format_stock_qty


class TouchQuantityDialog(QDialog):
    """Diálogo táctil para ingreso de peso o cantidad de producto."""

    def __init__(
        self,
        product_name: str,
        unit_price: Decimal,
        uom: str = "Kg",
        initial_qty: Decimal = Decimal('1.000'),
        live_scale_weight: Decimal = Decimal('0.000'),
        parent=None
    ):
        super().__init__(parent)
        self.product_name = product_name
        self.unit_price = Decimal(str(unit_price))
        self.uom = uom
        self.live_scale_weight = Decimal(str(live_scale_weight))
        self.is_kg = (uom.lower() == "kg" or uom.lower() == "kilo")

        self.input_text = ""
        self.final_qty = initial_qty.quantize(Decimal('0.001') if self.is_kg else Decimal('1'))

        self.setWindowTitle("Ingreso de Cantidad / Peso")
        self.setFixedSize(520, 620)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._init_ui()
        self._set_qty(self.final_qty)

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121622;
                border: 2px solid #2a3550;
                border-radius: 12px;
            }
            QLabel {
                color: #e0e6ed;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton {
                font-family: 'Segoe UI', Arial;
                font-weight: bold;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # --- Encabezado del Producto ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #1a2234; border-radius: 8px; padding: 6px;")
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(12, 8, 12, 8)
        h_layout.setSpacing(4)

        lbl_prod = QLabel(self.product_name)
        lbl_prod.setStyleSheet("font-size: 18px; font-weight: bold; color: #7aa2f7;")
        lbl_prod.setWordWrap(True)

        lbl_price = QLabel(f"Precio Unitario: ₲ {self.unit_price:,.0f} / {self.uom}".replace(",", "."))
        lbl_price.setStyleSheet("font-size: 13px; color: #a9b1d6;")

        h_layout.addWidget(lbl_prod)
        h_layout.addWidget(lbl_price)
        layout.addWidget(header_frame)

        # --- Display de Cantidad / Peso y Subtotal ---
        display_frame = QFrame()
        display_frame.setStyleSheet("background-color: #0d111a; border: 2px solid #7aa2f7; border-radius: 8px;")
        d_layout = QVBoxLayout(display_frame)
        d_layout.setContentsMargins(15, 10, 15, 10)
        d_layout.setSpacing(2)

        self.lbl_qty_display = QLabel("0.000")
        self.lbl_qty_display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_qty_display.setStyleSheet("font-size: 38px; font-weight: bold; color: #9ece6a; font-family: 'Consolas', monospace;")

        self.lbl_subtotal_display = QLabel("Subtotal: ₲ 0")
        self.lbl_subtotal_display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_subtotal_display.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffd166;")

        d_layout.addWidget(self.lbl_qty_display)
        d_layout.addWidget(self.lbl_subtotal_display)
        layout.addWidget(display_frame)

        # --- Botones de Presets / Incrementos Rápidos ---
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)

        presets = (
            [("+100g", Decimal('0.100')), ("+250g", Decimal('0.250')), ("+500g", Decimal('0.500')), ("+1 Kg", Decimal('1.000')), ("+2 Kg", Decimal('2.000'))]
            if self.is_kg else
            [("+1", Decimal('1')), ("+2", Decimal('2')), ("+5", Decimal('5')), ("+10", Decimal('10')), ("+12", Decimal('12'))]
        )

        for text, val in presets:
            btn_pre = QPushButton(text)
            btn_pre.setFixedHeight(44)
            btn_pre.setStyleSheet("""
                QPushButton {
                    background-color: #232c40;
                    color: #7aa2f7;
                    font-size: 14px;
                    border: 1px solid #3d4a6b;
                }
                QPushButton:hover {
                    background-color: #313d58;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #1a2234;
                }
            """)
            btn_pre.clicked.connect(lambda checked, v=val: self._add_preset(v))
            presets_layout.addWidget(btn_pre)

        layout.addLayout(presets_layout)

        # --- Botón de Balanza en Vivo (si aplica) ---
        if self.is_kg:
            btn_scale = QPushButton(f"⚖️ Capturar Balanza ({self.live_scale_weight} Kg)")
            btn_scale.setFixedHeight(40)
            btn_scale.setStyleSheet("""
                QPushButton {
                    background-color: #1f3b2d;
                    color: #06d6a0;
                    font-size: 14px;
                    border: 1px solid #2e6b4f;
                }
                QPushButton:hover {
                    background-color: #2a523e;
                }
            """)
            btn_scale.clicked.connect(self._capture_live_scale)
            layout.addWidget(btn_scale)

        # --- Grilla Numpad Táctil ---
        numpad_layout = QGridLayout()
        numpad_layout.setSpacing(8)

        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2), ('C', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('⌫', 1, 3),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2), ('00', 2, 3),
            ('0', 3, 0), ('.', 3, 1), ('000', 3, 2), ('✓ OK', 3, 3),
        ]

        for text, r, c in buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(50)

            if text == '✓ OK':
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1a4d2e;
                        color: #ffffff;
                        font-size: 16px;
                        border: 1px solid #2d8a52;
                    }
                    QPushButton:hover { background-color: #23683e; }
                    QPushButton:pressed { background-color: #123820; }
                """)
                btn.clicked.connect(self.accept)
            elif text == 'C':
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4a1f1f;
                        color: #ff6b6b;
                        font-size: 16px;
                        border: 1px solid #752d2d;
                    }
                    QPushButton:hover { background-color: #632929; }
                """)
                btn.clicked.connect(self._clear_input)
            elif text == '⌫':
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3b2c1f;
                        color: #ffd166;
                        font-size: 16px;
                        border: 1px solid #6b4d32;
                    }
                    QPushButton:hover { background-color: #523c2a; }
                """)
                btn.clicked.connect(self._backspace_input)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1c2333;
                        color: #e0e6ed;
                        font-size: 18px;
                        border: 1px solid #2a3550;
                    }
                    QPushButton:hover { background-color: #2a3550; color: #ffffff; }
                    QPushButton:pressed { background-color: #131929; }
                """)
                btn.clicked.connect(lambda checked, t=text: self._append_digit(t))

            numpad_layout.addWidget(btn, r, c)

        layout.addLayout(numpad_layout)

        # --- Botones Inferiores Cancelar / Aceptar ---
        bot_layout = QHBoxLayout()
        btn_cancel = QPushButton("✖ Cancelar [Esc]")
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #2b303c;
                color: #a9b1d6;
                font-size: 14px;
                border: 1px solid #3d4455;
            }
            QPushButton:hover { background-color: #384050; color: #ffffff; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_confirm = QPushButton("✅ Aceptar e Insertar [Enter]")
        btn_confirm.setFixedHeight(45)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #06d6a0;
                color: #0b1e17;
                font-size: 16px;
                font-weight: 800;
                border: none;
            }
            QPushButton:hover { background-color: #05b888; }
            QPushButton:pressed { background-color: #04966f; }
        """)
        btn_confirm.clicked.connect(self.accept)

        bot_layout.addWidget(btn_cancel, stretch=1)
        bot_layout.addWidget(btn_confirm, stretch=2)
        layout.addLayout(bot_layout)

    def _set_qty(self, qty: Decimal):
        self.final_qty = max(Decimal('0.001'), qty)
        self.input_text = str(self.final_qty)
        self._update_display()

    def _append_digit(self, digit: str):
        if digit == '.' and '.' in self.input_text:
            return
        self.input_text += digit
        try:
            val = Decimal(self.input_text)
            self.final_qty = max(Decimal('0.001'), val)
        except Exception:
            pass
        self._update_display()

    def _clear_input(self):
        self.input_text = ""
        self.final_qty = Decimal('0.000') if self.is_kg else Decimal('0')
        self._update_display()

    def _backspace_input(self):
        self.input_text = self.input_text[:-1]
        if not self.input_text:
            self.final_qty = Decimal('0.000') if self.is_kg else Decimal('0')
        else:
            try:
                self.final_qty = Decimal(self.input_text)
            except Exception:
                pass
        self._update_display()

    def _add_preset(self, val: Decimal):
        if self.final_qty <= Decimal('0'):
            self.final_qty = val
        else:
            self.final_qty += val
        self.input_text = str(self.final_qty)
        self._update_display()

    def _capture_live_scale(self):
        if self.live_scale_weight > Decimal('0'):
            self._set_qty(self.live_scale_weight)

    def _update_display(self):
        unit_label = "Kg" if self.is_kg else "Un"
        if self.is_kg:
            display_str = f"{self.final_qty:,.3f} {unit_label}".replace(",", ".")
        else:
            display_str = f"{self.final_qty:,.0f} {unit_label}".replace(",", ".")

        self.lbl_qty_display.setText(display_str)

        subtotal = (self.final_qty * self.unit_price).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        self.lbl_subtotal_display.setText(f"Subtotal: ₲ {subtotal:,.0f}".replace(",", "."))

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        elif key == Qt.Key.Key_Backspace:
            self._backspace_input()
        elif key in range(Qt.Key.Key_0, Qt.Key.Key_9 + 1):
            self._append_digit(chr(event.key()))
        elif key == Qt.Key.Key_Period or key == Qt.Key.Key_Comma:
            self._append_digit('.')
        else:
            super().keyPressEvent(event)

    def get_quantity(self) -> Decimal:
        return max(Decimal('0.001'), self.final_qty)
