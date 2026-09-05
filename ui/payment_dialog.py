from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QHBoxLayout, QMessageBox, QLabel, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database import SessionLocal
import models
from decimal import Decimal
import math

class PaymentDialog(QDialog):
    def __init__(self, totals, client=None, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("Cobro Split Multimoneda [F11]")
        self.resize(700, 600)
        
        self.total_adeudado_pyg = Decimal(str(totals.get('PYG', 0.0)))
        self.payment_successful = False
        self.payments_list = []
        
        # Cargar Tasas Activas
        self.tasas = self.cargar_tasas()
        
        self.setup_ui()
        self.actualizar_saldos()
        
    def cargar_tasas(self):
        db = SessionLocal()
        rates_db = db.query(models.CurrencyRate).filter_by(is_active=True).all()
        db.close()
        
        tasas = {
            'PYG': {'buy': Decimal("1.0"), 'sell': Decimal("1.0")}
        }
        for r in rates_db:
            tasas[r.currency_code] = {
                'buy': r.buy_rate,
                'sell': r.sell_rate
            }
        return tasas

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- CABECERA ---
        lbl_title = QLabel("TOTAL A COBRAR")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_layout.addWidget(lbl_title)
        
        self.lbl_total_pyg = QLabel(f"Gs. {self.total_adeudado_pyg:,.0f}")
        self.lbl_total_pyg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_total_pyg.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self.lbl_total_pyg.setStyleSheet("color: darkblue;")
        main_layout.addWidget(self.lbl_total_pyg)
        
        # --- PANEL DE INGRESO DE PAGOS ---
        group_ingreso = QGroupBox("Añadir Pago Parcial")
        layout_ingreso = QHBoxLayout(group_ingreso)
        
        self.combo_moneda = QComboBox()
        self.combo_moneda.addItems(["PYG", "USD", "BRL", "ARS"])
        self.combo_moneda.currentTextChanged.connect(self.mostrar_cotizacion_actual)
        
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(["Efectivo", "Tarjeta Crédito", "Tarjeta Débito", "PIX", "Transferencia Bancaria", "Cuenta Corriente"])
        
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Monto entregado")
        self.txt_monto.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.txt_monto.textChanged.connect(self.format_monto)
        self.txt_monto.returnPressed.connect(self.agregar_pago)
        
        self.lbl_cotizacion_act = QLabel("Tasa: 1.0")
        
        btn_add = QPushButton("Agregar Pago")
        btn_add.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_add.clicked.connect(self.agregar_pago)
        
        layout_ingreso.addWidget(QLabel("Moneda:"))
        layout_ingreso.addWidget(self.combo_moneda)
        layout_ingreso.addWidget(self.lbl_cotizacion_act)
        layout_ingreso.addWidget(QLabel("Método:"))
        layout_ingreso.addWidget(self.combo_metodo)
        layout_ingreso.addWidget(QLabel("Monto:"))
        layout_ingreso.addWidget(self.txt_monto)
        layout_ingreso.addWidget(btn_add)
        
        main_layout.addWidget(group_ingreso)
        
        # --- GRILLA DE PAGOS ---
        self.table_pagos = QTableWidget(0, 5)
        self.table_pagos.setHorizontalHeaderLabels(["Moneda", "Método", "Monto Origen", "Cotización (Compra)", "Subtotal (PYG)"])
        self.table_pagos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_pagos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table_pagos)
        
        btn_eliminar_pago = QPushButton("Eliminar Pago Seleccionado")
        btn_eliminar_pago.clicked.connect(self.eliminar_pago)
        main_layout.addWidget(btn_eliminar_pago, alignment=Qt.AlignmentFlag.AlignRight)
        
        # --- PANEL DE SALDOS Y VUELTO ---
        group_saldos = QGroupBox("Estado de Cuenta")
        layout_saldos = QGridLayout(group_saldos)
        
        font_saldos = QFont("Arial", 14, QFont.Weight.Bold)
        
        layout_saldos.addWidget(QLabel("Total Recibido (PYG):"), 0, 0)
        self.lbl_recibido = QLabel("0")
        self.lbl_recibido.setFont(font_saldos)
        layout_saldos.addWidget(self.lbl_recibido, 0, 1)
        
        layout_saldos.addWidget(QLabel("Faltante (PYG):"), 1, 0)
        self.lbl_faltante = QLabel("0")
        self.lbl_faltante.setFont(font_saldos)
        self.lbl_faltante.setStyleSheet("color: red;")
        layout_saldos.addWidget(self.lbl_faltante, 1, 1)
        
        layout_saldos.addWidget(QLabel("VUELTO (PYG):"), 2, 0)
        self.lbl_vuelto_pyg = QLabel("0")
        self.lbl_vuelto_pyg.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.lbl_vuelto_pyg.setStyleSheet("color: green;")
        layout_saldos.addWidget(self.lbl_vuelto_pyg, 2, 1)
        
        # Calculadora de Vuelto Cruzado
        layout_saldos.addWidget(QLabel("Moneda para Vuelto:"), 3, 0)
        self.combo_vuelto_moneda = QComboBox()
        self.combo_vuelto_moneda.addItems(["PYG", "USD", "BRL", "ARS"])
        self.combo_vuelto_moneda.currentTextChanged.connect(self.actualizar_saldos)
        layout_saldos.addWidget(self.combo_vuelto_moneda, 3, 1)
        
        layout_saldos.addWidget(QLabel("VUELTO A ENTREGAR:"), 4, 0)
        self.lbl_vuelto_final = QLabel("0")
        self.lbl_vuelto_final.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.lbl_vuelto_final.setStyleSheet("color: darkgreen; background-color: #e8f5e9; padding: 5px;")
        layout_saldos.addWidget(self.lbl_vuelto_final, 4, 1)
        
        main_layout.addWidget(group_saldos)
        
        # --- BOTONES DE ACCIÓN ---
        btn_layout = QHBoxLayout()
        self.btn_cobrar = QPushButton("Confirmar Factura [Enter]")
        self.btn_cobrar.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 15px; font-size: 16px;")
        self.btn_cobrar.clicked.connect(self.procesar_cobro)
        self.btn_cobrar.setEnabled(False)
        
        btn_cancelar = QPushButton("Cancelar [Esc]")
        btn_cancelar.setStyleSheet("padding: 15px; font-size: 16px;")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_cobrar)
        main_layout.addLayout(btn_layout)
        
        self.mostrar_cotizacion_actual(self.combo_moneda.currentText())

    def mostrar_cotizacion_actual(self, moneda):
        tasa_compra = self.tasas.get(moneda, {}).get('buy', Decimal("1.0"))
        self.lbl_cotizacion_act.setText(f"Tasa: {tasa_compra:,.2f}")


    def format_monto(self, text):
        if not text:
            return
        
        # Guardar posición del cursor
        cursor_pos = self.txt_monto.cursorPosition()
        
        clean_text = text.replace(",", "")
        
        try:
            parts = clean_text.split(".")
            if len(parts) == 1:
                if parts[0].isdigit():
                    formatted = f"{int(parts[0]):,}"
                else:
                    formatted = parts[0]
            elif len(parts) == 2:
                if parts[0] == "": parts[0] = "0"
                if parts[0].isdigit():
                    formatted = f"{int(parts[0]):,}.{parts[1]}"
                else:
                    formatted = clean_text
            else:
                formatted = clean_text
                
            self.txt_monto.blockSignals(True)
            self.txt_monto.setText(formatted)
            self.txt_monto.blockSignals(False)
            
            # Ajustar posición del cursor
            diff = len(formatted) - len(text)
            self.txt_monto.setCursorPosition(cursor_pos + diff)
        except Exception:
            pass

    def agregar_pago(self):
        try:
            monto_str = self.txt_monto.text().replace(',', '')
            if not monto_str: return
            
            monto_origen = Decimal(monto_str)
            if monto_origen <= 0: return
            
            moneda = self.combo_moneda.currentText()
            metodo = self.combo_metodo.currentText()
            tasa_compra = self.tasas.get(moneda, {}).get('buy', Decimal("1.0"))
            
            monto_pyg = (monto_origen * tasa_compra).quantize(Decimal("1"))
            
            row = self.table_pagos.rowCount()
            self.table_pagos.insertRow(row)
            
            self.table_pagos.setItem(row, 0, QTableWidgetItem(moneda))
            self.table_pagos.setItem(row, 1, QTableWidgetItem(metodo))
            self.table_pagos.setItem(row, 2, QTableWidgetItem(f"{monto_origen:,.2f}"))
            self.table_pagos.setItem(row, 3, QTableWidgetItem(f"{tasa_compra:,.2f}"))
            self.table_pagos.setItem(row, 4, QTableWidgetItem(f"{monto_pyg:,.0f}"))
            
            self.txt_monto.clear()
            self.txt_monto.setFocus()
            
            self.actualizar_saldos()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", "Monto inválido.")
            
    def eliminar_pago(self):
        current_row = self.table_pagos.currentRow()
        if current_row >= 0:
            self.table_pagos.removeRow(current_row)
            self.actualizar_saldos()

    def actualizar_saldos(self):
        total_recibido_pyg = Decimal("0")
        for row in range(self.table_pagos.rowCount()):
            item_pyg = self.table_pagos.item(row, 4)
            if item_pyg:
                total_recibido_pyg += Decimal(item_pyg.text().replace(',', ''))
                
        self.lbl_recibido.setText(f"{total_recibido_pyg:,.0f}")
        
        faltante = self.total_adeudado_pyg - total_recibido_pyg
        if faltante > 0:
            self.lbl_faltante.setText(f"{faltante:,.0f}")
            self.lbl_vuelto_pyg.setText("0")
            self.lbl_vuelto_final.setText("0")
            self.btn_cobrar.setEnabled(False)
        else:
            self.lbl_faltante.setText("0")
            vuelto_pyg = abs(faltante)
            self.lbl_vuelto_pyg.setText(f"{vuelto_pyg:,.0f}")
            self.btn_cobrar.setEnabled(True)
            
            # Vuelto Cruzado
            moneda_vuelto = self.combo_vuelto_moneda.currentText()
            tasa_venta = self.tasas.get(moneda_vuelto, {}).get('sell', Decimal("1.0"))
            
            if moneda_vuelto == "PYG":
                vuelto_final = vuelto_pyg
                self.lbl_vuelto_final.setText(f"Gs. {vuelto_final:,.0f}")
            else:
                # Redondeo hacia abajo a 2 decimales para evitar pérdidas
                vuelto_final = math.floor((vuelto_pyg / tasa_venta) * 100) / 100.0
                self.lbl_vuelto_final.setText(f"{vuelto_final:,.2f} {moneda_vuelto}")

    def procesar_cobro(self):
        self.payments_list = []
        for row in range(self.table_pagos.rowCount()):
            moneda = self.table_pagos.item(row, 0).text()
            metodo = self.table_pagos.item(row, 1).text()
            monto_origen = Decimal(self.table_pagos.item(row, 2).text().replace(',', ''))
            monto_pyg = Decimal(self.table_pagos.item(row, 4).text().replace(',', ''))
            
            self.payments_list.append({
                'moneda': moneda,
                'metodo': metodo,
                'monto_origen': float(monto_origen),
                'monto_pyg': float(monto_pyg)
            })
            
        self.payment_successful = True
        self.accept()
