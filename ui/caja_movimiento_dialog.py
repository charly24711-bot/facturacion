import sys
import datetime
from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QGroupBox, QGridLayout, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database import SessionLocal
import models

class CajaMovimientoDialog(QDialog):
    """
    Diálogo para Registrar Fondo Fijo Inicial y Sangría / Retiro de Efectivo a Tesorería.
    Permite mantener la caja segura evitando acumulación riesgosa de dinero físico.
    """
    def __init__(self, session_id=None, current_user=None, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.current_user = current_user or {"id": 1, "username": "cajero", "full_name": "Cajero Principal"}
        
        self.setWindowTitle("Movimientos de Caja: Sangría / Fondo Fijo [F7]")
        self.resize(520, 520)
        self.setFixedSize(520, 520)
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 18, 22, 18)
        main_layout.setSpacing(14)

        # Título
        lbl_title = QLabel("💵 MOVIMIENTO DE EFECTIVO EN CAJA")
        lbl_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #1a237e;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_title)

        lbl_sub = QLabel("Registro formal de retiros de seguridad a tesorería y fondos de cambio")
        lbl_sub.setFont(QFont("Arial", 8))
        lbl_sub.setStyleSheet("color: #64748b;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_sub)

        # Formulario
        grp_form = QGroupBox("Detalle de la Operación")
        grp_form.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
        """)
        form_grid = QGridLayout(grp_form)
        form_grid.setContentsMargins(14, 12, 14, 12)
        form_grid.setSpacing(10)

        # 1. Tipo de Movimiento
        form_grid.addWidget(QLabel("Tipo de Operación:"), 0, 0)
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems([
            "📤 RETIRO_SANGRIA (Retiro de Efectivo a Tesorería)",
            "📥 FONDO_INICIAL (Fondo de Cambio de Apertura)",
            "📥 INGRESO (Ingreso Extraordinario a Caja)"
        ])
        self.combo_tipo.setStyleSheet("padding: 6px; font-weight: bold;")
        form_grid.addWidget(self.combo_tipo, 0, 1)

        # 2. Moneda
        form_grid.addWidget(QLabel("Moneda:"), 1, 0)
        self.combo_mnd = QComboBox()
        self.combo_mnd.addItems(["PYG - Guaraníes", "USD - Dólares", "BRL - Reales (Efectivo/PIX)", "ARS - Pesos"])
        self.combo_mnd.setStyleSheet("padding: 6px;")
        form_grid.addWidget(self.combo_mnd, 1, 1)

        # 3. Monto
        form_grid.addWidget(QLabel("Monto:"), 2, 0)
        self.txt_monto = QLineEdit()
        self.txt_monto.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.txt_monto.setPlaceholderText("Ej: 500000 o 100.00")
        self.txt_monto.setStyleSheet("""
            QLineEdit {
                border: 2px solid #3b82f6;
                border-radius: 4px;
                padding: 6px 10px;
                color: #1e3a8a;
            }
        """)
        form_grid.addWidget(self.txt_monto, 2, 1)

        # 4. Concepto / Justificación
        form_grid.addWidget(QLabel("Concepto / Motivo:"), 3, 0)
        self.txt_concepto = QLineEdit("Retiro de seguridad por exceso de efectivo en caja")
        self.txt_concepto.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px;")
        form_grid.addWidget(self.txt_concepto, 3, 1)

        main_layout.addWidget(grp_form)

        # Comprobante / Vale preview
        self.txt_ticket_preview = QTextEdit()
        self.txt_ticket_preview.setReadOnly(True)
        self.txt_ticket_preview.setFont(QFont("Courier New", 9))
        self.txt_ticket_preview.setStyleSheet("background-color: #f8fafc; border: 1px dashed #cbd5e1; padding: 6px;")
        self.txt_ticket_preview.setPlaceholderText("Al registrar el movimiento, se generará el Vale de Caja para firma.")
        main_layout.addWidget(self.txt_ticket_preview, stretch=1)

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_guardar = QPushButton("✅ Registrar y Emitir Vale")
        self.btn_guardar.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #1b5e20;
                color: white;
                padding: 10px 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2e7d32;
            }
        """)
        self.btn_guardar.clicked.connect(self.guardar_movimiento)

        self.btn_cerrar = QPushButton("Cerrar [Esc]")
        self.btn_cerrar.setStyleSheet("padding: 10px 16px;")
        self.btn_cerrar.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_cerrar)
        main_layout.addLayout(btn_layout)

        # Focus inicial en monto
        self.txt_monto.setFocus()
        self.txt_monto.textChanged.connect(self.aplicar_regla_coma)
        self.txt_monto.returnPressed.connect(self.guardar_movimiento)
        
        self.combo_mnd.currentTextChanged.connect(lambda: self.aplicar_regla_coma(self.txt_monto.text()))

    def aplicar_regla_coma(self, text):
        if not text:
            return
            
        # Si es Guaraníes, formatear con puntos de miles (sin decimales)
        if "PYG" in self.combo_mnd.currentText():
            raw = "".join(c for c in text if c.isdigit())
            if raw:
                formatted = f"{int(raw):,}".replace(",", ".")
                self.txt_monto.blockSignals(True)
                self.txt_monto.setText(formatted)
                self.txt_monto.blockSignals(False)
        else:
            # Para otras monedas, permitir un separador decimal (coma o punto)
            # Solo limpiamos caracteres extraños
            clean = "".join(c for c in text if c.isdigit() or c in ".,")
            if clean != text:
                self.txt_monto.blockSignals(True)
                self.txt_monto.setText(clean)
                self.txt_monto.blockSignals(False)

    def guardar_movimiento(self):
        txt = self.txt_monto.text().strip()
        if not txt:
            QMessageBox.warning(self, "Dato Requerido", "Ingrese el monto del movimiento.")
            self.txt_monto.setFocus()
            return
            
        # Parseo robusto del monto (Regla de la coma)
        if "PYG" in self.combo_mnd.currentText():
            monto_str = txt.replace(".", "").replace(",", "")
        else:
            # Si tiene punto y coma (ej. 1.000,50) -> el último es el decimal
            if "." in txt and "," in txt:
                if txt.rfind(",") > txt.rfind("."):
                    monto_str = txt.replace(".", "").replace(",", ".")
                else:
                    monto_str = txt.replace(",", "")
            # Si solo tiene coma, asumimos que es decimal (ej. 10,50)
            elif "," in txt:
                # A menos que sean exactamente 3 ceros después de la única coma (ej 1,000)
                partes = txt.split(",")
                if len(partes) == 2 and len(partes[1]) == 3:
                    monto_str = txt.replace(",", "") # Asumimos miles
                else:
                    monto_str = txt.replace(",", ".")
            else:
                monto_str = txt

        try:
            monto = Decimal(monto_str)
            if monto <= 0:
                raise ValueError("El monto debe ser mayor a 0.")
        except Exception as e:
            QMessageBox.warning(self, "Monto Inválido", f"El monto ingresado no es válido: {e}")
            self.txt_monto.selectAll()
            self.txt_monto.setFocus()
            return

        tipo_sel = self.combo_tipo.currentText().split(" ")[0].replace("📤_", "").replace("📥_", "")
        if "RETIRO_SANGRIA" in self.combo_tipo.currentText():
            tipo = "RETIRO_SANGRIA"
        elif "FONDO_INICIAL" in self.combo_tipo.currentText():
            tipo = "FONDO_INICIAL"
        else:
            tipo = "INGRESO"

        mnd_sel = self.combo_mnd.currentText().split(" ")[0]
        concepto = self.txt_concepto.text().strip() or "Movimiento de caja"

        db = SessionLocal()
        try:
            # Obtener sesión de caja
            sesion = None
            if self.session_id:
                sesion = db.query(models.CashSession).filter_by(id=self.session_id).first()
            if not sesion:
                sesion = db.query(models.CashSession).filter_by(status='OPEN').order_by(models.CashSession.id.desc()).first()
            if not sesion:
                sesion = models.CashSession(status='OPEN', user_id=self.current_user.get('id', 1))
                db.add(sesion)
                db.flush()

            # Crear movimiento inmutable
            mov = models.CashMovement(
                session_id=sesion.id,
                tipo=tipo,
                monto=monto,
                moneda=mnd_sel,
                concepto=concepto,
                fecha=datetime.datetime.utcnow(),
                user_id=self.current_user.get('id', 1)
            )
            db.add(mov)
            db.commit()
            db.refresh(mov)

            # Generar comprobante impreso (Vale de Caja)
            now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            monto_fmt = f"Gs. {monto:,.0f}" if mnd_sel == 'PYG' else f"{mnd_sel} {monto:,.2f}"
            tipo_label = "RETIRO DE CAJA (SANGRÍA)" if tipo == 'RETIRO_SANGRIA' else ("FONDO INICIAL DE APERTURA" if tipo == 'FONDO_INICIAL' else "INGRESO EXTRA")

            ticket_text = f"""==========================================
        SUPERMERCADO CENTRAL
    VALE OFICIAL DE MOVIMIENTO DE CAJA
==========================================
COMPROBANTE Nº: VALE-{mov.id:06d}
SESIÓN DE CAJA: #{sesion.id}
FECHA / HORA  : {now_str}
CAJERO        : {self.current_user['full_name']}
OPERACIÓN     : {tipo_label}
MONEDA        : {mnd_sel}
MONTO         : {monto_fmt}
CONCEPTO      : {concepto}
==========================================

  __________________      __________________
    Firma Cajero            Firma Tesorería
==========================================
"""
            self.txt_ticket_preview.setPlainText(ticket_text)
            self.btn_guardar.setEnabled(False)
            self.btn_cerrar.setText("Aceptar y Salir")
            QMessageBox.information(self, "Movimiento Registrado", f"Se registró con éxito el movimiento {tipo_label} por {monto_fmt}.")

        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar movimiento: {e}")
        finally:
            db.close()
