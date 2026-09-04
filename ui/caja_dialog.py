from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, 
                             QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import SessionLocal
import models
import datetime

class CajaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Arqueo de Caja del Día")
        self.resize(700, 600)
        
        main_layout = QVBoxLayout(self)
        
        # --- TABLA DE MOVIMIENTOS ---
        group_movs = QGroupBox("Movimientos del Día")
        movs_layout = QVBoxLayout(group_movs)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID Cobro", "Hora", "Factura Nº", "Monto", "Moneda"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        movs_layout.addWidget(self.table)
        
        main_layout.addWidget(group_movs, stretch=2)
        
        # --- CONSOLIDADO POR MONEDA ---
        group_totales = QGroupBox("Consolidado (Dinero Físico en Caja)")
        totales_layout = QGridLayout(group_totales)
        
        font_monto = QFont("Arial", 16, QFont.Weight.Bold)
        
        # Labels para mostrar los totales
        self.lbl_pyg = QLabel("0")
        self.lbl_usd = QLabel("0")
        self.lbl_brl = QLabel("0")
        self.lbl_ars = QLabel("0")
        
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
        btn_layout.addStretch()
        
        btn_imprimir = QPushButton("Imprimir Cierre (Z)")
        btn_imprimir.setStyleSheet("background-color: blue; color: white; font-weight: bold; padding: 8px;")
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_imprimir)
        btn_layout.addWidget(btn_cerrar)
        
        main_layout.addLayout(btn_layout)
        
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
        
        totales = {"PYG": 0.0, "USD": 0.0, "BRL": 0.0, "ARS": 0.0}
        
        self.table.setRowCount(0)
        for row, pago in enumerate(pagos):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(pago.id)))
            
            hora = pago.cob_fecha.strftime("%H:%M:%S")
            self.table.setItem(row, 1, QTableWidgetItem(hora))
            
            self.table.setItem(row, 2, QTableWidgetItem(str(pago.cob_vennro)))
            
            monto_str = f"{pago.cob_monto:,.2f}" if pago.cob_mndori != "PYG" else f"{pago.cob_monto:,.0f}"
            self.table.setItem(row, 3, QTableWidgetItem(monto_str))
            self.table.setItem(row, 4, QTableWidgetItem(pago.cob_mndori))
            
            if pago.cob_mndori in totales:
                totales[pago.cob_mndori] += pago.cob_monto
                
        # Actualizar labels de resumen
        self.lbl_pyg.setText(f"{totales['PYG']:,.0f}")
        self.lbl_usd.setText(f"{totales['USD']:,.2f}")
        self.lbl_brl.setText(f"{totales['BRL']:,.2f}")
        self.lbl_ars.setText(f"{totales['ARS']:,.2f}")
        
        db.close()
