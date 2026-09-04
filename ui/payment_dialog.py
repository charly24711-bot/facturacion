from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QLabel, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import SessionLocal
import models
import datetime

class PaymentDialog(QDialog):
    def __init__(self, totals, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cobro de Factura [F11]")
        self.resize(400, 300)
        
        self.totals = totals # Dict with {'PYG': 0, 'USD': 0, 'BRL': 0, 'ARS': 0}
        self.payment_successful = False
        
        layout = QVBoxLayout(self)
        
        # Mostrar total a cobrar
        lbl_title = QLabel("TOTAL A COBRAR")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(lbl_title)
        
        lbl_amount = QLabel(f"Gs. {self.totals['PYG']:,.0f}")
        lbl_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_amount.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        lbl_amount.setStyleSheet("color: darkred;")
        layout.addWidget(lbl_amount)
        
        # Formulario de pago
        form_layout = QFormLayout()
        
        self.combo_moneda = QComboBox()
        self.combo_moneda.addItems(["PYG", "USD", "BRL", "ARS"])
        
        self.txt_recibido = QLineEdit()
        self.txt_recibido.setPlaceholderText("Monto entregado por el cliente")
        
        form_layout.addRow("Moneda de Pago:", self.combo_moneda)
        form_layout.addRow("Monto Recibido:", self.txt_recibido)
        
        layout.addLayout(form_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cobrar = QPushButton("Confirmar Pago [Enter]")
        btn_cobrar.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
        btn_cobrar.clicked.connect(self.procesar_pago)
        
        btn_cancelar = QPushButton("Cancelar [Esc]")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cobrar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
    def procesar_pago(self):
        try:
            monto_recibido = float(self.txt_recibido.text())
            moneda = self.combo_moneda.currentText()
            
            # Validar si el monto alcanza
            total_requerido = self.totals[moneda]
            if monto_recibido < total_requerido:
                QMessageBox.warning(self, "Error", f"El monto es insuficiente. Falta: {total_requerido - monto_recibido:,.2f} {moneda}")
                return
                
            vuelto = monto_recibido - total_requerido
            
            # Si hay vuelto, lo mostramos
            if vuelto > 0:
                QMessageBox.information(self, "Vuelto", f"Pago exitoso.\nVuelto a entregar: {vuelto:,.2f} {moneda}")
            else:
                QMessageBox.information(self, "Éxito", "Pago exacto registrado.")
                
            self.payment_successful = True
            self.moneda_pago = moneda
            self.monto_pagado = total_requerido # Se registra el total exacto pagado, no el recibido
            
            self.accept()
            
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingrese un monto numérico válido.")
