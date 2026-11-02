from decimal import Decimal, InvalidOperation
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QAbstractItemView, QInputDialog, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from database import SessionLocal, format_stock_qty
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
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Cód. Producto", "Descripción", "Precio (₲)", "Cant. Comprada", "Cant. a Devolver", "Destino Stock"
        ])
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
        
        # Cargar ítems (soportando vínculo por ven_numero o id)
        self.table.setRowCount(0)
        items = db.query(models.InvoiceItem).filter(
            (models.InvoiceItem.vit_numero == fac.ven_numero) |
            (models.InvoiceItem.vit_numero == fac.id)
        ).all()
        
        for it in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            prod = db.query(models.Product).filter_by(art_codigo=it.vit_articu).first()
            descri = prod.art_descri if prod else "Producto Eliminado"
            precio_dec = Decimal(str(it.vit_precio or '0')).quantize(Decimal('1'))
            canti_dec = Decimal(str(it.vit_canti or '0'))
            
            self.table.setItem(row, 0, QTableWidgetItem(it.vit_articu))
            self.table.setItem(row, 1, QTableWidgetItem(descri))
            self.table.setItem(row, 2, QTableWidgetItem(f"₲ {precio_dec:,.0f}"))
            
            # Cantidad original (Decimal estricto)
            i_cant = QTableWidgetItem(format_stock_qty(canti_dec))
            i_cant.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, i_cant)
            
            # Input Decimal para seleccionar cuánto devolver (soporta enteros y pesables)
            txt_dev = QLineEdit("0")
            txt_dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt_dev.setProperty("precio_str", str(precio_dec))
            txt_dev.setProperty("max_cant_str", str(canti_dec))
            self.table.setCellWidget(row, 4, txt_dev)

            # Selector de protocolo: Revisión/Merma (por defecto) o Reingreso Apto
            cmb_destino = QComboBox()
            cmb_destino.addItem("🔍 Revisión / Merma (No reingresa a venta)", "MERMA")
            cmb_destino.addItem("✅ Reingreso Apto para Venta", "APTO")
            self.table.setCellWidget(row, 5, cmb_destino)
            
        self.btn_procesar.setEnabled(True)
        db.close()

    def procesar_devolucion(self):
        if not self.current_invoice:
            return
            
        # Recolectar devoluciones en Decimal estricto (CERO float)
        devoluciones = []
        total_nc = Decimal('0')
        
        for row in range(self.table.rowCount()):
            cod = self.table.item(row, 0).text()
            txt_dev = self.table.cellWidget(row, 4)
            cmb_destino = self.table.cellWidget(row, 5)
            try:
                cant_dev = Decimal(txt_dev.text().replace(',', '.').strip() or '0')
            except (InvalidOperation, ValueError):
                QMessageBox.warning(self, "Error", f"Cantidad inválida en artículo {cod}.")
                return

            max_cant = Decimal(str(txt_dev.property("max_cant_str") or '0'))
            precio = Decimal(str(txt_dev.property("precio_str") or '0'))
            destino = cmb_destino.currentData() if cmb_destino else "MERMA"
            
            if cant_dev < Decimal('0') or cant_dev > max_cant:
                QMessageBox.warning(
                    self, "Cantidad fuera de rango",
                    f"La cantidad a devolver de {cod} ({format_stock_qty(cant_dev)}) no puede superar lo comprado ({format_stock_qty(max_cant)})."
                )
                return

            if cant_dev > Decimal('0'):
                subtotal_linea = (cant_dev * precio).quantize(Decimal('1'))
                devoluciones.append({
                    'codigo': cod,
                    'cantidad': cant_dev,
                    'precio': precio,
                    'subtotal': subtotal_linea,
                    'destino': destino
                })
                total_nc += subtotal_linea
                
        if not devoluciones:
            QMessageBox.information(self, "Aviso", "No ha seleccionado ninguna cantidad para devolver.")
            return
            
        resp = QMessageBox.question(
            self, "Confirmar", 
            f"Se generará una Nota de Crédito por ₲ {total_nc:,.0f}.\n\n¿Desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.No:
            return
            
        db = SessionLocal()
        fac_origen = db.query(models.Invoice).filter_by(id=self.current_invoice).first()
        
        # 1. Crear Factura tipo NC
        nc = models.Invoice(
            ven_tipo='NC',
            ven_codcli=fac_origen.ven_codcli,
            ven_total=total_nc,
            ven_codmnd='PYG'
        )
        db.add(nc)
        db.flush()
        if not nc.ven_numero:
            nc.ven_numero = nc.id
        
        parent_user = getattr(self.parent(), 'current_user', None)
        uid = parent_user.get('id') if isinstance(parent_user, dict) else 1

        # 2. Detalles, Protocolo de Revisión/Merma vs Stock Apto y Kardex
        for dev in devoluciones:
            item = models.InvoiceItem(
                vit_numero=nc.ven_numero,
                vit_articu=dev['codigo'],
                vit_canti=dev['cantidad'],
                vit_precio=dev['precio']
            )
            db.add(item)
            
            prod = db.query(models.Product).filter_by(art_codigo=dev['codigo']).first()
            if prod:
                componentes = db.query(models.ProductComponent).filter_by(parent_product_id=prod.id).all()
                targets = []
                if componentes:
                    for comp in componentes:
                        ins = db.query(models.Product).filter_by(art_codigo=comp.component_art_codigo).first()
                        if ins:
                            targets.append((ins, (Decimal(str(comp.cantidad)) * dev['cantidad']).quantize(Decimal('0.001')), f" [Insumo de Combo {prod.art_codigo}]"))
                else:
                    targets.append((prod, dev['cantidad'], ""))

                for tgt_prod, tgt_qty, tag_combo in targets:
                    stock_ant = Decimal(str(tgt_prod.art_stkini or '0'))
                    costo_unit = Decimal(str(tgt_prod.art_costo or '0'))
                    if dev['destino'] == 'APTO':
                        stock_post = stock_ant + tgt_qty
                        tgt_prod.art_stkini = stock_post
                        obs_mov = f"Devolución NC #{nc.ven_numero} -> Reingreso a Stock Apto{tag_combo}"
                    else:
                        stock_post = stock_ant
                        perdida_nc = (tgt_qty * costo_unit).quantize(Decimal('1'))
                        db.add(models.StockAdjustment(
                            art_codigo=tgt_prod.art_codigo,
                            tipo='MERMA',
                            cantidad=tgt_qty,
                            motivo=f"Devolución NC #{nc.ven_numero} en Revisión/Cuarentena (Fact. #{fac_origen.ven_numero}){tag_combo}",
                            costo_unitario=costo_unit,
                            monto_perdida=perdida_nc,
                            user_id=uid
                        ))
                        obs_mov = f"Devolución NC #{nc.ven_numero} -> Enviado a Revisión/Merma (No apto para venta){tag_combo}"

                    db.add(models.InventoryMovement(
                        art_codigo=tgt_prod.art_codigo,
                        tipo_movimiento='NOTA_CREDITO',
                        cantidad=tgt_qty if dev['destino'] == 'APTO' else Decimal('0'),
                        stock_anterior=stock_ant,
                        stock_resultante=stock_post,
                        comprobante=f"NC #{nc.ven_numero} (Ref. Fac #{fac_origen.ven_numero})",
                        terminal_id='POS/CAJA',
                        user_id=uid,
                        observacion=obs_mov
                    ))
                
        # 3. Si el cliente tiene cuenta corriente, registrar saldo a favor
        if fac_origen.ven_codcli and fac_origen.ven_codcli != "000001":
            cliente = db.query(models.Client).filter_by(cli_codigo=fac_origen.ven_codcli).first()
            if cliente:
                trx = models.CustomerTransaction(
                    client_id=cliente.id,
                    tipo='PAYMENT',
                    monto=total_nc,
                    referencia=f"Nota de Crédito #{nc.ven_numero}"
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
