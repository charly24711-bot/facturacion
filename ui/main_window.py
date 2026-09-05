import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMenuBar, QMenu, QGridLayout, QLineEdit, QGroupBox, QCheckBox, QFrame, QCompleter, QTableView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QAction, QColor, QPixmap

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills/ean13_parser/scripts')))
import ean13_parser
from ui.ventas_table_model import VentasTableModel
from ui.sync_worker import SyncWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro de Venta por Escritorio")
        self.resize(1200, 800)
        
        # --- ARQUEO Y SESIÓN ---
        self.session_id = None
        self.init_cash_session()

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
        
        btn_reporte_z = QPushButton("Cerrar Turno (Reporte Z)")
        btn_reporte_z.setStyleSheet("background-color: darkred; color: white;")
        btn_reporte_z.clicked.connect(self.open_reporte_z)
        
        action_buttons_layout.addWidget(btn_articulo)
        action_buttons_layout.addWidget(btn_cliente)
        action_buttons_layout.addWidget(btn_caja)
        action_buttons_layout.addWidget(btn_reporte_z)
        action_buttons_layout.addStretch()
        
        top_panel_layout.addLayout(action_buttons_layout)
        
        # 3. Cabecera de Factura Actual (Derecha)
        cabecera_layout = QGridLayout()
        
        # Indicador de Red
        self.lbl_network_status = QLabel("🔴 Offline")
        self.lbl_network_status.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        self.lbl_network_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        cabecera_layout.addWidget(self.lbl_network_status, 0, 5, 1, 2)
        
        cabecera_layout.addWidget(QLabel("Fecha:"), 0, 0)
        from PyQt6.QtCore import QDate
        date_edit = QLineEdit(QDate.currentDate().toString("dd-MM-yyyy"))
        date_edit.setReadOnly(True)
        cabecera_layout.addWidget(date_edit, 0, 1)
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
        self.txt_codigo.textChanged.connect(lambda t, le=self.txt_codigo: self.auto_format_thousands(t, le))
        self.txt_codigo.returnPressed.connect(self.buscar_producto)
        scanner_layout.addWidget(self.txt_codigo, stretch=1)
        
        btn_buscar = QPushButton("Buscar [F4]")
        btn_buscar.clicked.connect(self.open_product_search)
        scanner_layout.addWidget(btn_buscar)
        
        self.chk_visor = QCheckBox("Ocultar Visor de Producto")
        self.chk_visor.setChecked(False)
        self.chk_visor.toggled.connect(self.toggle_visor_producto)
        scanner_layout.addWidget(self.chk_visor)
        
        main_layout.addLayout(scanner_layout)
        
        # --- PANEL CENTRAL (Detalle de Factura) ---
        central_panel_layout = QHBoxLayout()
        
        self.table_detalle = QTableView()
        self.ventas_model = VentasTableModel()
        self.ventas_model.qty_changed_for_tier.connect(self.on_qty_changed_tier)
        self.table_detalle.setModel(self.ventas_model)
        self.table_detalle.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_detalle.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        
        self.ventas_model.dataChanged.connect(self.calcular_totales)
        self.table_detalle.selectionModel().selectionChanged.connect(self.update_product_view)
        self.table_detalle.itemDelegate().closeEditor.connect(self.focus_codigo)
        
        central_panel_layout.addWidget(self.table_detalle, stretch=3)
        
        # --- VISOR DE PRODUCTO ---
        self.product_view_panel = QGroupBox("Detalle de Producto")
        self.product_view_panel.setVisible(False)
        self.product_view_panel.setFixedWidth(250)
        
        from PyQt6.QtWidgets import QSizePolicy
        sp = self.product_view_panel.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.product_view_panel.setSizePolicy(sp)
        
        visor_layout = QVBoxLayout()
        
        # Imagen placeholder
        self.lbl_visor_img = QLabel("📷\nSin Imagen")
        self.lbl_visor_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_visor_img.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; color: #888;")
        self.lbl_visor_img.setFixedHeight(180)
        self.lbl_visor_img.setFont(QFont("Segoe UI Emoji", 24))
        visor_layout.addWidget(self.lbl_visor_img)
        
        # Textos
        self.lbl_visor_descri = QLabel("Seleccione un producto")
        self.lbl_visor_descri.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.lbl_visor_descri.setWordWrap(True)
        visor_layout.addWidget(self.lbl_visor_descri)
        
        self.lbl_visor_codigo = QLabel("Código: -")
        visor_layout.addWidget(self.lbl_visor_codigo)
        
        self.lbl_visor_precio = QLabel("Precio: -")
        self.lbl_visor_precio.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.lbl_visor_precio.setStyleSheet("color: #2e7d32;")
        visor_layout.addWidget(self.lbl_visor_precio)
        
        self.lbl_visor_stock = QLabel("Stock Disponible: -")
        self.lbl_visor_stock.setFont(QFont("Arial", 11))
        visor_layout.addWidget(self.lbl_visor_stock)
        
        visor_layout.addStretch()
        self.product_view_panel.setLayout(visor_layout)
        
        central_panel_layout.addWidget(self.product_view_panel)
        
        main_layout.addLayout(central_panel_layout, stretch=2)
        
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
        self.setup_autocomplete()
        
        # Iniciar Sincronización
        self.sync_worker = SyncWorker()
        self.sync_worker.status_changed.connect(self.update_network_status)
        self.sync_worker.start()

    def update_network_status(self, is_online):
        if is_online:
            self.lbl_network_status.setText("🟢 Online (Sincronizando)")
            self.lbl_network_status.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        else:
            self.lbl_network_status.setText("🔴 Modo Local (Offline)")
            self.lbl_network_status.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            
    def closeEvent(self, event):
        if hasattr(self, 'sync_worker'):
            self.sync_worker.stop()
        super().closeEvent(event)
        
    def setup_autocomplete(self):
        from database import SessionLocal
        import models
        from PyQt6.QtCore import Qt, QStringListModel
        
        db = SessionLocal()
        productos = db.query(models.Product).filter(models.Product.is_active == True).all()
        
        sugerencias = []
        for p in productos:
            sugerencias.append(f"{p.art_codigo} - {p.art_descri}")
            
        db.close()
        
        model = QStringListModel(sugerencias)
        completer = QCompleter()
        completer.setModel(model)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        
        self.txt_codigo.setCompleter(completer)
        
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
            indexes = self.table_detalle.selectionModel().selectedRows()
            if indexes:
                self.ventas_model.remove_item(indexes[0].row())
                self.calcular_totales()
        else:
            super().keyPressEvent(event)
            

                
    def procesar_factura(self):
        if self.ventas_model.rowCount() == 0:
            return
            
        totals = {
            'PYG': _safe_dec(self.lbl_pyg.text().replace(',', '')),
            'USD': _safe_dec(self.lbl_usd.text().replace(',', '')),
            'BRL': _safe_dec(self.lbl_brl.text().replace(',', '')),
            'ARS': _safe_dec(self.lbl_ars.text().replace(',', ''))
        }
        
        from database import SessionLocal
        import models
        db = SessionLocal()
        cliente_txt = self.txt_cliente.text()
        cod_cli = cliente_txt.split(" - ")[0] if " - " in cliente_txt else None
        cliente = db.query(models.Client).filter_by(cli_codigo=cod_cli).first() if cod_cli else None
        db.close()
        
        from ui.payment_dialog import PaymentDialog
        dialog = PaymentDialog(totals, cliente, self)
        if dialog.exec():
            if dialog.payment_successful:
                self.guardar_venta_db(dialog.payments_list)
                
    def guardar_venta_db(self, payments_list):
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        try:
            # 1. Crear Factura
            cliente_txt = self.txt_cliente.text()
            cod_cli = cliente_txt.split(" - ")[0] if " - " in cliente_txt else "000001"
            
            nueva_venta = models.Invoice(
                ven_codcli=cod_cli,
                ven_total=_safe_dec(self.lbl_pyg.text().replace(',', '')),
                ven_codmnd='PYG'
            )
            db.add(nueva_venta)
            db.flush() # Para obtener el ID generado
            
            # 2. Crear Detalle de Factura y Descontar Stock
            for item_data in self.ventas_model.items:
                cod_art = item_data['codigo']
                cantidad = item_data['cantidad']
                precio = item_data['precio']
                
                item = models.InvoiceItem(
                    vit_numero=nueva_venta.id,
                    vit_articu=cod_art,
                    vit_canti=cantidad,
                    vit_precio=precio
                )
                db.add(item)
                
                # Descontar stock general
                producto = db.query(models.Product).filter_by(art_codigo=cod_art).first()
                if producto:
                    producto.art_stkini = _safe_dec(producto.art_stkini or 0) - _safe_dec(cantidad)
                    
                    # FIFO Descontar stock de lotes
                    qty_to_deduct = _safe_dec(cantidad)
                    batches = (db.query(models.ProductBatch)
                                 .filter(models.ProductBatch.product_id == producto.id, 
                                         models.ProductBatch.stock_actual > 0)
                                 .order_by(models.ProductBatch.fecha_vencimiento.asc())
                                 .all())
                    
                    from decimal import Decimal
                    for b in batches:
                        if qty_to_deduct <= 0:
                            break
                        available = _safe_dec(b.stock_actual)
                        if available >= qty_to_deduct:
                            b.stock_actual = Decimal(str(available - qty_to_deduct))
                            qty_to_deduct = 0
                        else:
                            b.stock_actual = Decimal("0")
                            qty_to_deduct = _safe_dec(qty_to_deduct) - _safe_dec(available)
            
            # 3. Registrar Cobranza
            for p in payments_list:
                pago = models.Payment(
                    cob_monto=p['monto_origen'],
                    cob_monto_pyg=p['monto_pyg'],
                    cob_vennro=nueva_venta.id,
                    cob_mndori=p['moneda'],
                    cob_metodo=p['metodo'],
                    session_id=self.session_id
                )
                db.add(pago)
                
                if p['metodo'] == 'Cuenta Corriente':
                    # Find client again using the session
                    cli_cc = db.query(models.Client).filter_by(cli_codigo=cod_cli).first()
                    if cli_cc:
                        trx = models.CustomerTransaction(
                            client_id=cli_cc.id,
                            tipo='CHARGE',
                            monto=p['monto_pyg'],
                            referencia=f"Factura #{nueva_venta.id or 'Nueva'}"
                        )
                        db.add(trx)
            
            db.commit()
            
            # Limpiar pantalla para próxima venta
            self.ventas_model.clear()
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
        
    def open_reporte_z(self):
        from ui.arqueo_dialog import ArqueoDialog
        dialog = ArqueoDialog(self.session_id, self)
        if dialog.exec():
            # Session was closed, init a new one
            self.init_cash_session()

    def open_caja_dialog(self):
        from ui.caja_dialog import CajaDialog
        dialog = CajaDialog(self)
        dialog.exec()
                
    def buscar_producto(self):
        texto_busqueda = self.txt_codigo.text().strip()
        if not texto_busqueda:
            return
            
        if " - " in texto_busqueda:
            codigo = texto_busqueda.split(" - ")[0].strip()
        else:
            codigo = texto_busqueda
            
        # SKILL: EAN-13 PARSER
        parsed = ean13_parser.parse_scale_barcode(codigo, modo="peso")
        cantidad_balanza = 1.0
        if parsed.get("es_balanza"):
            codigo = parsed["plu"].zfill(6)
            if parsed["tipo"] == "BALANZA_PESO":
                cantidad_balanza = _safe_dec(parsed["peso_kg"])
            
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
            final_qty = cantidad_balanza if parsed.get("es_balanza") else 1.0 * factor_conversion
            self.txt_codigo.clear()
            self.add_product_to_grid(prod, cantidad=final_qty)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Encontrado", "Artículo no encontrado o inactivo.")
            self.txt_codigo.selectAll()
            
    def get_precio_vigente(self, art_codigo, cantidad=1):
        """Devuelve (precio, label). Prioridad: Promo > Tier > Lista de Precio de Cliente > Normal."""
        from database import SessionLocal
        import models
        import datetime as dt
        now = dt.datetime.now()
        db = SessionLocal()
        
        # 1. Promo temporal (mayor prioridad)
        promo = db.query(models.ProductPromo).filter(
            models.ProductPromo.pro_articu == art_codigo,
            models.ProductPromo.is_active == True,
            models.ProductPromo.pro_desde <= now,
            models.ProductPromo.pro_hasta >= now,
        ).order_by(models.ProductPromo.pro_hasta.asc()).first()
        
        if promo:
            db.close()
            return _safe_dec(promo.pro_precio), f"\U0001f3f7\ufe0f {promo.pro_descri or 'PROMO'}"
        
        # 2. Precio por volumen (tier)
        tier = (db.query(models.PriceTier)
                  .filter(
                      models.PriceTier.pt_articu == art_codigo,
                      models.PriceTier.is_active == True,
                      models.PriceTier.pt_qty_min <= cantidad,
                  )
                  .order_by(models.PriceTier.pt_qty_min.desc())
                  .first())
        
        if tier:
            db.close()
            return _safe_dec(tier.pt_precio), f"\U0001f4ca {tier.pt_descri or f'{int(cantidad)}+ u'}"
            
        # 3. Lista de precio del cliente
        cliente_txt = self.txt_cliente.text()
        cod_cli = cliente_txt.split(" - ")[0] if " - " in cliente_txt else None
        if cod_cli:
            cliente = db.query(models.Client).filter_by(cli_codigo=cod_cli).first()
            if cliente and cliente.price_list_id:
                list_item = db.query(models.PriceListItem).filter_by(
                    pli_list_id=cliente.price_list_id, 
                    pli_articu=art_codigo
                ).first()
                if list_item:
                    nombre_lista = cliente.price_list.pl_nombre if cliente.price_list else "Lista Esp."
                    db.close()
                    return _safe_dec(list_item.pli_precio), f"\U0001f4cb {nombre_lista}"
        
        # 4. Precio normal
        prod = db.query(models.Product).filter_by(art_codigo=art_codigo).first()
        db.close()
        if prod:
            return _safe_dec(prod.art_preven or 0), None
        return 0.0, None

    def add_product_to_grid(self, product, cantidad=1.0):
        # Check current qty already in cart to determine tier correctly
        qty_en_carrito = 0
        for item in self.ventas_model.items:
            if item['codigo'] == product.art_codigo:
                qty_en_carrito = item['cantidad']
                break
        qty_total = qty_en_carrito + _safe_dec(cantidad)
        precio, label = self.get_precio_vigente(product.art_codigo, qty_total)
        row_idx = self.ventas_model.add_item(product, cantidad, precio_override=precio, promo_label=label)
        self.calcular_totales()
        
        if row_idx is not None:
            self.table_detalle.selectRow(row_idx)
            # Focus on Cantidad column (4)
            index = self.ventas_model.index(row_idx, 4)
            self.table_detalle.setCurrentIndex(index)
            self.table_detalle.edit(index)
        

    def focus_codigo(self, editor=None, hint=None):
        from PyQt6.QtCore import QTimer
        # Usar un timer para asegurar que se procese el enter antes de mover el foco
        QTimer.singleShot(0, lambda: self.txt_codigo.setFocus())
        QTimer.singleShot(0, lambda: self.txt_codigo.selectAll())

    def calcular_totales(self, topLeft=None, bottomRight=None, roles=None):
        total_pyg = self.ventas_model.get_total_pyg()
                
        # Traer cotizaciones
        from database import SessionLocal
        import models
        db = SessionLocal()
        rates = {r.currency_code: _safe_dec(r.buy_rate) for r in db.query(models.CurrencyRate).filter_by(is_active=True).all()}
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
        if self.ventas_model.rowCount() == 0:
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
                total_pyg=_safe_dec(self.lbl_pyg.text().replace(',', ''))
            )
            db.add(nueva_remision)
            db.flush()
            
            for item_data in self.ventas_model.items:
                cod_art = item_data['codigo']
                cantidad = item_data['cantidad']
                precio = item_data['precio']
                
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
                    producto.art_stkini = _safe_dec(producto.art_stkini) - _safe_dec(int(cantidad))
            
            db.commit()
            
            self.ventas_model.clear()
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
        
        menu_util.addSeparator()
        
        action_compras = QAction("🛒 Ingreso de Compras (Stock)", self)
        action_compras.triggered.connect(self.open_purchase_dialog)
        menu_util.addAction(action_compras)

        action_promos = QAction("🏷️ Gestión de Promociones", self)
        action_promos.triggered.connect(self.open_promos_dialog)
        menu_util.addAction(action_promos)

        action_tiers = QAction("💰 Precios por Volumen", self)
        action_tiers.triggered.connect(self.open_price_tiers_dialog)
        menu_util.addAction(action_tiers)

    def open_purchase_dialog(self):
        from ui.purchase_dialog import PurchaseDialog
        dialog = PurchaseDialog(self)
        dialog.exec()

    def open_promos_dialog(self):
        from ui.promos_dialog import PromosDialog
        dialog = PromosDialog(self)
        dialog.exec()

    def open_price_tiers_dialog(self):
        from ui.price_tiers_dialog import PriceTiersDialog
        dialog = PriceTiersDialog(self)
        dialog.exec()
        
    def open_price_lists_dialog(self):
        from ui.price_lists_dialog import PriceListsDialog
        dialog = PriceListsDialog(self)
        dialog.exec()
        
    def open_customer_accounts_dialog(self):
        from ui.customer_accounts_dialog import CustomerAccountsDialog
        dialog = CustomerAccountsDialog(self)
        dialog.exec()
        
    def open_returns_dialog(self):
        from ui.returns_dialog import ReturnsDialog
        dialog = ReturnsDialog(self)
        dialog.exec()
        
    def open_batches_dialog(self):
        from ui.batches_dialog import BatchesDialog
        dialog = BatchesDialog(self)
        dialog.exec()

    def on_qty_changed_tier(self, row, nueva_qty):
        """Re-checks price tiers when quantity changes directly in the grid."""
        if row < 0 or row >= len(self.ventas_model.items):
            return
        item = self.ventas_model.items[row]
        precio, label = self.get_precio_vigente(item['codigo'], nueva_qty)
        # Update price and description in the model
        item['precio'] = precio
        # Update label: strip old tier/promo labels and apply new one
        desc_base = item['descripcion']
        for badge in ["📊 ", "🏷️ "]:
            if badge in desc_base:
                desc_base = desc_base.split("  " + badge)[0].strip()
        if label:
            item['descripcion'] = f"{desc_base}  {label}"
        else:
            item['descripcion'] = desc_base
        self.ventas_model._recalcular_fila(row)
        self.ventas_model.dataChanged.emit(
            self.ventas_model.index(row, 0),
            self.ventas_model.index(row, self.ventas_model.columnCount() - 1)
        )
        self.calcular_totales()

    def toggle_visor_producto(self, checked):
        self.product_view_panel.setVisible(not checked)
        if not checked:
            self.update_product_view()
            
    def init_cash_session(self):
        from database import SessionLocal
        import models
        db = SessionLocal()
        session = db.query(models.CashSession).filter_by(status='OPEN').first()
        if not session:
            session = models.CashSession(status='OPEN')
            db.add(session)
            db.commit()
            db.refresh(session)
        self.session_id = session.id
        db.close()

    def update_product_view(self):
        if self.chk_visor.isChecked():
            return
            
        indexes = self.table_detalle.selectionModel().selectedRows()
        if not indexes:
            self.lbl_visor_descri.setText("Seleccione un producto")
            self.lbl_visor_codigo.setText("Código: -")
            self.lbl_visor_precio.setText("Precio: -")
            self.lbl_visor_stock.setText("Stock Disponible: -")
            return
            
        row = indexes[0].row()
        cod_art = self.ventas_model.items[row]['codigo']
        
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        producto = db.query(models.Product).filter_by(art_codigo=cod_art).first()
        db.close()
        
        if producto:
            self.lbl_visor_descri.setText(producto.art_descri)
            self.lbl_visor_codigo.setText(f"Código: {producto.art_codigo}")
            self.lbl_visor_precio.setText(f"Precio: ₲ {producto.art_preven:,.0f}")
            self.lbl_visor_stock.setText(f"Stock Disponible: {producto.art_stkini}")
            
            import os
            if producto.image_path and os.path.exists(producto.image_path):
                pixmap = QPixmap(producto.image_path)
                self.lbl_visor_img.setPixmap(pixmap.scaled(self.lbl_visor_img.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                self.lbl_visor_img.clear()
                self.lbl_visor_img.setText("📷\nSin Imagen")
        else:
            self.lbl_visor_descri.setText("Producto no encontrado")
            self.lbl_visor_img.clear()
            self.lbl_visor_img.setText("📷\nSin Imagen")