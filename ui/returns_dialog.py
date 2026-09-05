from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QAbstractItemView, QInputDialog, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from database import SessionLocal
import models
import datetime


class ReturnsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("↩️ Devoluciones (Nota de Crédito)")
        self.resize(800, 500)
        self.current_invoice = None
        self.setup_ui()

    def setup_ui(self):
        main = QVBoxLayout(self)

        # ── Buscador de Factura ────────────────────────────────────────────
        grp_search = QGroupBox("Buscar Ticket / Factura Origen")
        search_layout = QHBoxLayout()

        self.txt_nro = QLineEdit()
        self.txt_nro.setPlaceholderText("Ingrese el Nro. de Factura y presione Enter")
        self.txt_nro.returnPressed.connect(self.buscar_factura)

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.clicked.connect(self.buscar_factura)

        search_layout.addWidget(self.txt_nro, stretch=1)
        search_layout.addWidget(btn_buscar)
        grp_search.setLayout(search_layout)
        main.addWidget(grp_search)

        # ── Detalles de la Factura ─────────────────────────────────────────
        self.lbl_info = QLabel("Factura: —  |  Fecha: —  |  Cliente: —")
        self.lbl_info.setStyleSheet("font-weight: bold; color: #2980b9; padding: 5px;")
        main.addWidget(self.lbl_info)

        # ── Grilla de Ítems ────────────────────────────────────────────────
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Cód. Producto", "Descripción", "Precio (₲)", "Cant. Comprada", "Cant. a Devolver"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        main.addWidget(self.table, stretch=1)

        # ── Botón Procesar ─────────────────────────────────────────────────
        foot = QHBoxLayout()
        self.btn_procesar = QPushButton("✅ Procesar Devolución")
        self.btn_procesar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        self.btn_procesar.clicked.connect(self.procesar_devolucion)
        self.btn_procesar.setEnabled(False)
        
        foot.addStretch()
        foot.addWidget(self.btn_procesar)
        main.addLayout(foot)

    # ── Lógica ─────────────────────────────────────────────────────────────
    def buscar_factura(self):
        nro = self.txt_nro.text().strip()
        if not nro.isdigit():
            QMessageBox.warning(self, "Error", "Ingrese un número de factura válido.")
            return

        db = SessionLocal()
        fac = db.query(models.Invoice).filter_by(ven_numero=int(nro), ven_tipo='FA').first()
        
        if not fac:
            QMessageBox.information(self, "No encontrado", f"No se encontró la factura número {nro}.")
            self.current_invoice = None
            self.lbl_info.setText("Factura: —  |  Fecha: —  |  Cliente: —")
            self.table.setRowCount(0)
            self.btn_procesar.setEnabled(False)
            db.close()
            return
            
        self.current_invoice = fac.id
        cli_nombre = fac.client.cli_nombre if fac.client else "CONSUMIDOR FINAL"
        fecha_str = fac.ven_fecha.strftime("%d/%m/%Y") if fac.ven_fecha else "—"
        
        self.lbl_info.setText(f"Factura: #{fac.ven_numero}  |  Fecha: {fecha_str}  |  Cliente: {cli_nombre}")
        
        # Cargar ítems
        self.table.setRowCount(0)
        items = db.query(models.InvoiceItem).filter_by(vit_numero=fac.id).all()
        
        for it in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            prod = db.query(models.Product).filter_by(art_codigo=it.vit_articu).first()
            descri = prod.art_descri if prod else "Producto Eliminado"
            
            self.table.setItem(row, 0, QTableWidgetItem(it.vit_articu))
            self.table.setItem(row, 1, QTableWidgetItem(descri))
            self.table.setItem(row, 2, QTableWidgetItem(f"₲ {float(it.vit_precio):,.0f}"))
            
            # Cantidad original
            i_cant = QTableWidgetItem(f"{float(it.vit_canti):g}")
            i_cant.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, i_cant)
            
            # Spinbox para seleccionar cuánto devolver
            spin = QSpinBox()
            spin.setRange(0, int(it.vit_canti))
            spin.setValue(0)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Store original price data in spinbox for easy retrieval
            spin.setProperty("precio", float(it.vit_precio))
            
            self.table.setCellWidget(row, 4, spin)
            
        self.btn_procesar.setEnabled(True)
        db.close()

    def procesar_devolucion(self):
        if not self.current_invoice:
            return
            
        # Recolectar devoluciones
        devoluciones = []
        total_nc = 0.0
        
        for row in range(self.table.rowCount()):
            cod = self.table.item(row, 0).text()
            spin = self.table.cellWidget(row, 4)
            cant_dev = spin.value()
            precio = spin.property("precio")
            
            if cant_dev > 0:
                devoluciones.append({
                    'codigo': cod,
                    'cantidad': cant_dev,
                    'precio': precio
                })
                total_nc += cant_dev * precio
                
        if not devoluciones:
            QMessageBox.information(self, "Aviso", "No ha seleccionado ninguna cantidad para devolver.")
            return
            
        resp = QMessageBox.question(
            self, "Confirmar", 
            f"Se generará una Nota de Crédito por ₲ {total_nc:,.0f} y se reingresará el stock.\\n\\n¿Desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.No:
            return
            
        db = SessionLocal()
        fac_origen = db.query(models.Invoice).get(self.current_invoice)
        
        # 1. Crear Factura tipo NC
        nc = models.Invoice(
            ven_tipo='NC',
            ven_codcli=fac_origen.ven_codcli,
            ven_total=total_nc,
            ven_codmnd='PYG'
        )
        db.add(nc)
        db.flush()
        
        # 2. Detalles y Restaurar Stock
        for dev in devoluciones:
            # Crear item
            item = models.InvoiceItem(
                vit_numero=nc.id,
                vit_articu=dev['codigo'],
                vit_canti=dev['cantidad'],
                vit_precio=dev['precio']
            )
            db.add(item)
            
            # Reingresar stock
            prod = db.query(models.Product).filter_by(art_codigo=dev['codigo']).first()
            if prod:
                prod.art_stkini += dev['cantidad']
                
        # 3. Si el cliente tiene cuenta corriente, registrar saldo a favor
        if fac_origen.ven_codcli and fac_origen.ven_codcli != "000001":
            cliente = db.query(models.Client).filter_by(cli_codigo=fac_origen.ven_codcli).first()
            if cliente:
                trx = models.CustomerTransaction(
                    client_id=cliente.id,
                    tipo='PAYMENT', # Payment actúa como saldo a favor / resta deuda
                    monto=total_nc,
                    referencia=f"Nota de Crédito #{nc.id}"
                )
                db.add(trx)
                
        db.commit()
        db.close()
        
        QMessageBox.information(self, "Éxito", "Devolución procesada correctamente.")
        self.txt_nro.clear()
        self.table.setRowCount(0)
        self.lbl_info.setText("Factura: —  |  Fecha: —  |  Cliente: —")
        self.btn_procesar.setEnabled(False)
        self.current_invoice = None
