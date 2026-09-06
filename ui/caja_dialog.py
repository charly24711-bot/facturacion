from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, 
                             QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database import SessionLocal
import models
from decimal import Decimal
import datetime

class CajaDialog(QDialog):
    def __init__(self, session_id=None, current_user=None, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.current_user = current_user or {"id": 1, "username": "cajero", "full_name": "Cajero Principal"}
        self.setWindowTitle("Arqueo y Movimientos de Caja del Día")
        self.resize(780, 600)
        
        main_layout = QVBoxLayout(self)
        
        # --- TABLA DE MOVIMIENTOS ---
        group_movs = QGroupBox("Movimientos de Caja del Día (Ventas y Sangrías)")
        movs_layout = QVBoxLayout(group_movs)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Ref", "Hora", "Tipo", "Concepto / Ref", "Monto", "Moneda"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        movs_layout.addWidget(self.table)
        
        main_layout.addWidget(group_movs, stretch=2)
        
        # --- CONSOLIDADO POR MONEDA ---
        group_totales = QGroupBox("Consolidado Físico Esperado en Caja (Efectivo Neto)")
        totales_layout = QGridLayout(group_totales)
        
        font_monto = QFont("Arial", 16, QFont.Weight.Bold)
        
        # Labels para mostrar los totales
        self.lbl_pyg = QLabel("0")
        self.lbl_usd = QLabel("0.00")
        self.lbl_brl = QLabel("0.00")
        self.lbl_ars = QLabel("0.00")
        
        self.lbl_pyg.setFont(font_monto)
        self.lbl_usd.setFont(font_monto)
        self.lbl_brl.setFont(font_monto)
        self.lbl_ars.setFont(font_monto)
        
        self.lbl_pyg.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_usd.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_brl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_ars.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        totales_layout.addWidget(QLabel("GUARANÍES (PYG):"), 0, 0)
        totales_layout.addWidget(self.lbl_pyg, 0, 1)
        
        totales_layout.addWidget(QLabel("DÓLARES (USD):"), 1, 0)
        totales_layout.addWidget(self.lbl_usd, 1, 1)
        
        totales_layout.addWidget(QLabel("REALES (BRL):"), 0, 2)
        totales_layout.addWidget(self.lbl_brl, 0, 3)
        
        totales_layout.addWidget(QLabel("PESOS (ARS):"), 1, 2)
        totales_layout.addWidget(self.lbl_ars, 1, 3)
        
        main_layout.addWidget(group_totales)
        
        # --- BOTONES ---
        btn_layout = QHBoxLayout()
        
        btn_sangria = QPushButton("💸 Movimiento / Sangría [F7]")
        btn_sangria.setStyleSheet("background-color: #00695c; color: white; font-weight: bold; padding: 8px 14px;")
        btn_sangria.clicked.connect(self.open_movimiento)
        
        btn_imprimir = QPushButton("Imprimir Cierre (Z)")
        btn_imprimir.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold; padding: 8px 14px;")
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet("padding: 8px 14px;")
        btn_cerrar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_sangria)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_imprimir)
        btn_layout.addWidget(btn_cerrar)
        
        main_layout.addLayout(btn_layout)
        
        self.cargar_movimientos_hoy()
        
    def open_movimiento(self):
        from ui.caja_movimiento_dialog import CajaMovimientoDialog
        dialog = CajaMovimientoDialog(session_id=self.session_id, current_user=self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.cargar_movimientos_hoy()
        
    def cargar_movimientos_hoy(self):
        db = SessionLocal()
        
        # Obtener fecha de hoy (inicio y fin)
        hoy = datetime.datetime.utcnow().date()
        inicio_dia = datetime.datetime(hoy.year, hoy.month, hoy.day)
        fin_dia = datetime.datetime(hoy.year, hoy.month, hoy.day, 23, 59, 59)
        
        pagos = db.query(models.Payment).filter(
            models.Payment.cob_fecha >= inicio_dia,
            models.Payment.cob_fecha <= fin_dia
        ).all()

        movs = db.query(models.CashMovement).filter(
            models.CashMovement.fecha >= inicio_dia,
            models.CashMovement.fecha <= fin_dia
        ).all()
        
        totales = {"PYG": Decimal('0'), "USD": Decimal('0'), "BRL": Decimal('0'), "ARS": Decimal('0')}
        
        self.table.setRowCount(0)
        row = 0

        # Cargar pagos / cobranzas de ventas
        for pago in pagos:
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"COB-{pago.id}"))
            
            hora = pago.cob_fecha.strftime("%H:%M:%S")
            self.table.setItem(row, 1, QTableWidgetItem(hora))
            self.table.setItem(row, 2, QTableWidgetItem(f"VENTA ({pago.cob_metodo})"))
            self.table.setItem(row, 3, QTableWidgetItem(f"Factura Nº {pago.cob_vennro}"))
            
            monto_dec = Decimal(str(pago.cob_monto or '0'))
            monto_str = f"{monto_dec:,.0f}" if pago.cob_mndori == "PYG" else f"{monto_dec:,.2f}"
            
            item_monto = QTableWidgetItem(monto_str)
            item_monto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, item_monto)
            self.table.setItem(row, 5, QTableWidgetItem(pago.cob_mndori))
            
            if pago.cob_mndori in totales:
                totales[pago.cob_mndori] += monto_dec
            row += 1

        # Cargar movimientos de caja (Fondo Inicial / Sangrías)
        for m in movs:
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"MOV-{m.id}"))
            
            hora = m.fecha.strftime("%H:%M:%S")
            self.table.setItem(row, 1, QTableWidgetItem(hora))
            
            es_ingreso = m.tipo in ('FONDO_INICIAL', 'INGRESO')
            tipo_label = "📥 FONDO/ING." if es_ingreso else "📤 SANGRÍA/RET."
            item_tipo = QTableWidgetItem(tipo_label)
            if not es_ingreso:
                item_tipo.setForeground(QColor("#c62828"))
            else:
                item_tipo.setForeground(QColor("#2e7d32"))
            self.table.setItem(row, 2, item_tipo)
            
            self.table.setItem(row, 3, QTableWidgetItem(m.concepto or "-"))
            
            monto_dec = Decimal(str(m.monto or '0'))
            signo = "+" if es_ingreso else "-"
            monto_str = f"{signo}{monto_dec:,.0f}" if m.moneda == "PYG" else f"{signo}{monto_dec:,.2f}"
            
            item_monto = QTableWidgetItem(monto_str)
            item_monto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if not es_ingreso:
                item_monto.setForeground(QColor("#c62828"))
            else:
                item_monto.setForeground(QColor("#2e7d32"))
            self.table.setItem(row, 4, item_monto)
            self.table.setItem(row, 5, QTableWidgetItem(m.moneda))
            
            if m.moneda in totales:
                if es_ingreso:
                    totales[m.moneda] += monto_dec
                else:
                    totales[m.moneda] -= monto_dec
            row += 1
                
        # Actualizar labels de consolidado físico
        self.lbl_pyg.setText(f"{totales['PYG']:,.0f}".replace(",", "."))
        self.lbl_usd.setText(f"{totales['USD']:,.2f}")
        self.lbl_brl.setText(f"{totales['BRL']:,.2f}")
        self.lbl_ars.setText(f"{totales['ARS']:,.2f}")
        
        db.close()
