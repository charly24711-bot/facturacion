import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from database import SessionLocal
import models


class BatchesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 Control de Lotes y Vencimientos")
        self.resize(850, 500)
        self.setup_ui()
        self.load_batches()

    def setup_ui(self):
        main = QVBoxLayout(self)

        # ── Filtros ─────────────────────────────────────────────────────────
        grp_filter = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filtrar por código o descripción del producto...")
        self.txt_search.textChanged.connect(self.load_batches)
        
        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.clicked.connect(self.load_batches)

        filter_layout.addWidget(self.txt_search, stretch=1)
        filter_layout.addWidget(self.btn_refresh)
        grp_filter.setLayout(filter_layout)
        main.addWidget(grp_filter)

        # ── Grilla ─────────────────────────────────────────────────────────
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Código Prod.", "Producto", "Lote", "Vencimiento", "Stock del Lote", "Estado"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main.addWidget(self.table, stretch=1)
        
        # ── Leyenda ────────────────────────────────────────────────────────
        leyenda_layout = QHBoxLayout()
        lbl_vencido = QLabel("■ Vencido")
        lbl_vencido.setStyleSheet("color: white; background-color: #c0392b; padding: 4px; font-weight: bold;")
        lbl_prox = QLabel("■ Vence en < 30 días")
        lbl_prox.setStyleSheet("color: black; background-color: #f39c12; padding: 4px; font-weight: bold;")
        lbl_ok = QLabel("■ Vigente")
        lbl_ok.setStyleSheet("color: white; background-color: #27ae60; padding: 4px; font-weight: bold;")
        
        leyenda_layout.addStretch()
        leyenda_layout.addWidget(lbl_ok)
        leyenda_layout.addWidget(lbl_prox)
        leyenda_layout.addWidget(lbl_vencido)
        
        main.addLayout(leyenda_layout)

    def load_batches(self):
        query_text = self.txt_search.text().lower().strip()
        self.table.setRowCount(0)
        
        db = SessionLocal()
        
        # Obtener lotes con stock > 0, ordenados por vencimiento (los que vencen antes primero)
        query = (db.query(models.ProductBatch)
                   .join(models.Product)
                   .filter(models.ProductBatch.stock_actual > 0)
                   .order_by(models.ProductBatch.fecha_vencimiento.asc()))
                   
        batches = query.all()
        now = datetime.datetime.now()
        
        for b in batches:
            # Filtrar manual
            prod = b.product
            if query_text:
                if not prod or (query_text not in prod.art_codigo.lower() and query_text not in prod.art_descri.lower()):
                    continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            descri = prod.art_descri if prod else "Desconocido"
            codigo = prod.art_codigo if prod else "-"
            venc_date = b.fecha_vencimiento
            
            venc_str = venc_date.strftime("%d/%m/%Y") if venc_date else "Sin fecha"
            
            # Evaluar estado
            estado = "Vigente"
            color = QColor("#27ae60") # verde
            fg_color = QColor("white")
            
            if venc_date:
                days_left = (venc_date - now).days
                if days_left < 0:
                    estado = "Vencido"
                    color = QColor("#c0392b") # rojo
                elif days_left <= 30:
                    estado = "Próximo a Vencer"
                    color = QColor("#f39c12") # amarillo
                    fg_color = QColor("black")
            
            self.table.setItem(row, 0, QTableWidgetItem(codigo))
            self.table.setItem(row, 1, QTableWidgetItem(descri))
            self.table.setItem(row, 2, QTableWidgetItem(b.lote or "-"))
            
            i_venc = QTableWidgetItem(venc_str)
            self.table.setItem(row, 3, i_venc)
            
            i_stock = QTableWidgetItem(f"{float(b.stock_actual):g}")
            i_stock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, i_stock)
            
            i_est = QTableWidgetItem(estado)
            i_est.setBackground(color)
            i_est.setForeground(fg_color)
            f = i_est.font()
            f.setBold(True)
            i_est.setFont(f)
            self.table.setItem(row, 5, i_est)
            
        db.close()
