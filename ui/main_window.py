import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMenuBar, QMenu, QGridLayout, QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QAction, QColor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro de Venta por Escritorio")
        self.resize(1200, 800)
        
        self.create_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # --- PANEL SUPERIOR ---
        top_panel_layout = QHBoxLayout()
        
        # 1. Grilla Historial de Ventas (Izquierda)
        self.table_historial = QTableWidget(0, 5)
        self.table_historial.setHorizontalHeaderLabels(["Nro.", "Hora", "Cliente", "Total", "FacNº"])
        self.table_historial.setFixedWidth(400)
        self.table_historial.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_historial.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_historial.itemDoubleClicked.connect(self.ver_detalle_factura)
        
        top_panel_layout.addWidget(self.table_historial)
        
        # 2. Botones de Acción (Medio)
        action_buttons_layout = QVBoxLayout()
        
        btn_articulo = QPushButton("Artículos")
        btn_articulo.clicked.connect(self.open_product_management)
        
        btn_cliente = QPushButton("Clientes")
        btn_cliente.clicked.connect(self.open_client_management)
        
        btn_caja = QPushButton("Caja")
        btn_caja.clicked.connect(self.open_caja_dialog)
        
        action_buttons_layout.addWidget(btn_articulo)
        action_buttons_layout.addWidget(btn_cliente)
        action_buttons_layout.addWidget(btn_caja)
        action_buttons_layout.addStretch()
        
        top_panel_layout.addLayout(action_buttons_layout)
        
        # 3. Cabecera de Factura Actual (Derecha)
        cabecera_layout = QGridLayout()
        cabecera_layout.addWidget(QLabel("Fecha:"), 0, 0)
        cabecera_layout.addWidget(QLineEdit("08/09/2026"), 0, 1)
        cabecera_layout.addWidget(QLabel("Fact.:"), 0, 2)
        cabecera_layout.addWidget(QLineEdit("1/1"), 0, 3)
        cabecera_layout.addWidget(QLabel("Nº: 4203"), 0, 4) # Resaltado en naranja en la imagen
        
        cabecera_layout.addWidget(QLabel("Cliente [F8]:"), 2, 0)
        self.txt_cliente = QLineEdit("002276 - DESPENSA SAN CAYETANO")
        cabecera_layout.addWidget(self.txt_cliente, 2, 1, 1, 4)
        
        cabecera_layout.addWidget(QLabel("Vendedor:"), 3, 0)
        self.txt_vendedor = QLineEdit("012 - JULIO VERGARA")
        cabecera_layout.addWidget(self.txt_vendedor, 3, 1, 1, 4)
        
        group_cabecera = QGroupBox("Datos Factura")
        group_cabecera.setLayout(cabecera_layout)
        top_panel_layout.addWidget(group_cabecera, stretch=1)
        
        main_layout.addLayout(top_panel_layout, stretch=1)
        
        # --- BUSCADOR / ESCANER DE CÓDIGO DE BARRAS ---
        scanner_layout = QHBoxLayout()
        scanner_layout.addWidget(QLabel("Código de Barras / Artículo:"))
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Escanee el código de barras y presione ENTER")
        self.txt_codigo.returnPressed.connect(self.buscar_producto)
        scanner_layout.addWidget(self.txt_codigo, stretch=1)
        
        btn_buscar = QPushButton("Buscar [F4]")
        btn_buscar.clicked.connect(self.open_product_search)
        scanner_layout.addWidget(btn_buscar)
        
        main_layout.addLayout(scanner_layout)
        
        # --- PANEL CENTRAL (Detalle de Factura) ---
        self.table_detalle = QTableWidget(0, 9)
        self.table_detalle.setHorizontalHeaderLabels(["Nro", "Codigo", "Descripcion", "Dp", "Cantidad", "Imp", "Iva", "Precio", "Total"])
        self.table_detalle.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Permitir edición solo en la columna de Cantidad
        self.table_detalle.itemChanged.connect(self.on_item_changed)
        
        main_layout.addWidget(self.table_detalle, stretch=2)
        
        # --- PANEL INFERIOR ---
        bottom_panel_layout = QHBoxLayout()
        
        # 1. Panel de Créditos / Atajos (Izquierda)
        creditos_layout = QVBoxLayout()
        lbl_creditos = QLabel("Creditos [F3]")
        lbl_creditos.setStyleSheet("background-color: darkblue; color: white; font-weight: bold;")
        creditos_layout.addWidget(lbl_creditos)
        
        self.table_creditos = QTableWidget(0, 4)
        self.table_creditos.setHorizontalHeaderLabels(["Cuenta", "Cuota", "Monto", "Vence"])
        self.table_creditos.setFixedWidth(300)
        creditos_layout.addWidget(self.table_creditos)
        bottom_panel_layout.addLayout(creditos_layout)
        
        # 2. Botones de Cierre (Centro)
        cierre_layout = QVBoxLayout()
        cierre_layout.addStretch()
        btn_remision = QPushButton("Remisión [F7]")
        btn_remision.clicked.connect(self.procesar_remision)
        
        btn_factura = QPushButton("Cobrar/Factura [F11]")
        btn_factura.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px;")
        btn_factura.clicked.connect(self.procesar_factura)
        
        cierre_layout.addWidget(btn_remision)
        cierre_layout.addWidget(btn_factura)
        cierre_layout.addStretch()
        bottom_panel_layout.addLayout(cierre_layout)
        
        # 3. Totales (Derecha - Fondo Púrpura)
        totals_widget = QWidget()
        totals_layout = QGridLayout(totals_widget)
        totals_widget.setStyleSheet("background-color: #800080; color: white; border: 1px solid black;")
        
        font_totals = QFont("Arial", 16, QFont.Weight.Bold)
        
        # Monedas
        self.lbl_usd = QLabel("8.46") # USD
        self.lbl_brl = QLabel("42.30") # BRL
        self.lbl_ars = QLabel("68,750.0") # ARS
        self.lbl_pyg = QLabel("55,000") # PYG
        
        flags = ["USD", "BRL", "ARS", "PYG"]
        labels = [self.lbl_usd, self.lbl_brl, self.lbl_ars, self.lbl_pyg]
        
        for i, (flag, lbl) in enumerate(zip(flags, labels)):
            lbl.setFont(font_totals)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            totals_layout.addWidget(QLabel(flag), i, 0)
            totals_layout.addWidget(lbl, i, 1)
            
        totals_layout.addWidget(QLabel("Total Gral.:"), 3, 2)
        lbl_total_gral = QLabel("55,000")
        lbl_total_gral.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        totals_layout.addWidget(lbl_total_gral, 3, 3)
        
        bottom_panel_layout.addWidget(totals_widget, stretch=1)
        
        main_layout.addLayout(bottom_panel_layout, stretch=1)
        
        self.cargar_historial_ventas()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F8:
            self.open_client_search()
        elif event.key() == Qt.Key.Key_F4:
            self.open_product_search()
        elif event.key() == Qt.Key.Key_F11:
            self.procesar_factura()
        elif event.key() == Qt.Key.Key_F7:
            self.procesar_remision()
        elif event.key() == Qt.Key.Key_Delete:
            # Borrar fila seleccionada
            current_row = self.table_detalle.currentRow()
            if current_row >= 0:
                self.table_detalle.removeRow(current_row)
                self.calcular_totales()
        else:
            super().keyPressEvent(event)
            
    def on_item_changed(self, item):
        # Evitar recursividad si estamos modificando el Total desde código
        if item.column() == 4: # Columna Cantidad
            try:
                row = item.row()
                cantidad = float(item.text())
                precio_item = self.table_detalle.item(row, 7)
                if precio_item:
                    precio = float(precio_item.text().replace(',', ''))
                    nuevo_total = cantidad * precio
                    
                    # Actualizar celda de Total temporalmente desconectando la señal
                    self.table_detalle.itemChanged.disconnect(self.on_item_changed)
                    self.table_detalle.setItem(row, 8, QTableWidgetItem(f"{nuevo_total:,.0f}"))
                    self.table_detalle.itemChanged.connect(self.on_item_changed)
                    
                    self.calcular_totales()
            except ValueError:
                pass # Si escriben letras, ignorar
                
    def procesar_factura(self):
        if self.table_detalle.rowCount() == 0:
            return
            
        totals = {
            'PYG': float(self.lbl_pyg.text().replace(',', '')),
            'USD': float(self.lbl_usd.text().replace(',', '')),
            'BRL': float(self.lbl_brl.text().replace(',', '')),
            'ARS': float(self.lbl_ars.text().replace(',', ''))
        }
        
        from ui.payment_dialog import PaymentDialog
        dialog = PaymentDialog(totals, self)
        if dialog.exec():
            if dialog.payment_successful:
                self.guardar_venta_db(dialog.moneda_pago, dialog.monto_pagado)
                
    def guardar_venta_db(self, moneda, monto_pagado):
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        try:
            # 1. Crear Factura
            cliente_txt = self.txt_cliente.text()
            cod_cli = cliente_txt.split(" - ")[0] if " - " in cliente_txt else "000001"
            
            nueva_venta = models.Invoice(
                ven_codcli=cod_cli,
                ven_total=float(self.lbl_pyg.text().replace(',', '')),
                ven_codmnd=moneda
            )
            db.add(nueva_venta)
            db.flush() # Para obtener el ID generado
            
            # 2. Crear Detalle de Factura y Descontar Stock
            for row in range(self.table_detalle.rowCount()):
                cod_art = self.table_detalle.item(row, 1).text()
                cantidad = float(self.table_detalle.item(row, 4).text())
                precio = float(self.table_detalle.item(row, 7).text().replace(',', ''))
                
                item = models.InvoiceItem(
                    vit_numero=nueva_venta.id,
                    vit_articu=cod_art,
                    vit_canti=cantidad,
                    vit_precio=precio
                )
                db.add(item)
                
                # Descontar stock
                producto = db.query(models.Product).filter_by(art_codigo=cod_art).first()
                if producto:
                    producto.art_stkini -= int(cantidad)
            
            # 3. Registrar Cobranza
            pago = models.Payment(
                cob_monto=monto_pagado,
                cob_vennro=nueva_venta.id,
                cob_mndori=moneda
            )
            db.add(pago)
            
            db.commit()
            
            # Limpiar pantalla para próxima venta
            self.table_detalle.setRowCount(0)
            self.txt_cliente.setText("000001 - CONSUMIDOR FINAL")
            self.calcular_totales()
            self.cargar_historial_ventas()
            
        except Exception as e:
            db.rollback()
            print("Error al guardar:", str(e))
        finally:
            db.close()
            
    def cargar_historial_ventas(self):
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        # Últimas 50 facturas
        facturas = db.query(models.Invoice).order_by(models.Invoice.id.desc()).limit(50).all()
        
        self.table_historial.setRowCount(0)
        for row, fac in enumerate(facturas):
            self.table_historial.insertRow(row)
            self.table_historial.setItem(row, 0, QTableWidgetItem(str(fac.id)))
            self.table_historial.setItem(row, 1, QTableWidgetItem(fac.ven_fecha.strftime("%H:%M")))
            
            cliente_nombre = fac.client.cli_nombre if fac.client else "CONSUMIDOR FINAL"
            self.table_historial.setItem(row, 2, QTableWidgetItem(cliente_nombre))
            
            self.table_historial.setItem(row, 3, QTableWidgetItem(f"{fac.ven_total:,.0f}"))
            self.table_historial.setItem(row, 4, QTableWidgetItem(f"{fac.id}/1"))
            
            self.table_historial.item(row, 0).setData(Qt.ItemDataRole.UserRole, fac.id)
            
        db.close()
        
    def ver_detalle_factura(self, item):
        row = item.row()
        invoice_id = self.table_historial.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        from ui.invoice_detail_dialog import InvoiceDetailDialog
        dialog = InvoiceDetailDialog(invoice_id, self)
        dialog.exec()
            
    def open_client_search(self):
        from ui.client_search_dialog import ClientSearchDialog
        dialog = ClientSearchDialog(self)
        if dialog.exec():
            client = dialog.selected_client
            if client:
                self.txt_cliente.setText(f"{client.cli_codigo} - {client.cli_nombre}")
                
    def open_product_search(self):
        from ui.product_search_dialog import ProductSearchDialog
        dialog = ProductSearchDialog(self)
        if dialog.exec():
            product = dialog.selected_product
            if product:
                self.add_product_to_grid(product)
            
    def open_product_management(self):
        from ui.product_management import ProductManagementDialog
        dialog = ProductManagementDialog(self)
        dialog.exec()
        
    def open_client_management(self):
        from ui.client_management import ClientManagementDialog
        dialog = ClientManagementDialog(self)
        dialog.exec()
        
    def open_caja_dialog(self):
        from ui.caja_dialog import CajaDialog
        dialog = CajaDialog(self)
        dialog.exec()
                
    def buscar_producto(self):
        codigo = self.txt_codigo.text().strip()
        if not codigo:
            return
            
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        prod = db.query(models.Product).filter(
            models.Product.is_active == True,
            (models.Product.art_codigo == codigo) | (models.Product.art_cbarra == codigo)
        ).first()
        
        factor_conversion = 1.0
        
        if not prod:
            barcode = db.query(models.ProductBarcode).filter_by(barcode=codigo).first()
            if barcode and barcode.product.is_active:
                prod = barcode.product
                factor_conversion = barcode.factor_conversion
                
        db.close()
        
        if prod:
            self.add_product_to_grid(prod, cantidad=1.0 * factor_conversion)
            self.txt_codigo.clear()
            self.txt_codigo.setFocus()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Encontrado", "Artículo no encontrado o inactivo.")
            self.txt_codigo.selectAll()
            
    def add_product_to_grid(self, product, cantidad=1.0):
        # Verificar si ya existe en la grilla para sumar cantidad
        for row in range(self.table_detalle.rowCount()):
            if self.table_detalle.item(row, 1).text() == product.art_codigo:
                current_qty = float(self.table_detalle.item(row, 4).text())
                new_qty = current_qty + cantidad
                self.table_detalle.item(row, 4).setText(str(new_qty))
                
                precio = product.art_preven
                subtotal = new_qty * precio
                self.table_detalle.item(row, 8).setText(f"{subtotal:,.0f}")
                self.calcular_totales()
                return
                
        # Si no existe, agregar nueva fila
        row = self.table_detalle.rowCount()
        self.table_detalle.insertRow(row)
        
        precio = product.art_preven
        total = precio * cantidad
        
        self.table_detalle.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table_detalle.setItem(row, 1, QTableWidgetItem(product.art_codigo))
        
        descri = product.art_descri
        if product.is_fractional:
            descri += " (Fraccionable)"
            
        self.table_detalle.setItem(row, 2, QTableWidgetItem(descri))
        self.table_detalle.setItem(row, 3, QTableWidgetItem("DC")) 
        self.table_detalle.setItem(row, 4, QTableWidgetItem(str(cantidad)))
        self.table_detalle.setItem(row, 5, QTableWidgetItem("I")) 
        self.table_detalle.setItem(row, 6, QTableWidgetItem(str(product.art_impu)))
        self.table_detalle.setItem(row, 7, QTableWidgetItem(f"{precio:,.0f}"))
        self.table_detalle.setItem(row, 8, QTableWidgetItem(f"{total:,.0f}"))
        
        self.calcular_totales()
        
    def calcular_totales(self):
        total_pyg = 0.0
        for row in range(self.table_detalle.rowCount()):
            item_total = self.table_detalle.item(row, 8)
            if item_total:
                total_pyg += float(item_total.text().replace(',', ''))
                
        # Traer cotizaciones
        from database import SessionLocal
        import models
        db = SessionLocal()
        rates = {r.currency: r.rate_to_pyg for r in db.query(models.ExchangeRate).all()}
        db.close()
        
        rate_usd = rates.get("USD", 7500.0)
        rate_brl = rates.get("BRL", 1500.0)
        rate_ars = rates.get("ARS", 10.0)
        
        total_usd = total_pyg / rate_usd if rate_usd > 0 else 0
        total_brl = total_pyg / rate_brl if rate_brl > 0 else 0
        total_ars = total_pyg / rate_ars if rate_ars > 0 else 0
        
        self.lbl_pyg.setText(f"{total_pyg:,.0f}")
        self.lbl_usd.setText(f"{total_usd:,.2f}")
        self.lbl_brl.setText(f"{total_brl:,.2f}")
        self.lbl_ars.setText(f"{total_ars:,.2f}")
        
    def procesar_remision(self):
        if self.table_detalle.rowCount() == 0:
            return
            
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, 'Confirmar Remisión', '¿Generar Nota de Remisión y descontar stock?\n\n(Esta acción no genera un movimiento de caja)', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        try:
            cliente_txt = self.txt_cliente.text()
            cod_cli = cliente_txt.split(" - ")[0] if " - " in cliente_txt else "000001"
            
            nueva_remision = models.Remission(
                codcli=cod_cli,
                total_pyg=float(self.lbl_pyg.text().replace(',', ''))
            )
            db.add(nueva_remision)
            db.flush()
            
            for row in range(self.table_detalle.rowCount()):
                cod_art = self.table_detalle.item(row, 1).text()
                cantidad = float(self.table_detalle.item(row, 4).text())
                precio = float(self.table_detalle.item(row, 7).text().replace(',', ''))
                
                item = models.RemissionItem(
                    remission_id=nueva_remision.id,
                    articu=cod_art,
                    canti=cantidad,
                    precio=precio
                )
                db.add(item)
                
                # Descontar stock
                producto = db.query(models.Product).filter_by(art_codigo=cod_art).first()
                if producto:
                    producto.art_stkini -= int(cantidad)
            
            db.commit()
            
            self.table_detalle.setRowCount(0)
            self.txt_cliente.setText("000001 - CONSUMIDOR FINAL")
            self.calcular_totales()
            
            QMessageBox.information(self, "Éxito", f"Nota de Remisión #{nueva_remision.id} generada con éxito.")
            
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Error al generar remisión: {str(e)}")
        finally:
            db.close()
            
    def open_cotizacion_dialog(self):
        from ui.cotizacion_dialog import CotizacionDialog
        dialog = CotizacionDialog(self)
        dialog.exec()
        
    def open_company_settings(self):
        from ui.company_settings_dialog import CompanySettingsDialog
        dialog = CompanySettingsDialog(self)
        dialog.exec()
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        menu_util = menubar.addMenu("Utilidades")
        
        action_cotiz = QAction("5. Cotización de Moneda", self)
        action_cotiz.triggered.connect(self.open_cotizacion_dialog)
        menu_util.addAction(action_cotiz)
        
        action_conf = QAction("Configuración de Empresa", self)
        action_conf.triggered.connect(self.open_company_settings)
        menu_util.addAction(action_conf)
