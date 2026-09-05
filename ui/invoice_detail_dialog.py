from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import SessionLocal
import models

class InvoiceDetailDialog(QDialog):
    def __init__(self, invoice_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalle de Factura #{invoice_id}")
        self.resize(600, 400)
        
        self.invoice_id = invoice_id
        
        main_layout = QVBoxLayout(self)
        
        # --- CABECERA ---
        cabecera_layout = QGridLayout()
        
        self.lbl_fecha = QLabel()
        self.lbl_cliente = QLabel()
        self.lbl_total = QLabel()
        self.lbl_total.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.lbl_moneda = QLabel()
        
        cabecera_layout.addWidget(QLabel("Fecha:"), 0, 0)
        cabecera_layout.addWidget(self.lbl_fecha, 0, 1)
        
        cabecera_layout.addWidget(QLabel("Cliente:"), 1, 0)
        cabecera_layout.addWidget(self.lbl_cliente, 1, 1)
        
        cabecera_layout.addWidget(QLabel("Total:"), 0, 2)
        cabecera_layout.addWidget(self.lbl_total, 0, 3)
        
        cabecera_layout.addWidget(QLabel("Moneda de Pago:"), 1, 2)
        cabecera_layout.addWidget(self.lbl_moneda, 1, 3)
        
        group_cabecera = QGroupBox("Datos de la Venta")
        group_cabecera.setLayout(cabecera_layout)
        main_layout.addWidget(group_cabecera)
        
        # --- DETALLE (Ítems) ---
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción", "Cantidad", "Precio Unit."])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        main_layout.addWidget(self.table, stretch=1)
        
        self.cargar_datos()
        
    def cargar_datos(self):
        db = SessionLocal()
        
        factura = db.query(models.Invoice).filter_by(id=self.invoice_id).first()
        if factura:
            self.lbl_fecha.setText(factura.ven_fecha.strftime("%d/%m/%Y %H:%M:%S"))
            
            cliente_nombre = factura.client.cli_nombre if factura.client else "CONSUMIDOR FINAL"
            self.lbl_cliente.setText(f"{factura.ven_codcli} - {cliente_nombre}")
            
            self.lbl_total.setText(f"{factura.ven_total:,.0f} PYG")
            
            pago = db.query(models.Payment).filter_by(cob_vennro=factura.id).first()
            if pago:
                monto_str = f"{pago.cob_monto:,.2f}" if pago.cob_mndori != "PYG" else f"{pago.cob_monto:,.0f}"
                self.lbl_moneda.setText(f"{monto_str} {pago.cob_mndori}")
            
            # Cargar ítems
            items = db.query(models.InvoiceItem).filter_by(vit_numero=factura.id).all()
            self.table.setRowCount(0)
            for row, item in enumerate(items):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(item.vit_articu))
                
                descri = item.product.art_descri if item.product else "Desconocido"
                self.table.setItem(row, 1, QTableWidgetItem(descri))
                
                canti_formateada = f"{float(item.vit_canti):g}"
                self.table.setItem(row, 2, QTableWidgetItem(canti_formateada))
                self.table.setItem(row, 3, QTableWidgetItem(f"{item.vit_precio:,.0f}"))
                
        db.close()
