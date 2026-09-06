import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMenuBar, QMenu, QGridLayout, QLineEdit, QGroupBox, QCheckBox, QFrame, QCompleter, QTableView,
                             QComboBox, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QAction, QColor, QPixmap

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills/ean13_parser/scripts')))
import ean13_parser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills/tax_calculator/scripts')))
import tax_calculator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))
from validator.validator import POSGuardrail
from decimal import Decimal
from ui.ventas_table_model import VentasTableModel
from ui.sync_worker import SyncWorker

def _safe_dec(v):
    from decimal import Decimal
    if v is None: return Decimal('0')
    if isinstance(v, Decimal): return v
    return Decimal(str(v).replace(',', '.'))

class MainWindow(QMainWindow):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user or {
            "id": 1,
            "username": "admin",
            "full_name": "Administrador General",
            "role": "ADMIN"
        }
        self.setWindowTitle("Supermercado Central - Punto de Venta (POS)")
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

        # Botón a Panel Administrativo (Visible para Admin/Gerente)
        if self.current_user.get('role') in ('ADMIN', 'GERENTE'):
            btn_admin = QPushButton("🏢 Panel Admin")
            btn_admin.setStyleSheet("background-color: #1a237e; color: white; font-weight: bold;")
            btn_admin.clicked.connect(self.open_admin_panel)
            action_buttons_layout.addWidget(btn_admin)

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
        vendedor_text = f"{self.current_user['id']:03d} - {self.current_user['full_name']}"
        self.txt_vendedor = QLineEdit(vendedor_text)
        cabecera_layout.addWidget(self.txt_vendedor, 3, 1, 1, 4)
        
        cabecera_layout.addWidget(QLabel("Canal Precio:"), 4, 0)
        self.cmb_canal_precio = QComboBox()
        self.cmb_canal_precio.setStyleSheet("font-weight: bold; padding: 2px 4px; background-color: #f1f5f9; color: #0f172a;")
        self.cargar_canales_precios()
        self.cmb_canal_precio.currentIndexChanged.connect(self.on_canal_precio_changed)
        cabecera_layout.addWidget(self.cmb_canal_precio, 4, 1, 1, 4)
        
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
        self.ventas_model.dataChanged.connect(self.calcular_totales)
        self.table_detalle.selectionModel().selectionChanged.connect(lambda *args: self.update_product_view())
        self.table_detalle.clicked.connect(lambda *args: self.update_product_view())
        self.table_detalle.itemDelegate().closeEditor.connect(self.focus_codigo)
        
        central_panel_layout.addWidget(self.table_detalle, stretch=3)
        
        # --- VISOR DE PRODUCTO ---
        self.product_view_panel = QGroupBox("Detalle de Producto")
        self.product_view_panel.setVisible(True)
        self.product_view_panel.setFixedWidth(260)
        
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
        
        # 1. Panel de Liquidación de IVA (Ley 6380/19) y Atajos de Caja
        panel_fiscal = QGroupBox("📋 Liquidación I.V.A. (Ley 6380/19)")
        panel_fiscal.setFixedWidth(340)
        panel_fiscal.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 2px solid #1a237e;
                border-radius: 6px;
                margin-top: 6px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1a237e;
            }
            QLabel {
                font-size: 11px;
            }
        """)
        
        fiscal_layout = QVBoxLayout(panel_fiscal)
        fiscal_layout.setContentsMargins(8, 10, 8, 6)
        fiscal_layout.setSpacing(3)
        
        grid_iva = QGridLayout()
        grid_iva.setHorizontalSpacing(8)
        grid_iva.setVerticalSpacing(2)
        
        # Fila 0: Gravada 10% e IVA 10%
        grid_iva.addWidget(QLabel("Grav. 10%:"), 0, 0)
        self.lbl_gravada_10 = QLabel("0")
        self.lbl_gravada_10.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_gravada_10.setStyleSheet("font-weight: bold; color: #37474f;")
        grid_iva.addWidget(self.lbl_gravada_10, 0, 1)
        
        grid_iva.addWidget(QLabel("IVA 10%:"), 0, 2)
        self.lbl_iva_10 = QLabel("0")
        self.lbl_iva_10.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_iva_10.setStyleSheet("font-weight: bold; color: #1565c0;")
        grid_iva.addWidget(self.lbl_iva_10, 0, 3)
        
        # Fila 1: Gravada 5% e IVA 5%
        grid_iva.addWidget(QLabel("Grav. 5%:"), 1, 0)
        self.lbl_gravada_5 = QLabel("0")
        self.lbl_gravada_5.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_gravada_5.setStyleSheet("font-weight: bold; color: #37474f;")
        grid_iva.addWidget(self.lbl_gravada_5, 1, 1)
        
        grid_iva.addWidget(QLabel("IVA 5%:"), 1, 2)
        self.lbl_iva_5 = QLabel("0")
        self.lbl_iva_5.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_iva_5.setStyleSheet("font-weight: bold; color: #00897b;")
        grid_iva.addWidget(self.lbl_iva_5, 1, 3)
        
        # Fila 2: Exentas y Total IVA
        grid_iva.addWidget(QLabel("Exentas:"), 2, 0)
        self.lbl_exenta = QLabel("0")
        self.lbl_exenta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_exenta.setStyleSheet("font-weight: bold; color: #546e7a;")
        grid_iva.addWidget(self.lbl_exenta, 2, 1)
        
        grid_iva.addWidget(QLabel("Total IVA:"), 2, 2)
        self.lbl_total_iva = QLabel("0")
        self.lbl_total_iva.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_total_iva.setStyleSheet("font-weight: bold; color: #c62828; font-size: 12px;")
        grid_iva.addWidget(self.lbl_total_iva, 2, 3)
        
        fiscal_layout.addLayout(grid_iva)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        fiscal_layout.addWidget(line)
        
        # Botonera de Atajos Rápidos de Caja
        shortcuts_layout = QHBoxLayout()
        shortcuts_layout.setSpacing(4)
        
        btn_f2 = QPushButton("🔍 [F2] Buscar")
        btn_f2.setStyleSheet("background-color: #e3f2fd; color: #0d47a1; font-weight: bold; padding: 4px; font-size: 10px;")
        btn_f2.clicked.connect(self.open_product_search)
        
        btn_f8 = QPushButton("👤 [F8] RUC")
        btn_f8.setStyleSheet("background-color: #e8f5e9; color: #1b5e20; font-weight: bold; padding: 4px; font-size: 10px;")
        btn_f8.clicked.connect(self.open_client_search)
        
        btn_f5 = QPushButton("📋 [F5] Presup.")
        btn_f5.setStyleSheet("background-color: #e1f5fe; color: #0277bd; font-weight: bold; padding: 4px; font-size: 10px;")
        btn_f5.clicked.connect(self.abrir_buscar_presupuesto)
        
        btn_f7 = QPushButton("💸 [F7] Sangría")
        btn_f7.setStyleSheet("background-color: #e0f2f1; color: #004d40; font-weight: bold; padding: 4px; font-size: 10px;")
        btn_f7.clicked.connect(self.open_caja_movimiento)
        
        btn_f9 = QPushButton("🚫 [F9] Anular")
        btn_f9.setStyleSheet("background-color: #ffebee; color: #b71c1c; font-weight: bold; padding: 4px; font-size: 10px;")
        btn_f9.clicked.connect(self.cancelar_venta_actual)

        btn_f10 = QPushButton("📊 [F10] Caja")
        btn_f10.setStyleSheet("background-color: #fff3e0; color: #e65100; font-weight: bold; padding: 4px; font-size: 10px;")
        btn_f10.clicked.connect(self.open_reporte_z)
        
        shortcuts_layout.addWidget(btn_f2)
        shortcuts_layout.addWidget(btn_f5)
        shortcuts_layout.addWidget(btn_f7)
        shortcuts_layout.addWidget(btn_f8)
        shortcuts_layout.addWidget(btn_f9)
        shortcuts_layout.addWidget(btn_f10)
        fiscal_layout.addLayout(shortcuts_layout)
        
        bottom_panel_layout.addWidget(panel_fiscal)
        
        # 2. Botones de Cierre y Operaciones de POS (Centro)
        cierre_layout = QVBoxLayout()
        cierre_layout.addStretch()
        
        btn_quitar_item = QPushButton("❌ Quitar Ítem [Supr]")
        btn_quitar_item.setStyleSheet("background-color: #ffebee; color: #b71c1c; font-weight: bold; border: 1px solid #ef9a9a; padding: 5px;")
        btn_quitar_item.clicked.connect(self.quitar_item_seleccionado)

        btn_cancelar_venta = QPushButton("🚫 Cancelar Venta [F9]")
        btn_cancelar_venta.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 5px;")
        btn_cancelar_venta.clicked.connect(self.cancelar_venta_actual)

        btn_sangria = QPushButton("💸 Movimiento/Sangría [F7]")
        btn_sangria.setStyleSheet("background-color: #00695c; color: white; font-weight: bold; padding: 5px;")
        btn_sangria.clicked.connect(self.open_caja_movimiento)

        btn_cargar_presupuesto = QPushButton("Cargar Presupuesto [F5]")
        btn_cargar_presupuesto.setStyleSheet("background-color: #f57c00; color: white; font-weight: bold; padding: 5px;")
        btn_cargar_presupuesto.clicked.connect(self.abrir_buscar_presupuesto)
        
        btn_presupuesto = QPushButton("Presupuesto [F6]")
        btn_presupuesto.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 5px;")
        btn_presupuesto.clicked.connect(self.procesar_presupuesto)
        
        btn_factura = QPushButton("Cobrar/Factura [F11]")
        btn_factura.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 10px; font-size: 13px;")
        btn_factura.clicked.connect(self.procesar_factura)
        
        cierre_layout.addWidget(btn_quitar_item)
        cierre_layout.addWidget(btn_cancelar_venta)
        cierre_layout.addWidget(btn_sangria)
        cierre_layout.addWidget(btn_cargar_presupuesto)
        cierre_layout.addWidget(btn_presupuesto)
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
        self.lbl_total_gral = QLabel("0")
        self.lbl_total_gral.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        totals_layout.addWidget(self.lbl_total_gral, 3, 3)
        
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
        elif event.key() in (Qt.Key.Key_F2, Qt.Key.Key_F4):
            self.open_product_search()
        elif event.key() == Qt.Key.Key_F5:
            self.abrir_buscar_presupuesto()
        elif event.key() == Qt.Key.Key_F6:
            self.procesar_presupuesto()
        elif event.key() == Qt.Key.Key_F7:
            self.open_caja_movimiento()
        elif event.key() == Qt.Key.Key_F9:
            self.cancelar_venta_actual()
        elif event.key() == Qt.Key.Key_F10:
            self.open_reporte_z()
        elif event.key() in (Qt.Key.Key_F11, Qt.Key.Key_F12):
            self.procesar_factura()
        elif event.key() == Qt.Key.Key_Delete:
            self.quitar_item_seleccionado()
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
                cliente_a_facturar = getattr(dialog, 'selected_client', cliente)
                self.guardar_venta_db(dialog.payments_list, cliente_a_facturar)
                
    def guardar_venta_db(self, payments_list, cliente=None):
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        try:
            # 0. Validar todos los ítems con POSGuardrail antes de tocar DB o stock
            clean_items = []
            for item_data in self.ventas_model.items:
                payload = {
                    "plu_code": item_data['codigo'],
                    "description": item_data['descripcion'],
                    "quantity": str(item_data['cantidad']),
                    "unit_price": str(item_data['precio']),
                    "tax_rate": int(item_data.get('impuesto_porc', 10))
                }
                status = POSGuardrail.validate_sale_item(payload)
                if not status.is_valid:
                    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.critical(self, "Error de Validación", f"Error en artículo {item_data['codigo']}: {', '.join(status.errors)}")
                    else:
                        print(f"Error de Validación en artículo {item_data['codigo']}: {', '.join(status.errors)}")
                    db.close()
                    return
                clean_items.append((item_data, status.clean_data))

            # 1. Crear Factura
            if cliente:
                cod_cli = cliente.cli_codigo
            else:
                cliente_txt = self.txt_cliente.text()
                cod_cli = cliente_txt.split(" - ")[0] if " - " in cliente_txt else "000001"
            
            nueva_venta = models.Invoice(
                ven_codcli=cod_cli,
                ven_total=_safe_dec(self.lbl_pyg.text().replace(',', '')),
                ven_codmnd='PYG'
            )
            db.add(nueva_venta)
            db.flush() # Para obtener el ID generado
            if not nueva_venta.ven_numero:
                nueva_venta.ven_numero = nueva_venta.id
            
            # 2. Crear Detalle de Factura y Descontar Stock
            for item_data, clean_data in clean_items:
                cod_art = clean_data['plu_code']
                cantidad = clean_data['quantity']
                precio = clean_data['unit_price']
                
                item = models.InvoiceItem(
                    vit_numero=nueva_venta.ven_numero,
                    vit_articu=cod_art,
                    vit_canti=cantidad,
                    vit_precio=precio
                )
                db.add(item)
                
                # Descontar stock general
                producto = db.query(models.Product).filter_by(art_codigo=cod_art).first()
                if producto:
                    producto.art_stkini = _safe_dec(producto.art_stkini or 0) - cantidad
                    
                    # FIFO Descontar stock de lotes
                    qty_to_deduct = cantidad
                    batches = (db.query(models.ProductBatch)
                                 .filter(models.ProductBatch.product_id == producto.id, 
                                         models.ProductBatch.stock_actual > 0)
                                 .order_by(models.ProductBatch.fecha_vencimiento.asc())
                                 .all())
                    
                    for b in batches:
                        if qty_to_deduct <= Decimal('0'):
                            break
                        available = _safe_dec(b.stock_actual)
                        if available >= qty_to_deduct:
                            b.stock_actual = available - qty_to_deduct
                            qty_to_deduct = Decimal('0')
                        else:
                            b.stock_actual = Decimal('0')
                            qty_to_deduct = qty_to_deduct - available
            
            # 3. Registrar Cobranza
            for p in payments_list:
                pago = models.Payment(
                    cob_monto=p['monto_origen'],
                    cob_monto_pyg=p['monto_pyg'],
                    cob_vennro=nueva_venta.ven_numero,
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
            
            # Si la venta proviene de un presupuesto, marcarlo como FACTURADO
            if getattr(self, 'active_budget_id', None):
                b_obj = db.query(models.Budget).filter_by(id=self.active_budget_id).first()
                if b_obj:
                    b_obj.estado = 'FACTURADO'
                self.active_budget_id = None
            
            db.commit()
            invoice_id = nueva_venta.id
            
            # Limpiar pantalla para próxima venta
            self.ventas_model.clear()
            self.txt_cliente.setText("000001 - CONSUMIDOR FINAL")
            self.active_budget_id = None
            self.calcular_totales()
            self.cargar_historial_ventas()
            
            # Mostrar e Imprimir Ticket Fiscal con desglose de IVA
            from ui.ticket_dialog import TicketDialog
            ticket_dlg = TicketDialog(invoice_id, self)
            if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
                ticket_dlg.exec()
            
        except Exception as e:
            db.rollback()
            print("Error al guardar:", str(e))
        finally:
            db.close()
            
    def cargar_historial_ventas(self):
        from database import SessionLocal
        import models
        from datetime import datetime, time
        db = SessionLocal()
        
        # Ventas del día actual, orden cronológico (ascendente)
        today_start = datetime.combine(datetime.today(), time.min)
        facturas = db.query(models.Invoice).filter(models.Invoice.ven_fecha >= today_start).order_by(models.Invoice.id.asc()).limit(200).all()
        
        self.table_historial.setSortingEnabled(False)
        self.table_historial.setRowCount(0)
        for row, fac in enumerate(facturas):
            self.table_historial.insertRow(row)
            
            # Usar QTableWidgetItem numérico para permitir ordenamiento correcto si se hace clic
            item_nro = QTableWidgetItem()
            item_nro.setData(Qt.ItemDataRole.DisplayRole, fac.id)
            self.table_historial.setItem(row, 0, item_nro)
            
            self.table_historial.setItem(row, 1, QTableWidgetItem(fac.ven_fecha.strftime("%H:%M")))
            
            cliente_nombre = fac.client.cli_nombre if fac.client else "CONSUMIDOR FINAL"
            self.table_historial.setItem(row, 2, QTableWidgetItem(cliente_nombre))
            
            item_total = QTableWidgetItem()
            item_total.setData(Qt.ItemDataRole.DisplayRole, int(fac.ven_total))
            self.table_historial.setItem(row, 3, item_total)
            
            self.table_historial.setItem(row, 4, QTableWidgetItem(f"{fac.id}/1"))
            
            self.table_historial.item(row, 0).setData(Qt.ItemDataRole.UserRole, fac.id)
            
        self.table_historial.setSortingEnabled(True)
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
        dialog = CajaDialog(session_id=getattr(self, 'session_id', None),
                            current_user=self.current_user, parent=self)
        dialog.exec()

    # ─── Canales de Precios ──────────────────────────────────────────────────
    def cargar_canales_precios(self):
        """Rellena cmb_canal_precio con Minorista Estándar + todas las PriceLists activas."""
        from database import SessionLocal
        import models
        self.cmb_canal_precio.blockSignals(True)
        self.cmb_canal_precio.clear()
        self.cmb_canal_precio.addItem("🏪 Minorista (Estándar)", None)  # None = precio art_preven
        db = SessionLocal()
        try:
            listas = db.query(models.PriceList).order_by(models.PriceList.id).all()
            for lst in listas:
                self.cmb_canal_precio.addItem(f"📋 {lst.pl_nombre}", lst.id)
        finally:
            db.close()
        self.cmb_canal_precio.blockSignals(False)

    def on_canal_precio_changed(self, index):
        """Recalcula en caliente los precios de todos los ítems del carrito al cambiar de canal."""
        if not self.ventas_model.items:
            return
        canal_nombre = self.cmb_canal_precio.currentText()
        for row, item in enumerate(self.ventas_model.items):
            nuevo_precio, label = self.get_precio_vigente(item['codigo'], item['cantidad'])
            item['precio'] = nuevo_precio
            # Limpiar badge anterior y poner el nuevo si lo hay
            desc_base = item['descripcion']
            for badge in ["🏪 ", "📋 ", "🏷️ ", "📊 ", "🏬 "]:
                if f"  {badge}" in desc_base:
                    desc_base = desc_base.split(f"  {badge}")[0].strip()
            item['descripcion'] = f"{desc_base}  {label}" if label else desc_base
            self.ventas_model._recalcular_fila(row)
            self.ventas_model.dataChanged.emit(
                self.ventas_model.index(row, 0),
                self.ventas_model.index(row, self.ventas_model.columnCount() - 1)
            )
        self.calcular_totales()

    # ─── Operaciones Ergonómicas de POS ──────────────────────────────────────
    def quitar_item_seleccionado(self):
        """Elimina la línea seleccionada del carrito y recalcula totales [Supr]."""
        indexes = self.table_detalle.selectionModel().selectedRows()
        if not indexes:
            # Si nada seleccionado, tomar la fila actual del cursor
            curr = self.table_detalle.currentIndex()
            if curr.isValid():
                indexes = [curr]
        if indexes:
            row = indexes[0].row()
            if 0 <= row < self.ventas_model.rowCount():
                self.ventas_model.remove_item(row)
                self.calcular_totales()
                self.update_product_view()

    def cancelar_venta_actual(self):
        """Cancela (vacía) el carrito activo con confirmación [F9]."""
        if self.ventas_model.rowCount() == 0:
            return
        resp = QMessageBox.question(
            self, "Cancelar Venta",
            "¿Desea cancelar toda la venta en curso?\nSe borrarán todos los ítems del carrito.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.ventas_model.clear()
            self.txt_cliente.setText("")
            self.calcular_totales()
            self.update_product_view()
            self.txt_codigo.setFocus()

    def open_caja_movimiento(self):
        """Abre el diálogo de Fondo Fijo / Sangría de Caja [F7]."""
        from ui.caja_movimiento_dialog import CajaMovimientoDialog
        dialog = CajaMovimientoDialog(
            session_id=getattr(self, 'session_id', None),
            current_user=self.current_user,
            parent=self
        )
        dialog.exec()

    def open_admin_panel(self):
        from ui.admin_window import AdminWindow
        if not hasattr(self, 'admin_window') or not self.admin_window:
            self.admin_window = AdminWindow(current_user=self.current_user)
        self.admin_window.show()
        self.admin_window.activateWindow()

    def ver_detalle_factura(self, item=None):
        row = self.table_historial.currentRow()
        if row < 0 and item:
            row = item.row()
        if row >= 0:
            fac_item = self.table_historial.item(row, 4) or self.table_historial.item(row, 0)
            if fac_item:
                txt = fac_item.text().replace('#', '').strip()
                try:
                    invoice_id = int(txt)
                    from ui.invoice_detail_dialog import InvoiceDetailDialog
                    dlg = InvoiceDetailDialog(invoice_id, self)
                    dlg.exec()
                except Exception as e:
                    print(f"Error abriendo detalle de factura: {e}")
                
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
        cantidad_balanza = Decimal('1')
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
        
        factor_conversion = Decimal('1')
        
        if not prod:
            barcode = db.query(models.ProductBarcode).filter_by(barcode=codigo).first()
            if barcode and barcode.product.is_active:
                prod = barcode.product
                factor_conversion = _safe_dec(barcode.factor_conversion)
                
        db.close()
        
        if prod:
            final_qty = cantidad_balanza if parsed.get("es_balanza") else (Decimal('1') * factor_conversion)
            self.txt_codigo.clear()
            self.add_product_to_grid(prod, cantidad=final_qty)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Encontrado", "Artículo no encontrado o inactivo.")
            self.txt_codigo.selectAll()
            
    def get_precio_vigente(self, art_codigo, cantidad=1):
        """Devuelve (precio, label). Prioridad: Promo > Tier > Canal Activo > Lista Cliente > Normal."""
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
        
        # 3. Canal de precio activo seleccionado en combo (PriceList de canal)
        canal_list_id = self.cmb_canal_precio.currentData() if hasattr(self, 'cmb_canal_precio') else None
        if canal_list_id:
            canal_item = db.query(models.PriceListItem).filter_by(
                pli_list_id=canal_list_id,
                pli_articu=art_codigo
            ).first()
            if canal_item:
                canal_nombre = self.cmb_canal_precio.currentText()
                db.close()
                return _safe_dec(canal_item.pli_precio), f"\U0001f3ea {canal_nombre}"

        # 4. Lista de precio del cliente (cuenta corriente / convenio)
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
        
        # 5. Precio Minorista estándar (art_preven)
        prod = db.query(models.Product).filter_by(art_codigo=art_codigo).first()
        db.close()
        if prod:
            return _safe_dec(prod.art_preven or 0), None
        return Decimal('0'), None

    def add_product_to_grid(self, product, cantidad=Decimal('1')):
        from database import format_stock_qty
        stock_actual = _safe_dec(product.art_stkini or 0)
        
        # Check current qty already in cart to determine tier correctly
        qty_en_carrito = Decimal('0')
        for item in self.ventas_model.items:
            if item['codigo'] == product.art_codigo:
                qty_en_carrito = item['cantidad']
                break
        qty_total = qty_en_carrito + _safe_dec(cantidad)
        
        # Frase de advertencia por stock negativo o insuficiente
        if stock_actual <= Decimal('0') or qty_total > stock_actual:
            from PyQt6.QtWidgets import QMessageBox
            if stock_actual <= Decimal('0'):
                frase_adv = f"El producto '{product.art_descri}' (Cód: {product.art_codigo}) se encuentra con STOCK NEGATIVO O AGOTADO ({format_stock_qty(stock_actual)})."
            else:
                frase_adv = f"La cantidad solicitada ({format_stock_qty(qty_total)}) supera el stock disponible ({format_stock_qty(stock_actual)})."
                
            resp = QMessageBox.warning(
                self,
                "⚠️ Advertencia de Stock",
                f"{frase_adv}\n\n¿Desea autorizar la venta de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                self.statusBar().showMessage(f"❌ Venta no autorizada: {frase_adv}", 7000)
                return

        precio, label = self.get_precio_vigente(product.art_codigo, qty_total)
        row_idx = self.ventas_model.add_item(product, cantidad, precio_override=precio, promo_label=label)
        self.calcular_totales()
        
        if row_idx is not None:
            self.table_detalle.selectRow(row_idx)
            self.update_product_view()
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
        
        from decimal import Decimal
        rate_usd = rates.get("USD", Decimal('7500.0'))
        rate_brl = rates.get("BRL", Decimal('1500.0'))
        rate_ars = rates.get("ARS", Decimal('10.0'))
        
        total_usd = (total_pyg / rate_usd).quantize(Decimal('0.01')) if rate_usd > 0 else Decimal('0')
        total_brl = (total_pyg / rate_brl).quantize(Decimal('0.01')) if rate_brl > 0 else Decimal('0')
        total_ars = (total_pyg / rate_ars).quantize(Decimal('0.01')) if rate_ars > 0 else Decimal('0')
        
        self.lbl_pyg.setText(f"{total_pyg:,.0f}")
        self.lbl_usd.setText(f"{total_usd:,.2f}")
        self.lbl_brl.setText(f"{total_brl:,.2f}")
        self.lbl_ars.setText(f"{total_ars:,.2f}")
        self.lbl_total_gral.setText(f"{total_pyg:,.0f}")
        
        # Liquidación I.V.A. en vivo (Ley 6380/19)
        gravada_10 = Decimal('0')
        iva_10 = Decimal('0')
        gravada_5 = Decimal('0')
        iva_5 = Decimal('0')
        exenta = Decimal('0')
        
        for item in self.ventas_model.items:
            tot = _safe_dec(item.get('total', 0))
            imp = int(item.get('impuesto_porc', 10))
            res = tax_calculator.calcular_iva_linea(tot, imp)
            gravada_10 += res['gravada_10']
            iva_10 += res['iva_10']
            gravada_5 += res['gravada_5']
            iva_5 += res['iva_5']
            exenta += res['exenta']
            
        total_iva = iva_10 + iva_5
        
        if hasattr(self, 'lbl_gravada_10'):
            self.lbl_gravada_10.setText(f"{gravada_10:,.0f}")
            self.lbl_iva_10.setText(f"{iva_10:,.0f}")
            self.lbl_gravada_5.setText(f"{gravada_5:,.0f}")
            self.lbl_iva_5.setText(f"{iva_5:,.0f}")
            self.lbl_exenta.setText(f"{exenta:,.0f}")
            self.lbl_total_iva.setText(f"{total_iva:,.0f}")
        
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
                    producto.art_stkini = _safe_dec(producto.art_stkini) - _safe_dec(cantidad)
            
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
            
    def procesar_presupuesto(self):
        """
        Emite un Presupuesto / Cotización formal para el cliente [F6].
        Calcula totales multi-moneda e IVA (Ley 6380/19) sin alterar stock.
        """
        if self.ventas_model.rowCount() == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Presupuesto", "El carrito de ventas está vacío. Ingrese artículos antes de generar un presupuesto.")
            return
            
        from PyQt6.QtWidgets import QMessageBox
        from database import SessionLocal
        import models
        from ui.budget_dialog import BudgetDialog
        
        # 0. Validar todos los ítems con POSGuardrail
        for item_data in self.ventas_model.items:
            payload = {
                "plu_code": item_data['codigo'],
                "description": item_data['descripcion'],
                "quantity": str(item_data['cantidad']),
                "unit_price": str(item_data['precio']),
                "tax_rate": int(item_data.get('impuesto_porc', 10))
            }
            status = POSGuardrail.validate_sale_item(payload)
            if not status.is_valid:
                QMessageBox.critical(self, "Error de Validación", f"Artículo inválido en presupuesto ({item_data['descripcion']}):\n" + "\n".join(status.errors))
                return
                
        db = SessionLocal()
        try:
            cliente_txt = self.txt_cliente.text()
            if " - " in cliente_txt:
                parts = cliente_txt.split(" - ", 1)
                cod_cli = parts[0]
                nom_cli = parts[1]
            else:
                cod_cli = "000001"
                nom_cli = "CONSUMIDOR FINAL"
                
            cli_obj = db.query(models.Client).filter_by(cli_codigo=cod_cli).first()
            ruc_cli = cli_obj.cli_ruc if (cli_obj and cli_obj.cli_ruc) else "44444401-7"
            
            tot_pyg = _safe_dec(self.lbl_pyg.text().replace(',', ''))
            tot_usd = _safe_dec(self.lbl_usd.text().replace(',', ''))
            tot_brl = _safe_dec(self.lbl_brl.text().replace(',', ''))
            tot_ars = _safe_dec(self.lbl_ars.text().replace(',', ''))
            
            nuevo_presupuesto = models.Budget(
                codcli=cod_cli,
                cliente_nombre=nom_cli,
                cliente_ruc=ruc_cli,
                total_pyg=tot_pyg,
                total_usd=tot_usd,
                total_brl=tot_brl,
                total_ars=tot_ars,
                estado='PENDIENTE',
                validez_dias=15
            )
            db.add(nuevo_presupuesto)
            db.flush()
            
            nuevo_presupuesto.numero = f"PRES-{nuevo_presupuesto.id:06d}"
            
            for item_data in self.ventas_model.items:
                cod_art = item_data['codigo']
                cantidad = _safe_dec(item_data['cantidad'])
                precio = _safe_dec(item_data['precio'])
                subtotal = (cantidad * precio).quantize(Decimal('1'))
                tasa = int(item_data.get('impuesto_porc', 10))
                
                b_item = models.BudgetItem(
                    budget_id=nuevo_presupuesto.id,
                    articu=cod_art,
                    descripcion=item_data['descripcion'],
                    canti=cantidad,
                    precio=precio,
                    impuesto_porc=tasa,
                    subtotal=subtotal
                )
                db.add(b_item)
                # NOTA: Presupuesto comercial - NO deduce stock
                
            db.commit()
            budget_id = nuevo_presupuesto.id
            
            # Mostrar diálogo de impresión de presupuesto
            if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
                dlg = BudgetDialog(budget_id, self)
                dlg.exec()
                reply = QMessageBox.question(
                    self,
                    "Presupuesto Generado",
                    f"Presupuesto {nuevo_presupuesto.numero} generado con éxito.\n\n¿Desea limpiar la pantalla de ventas para una nueva operación?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            else:
                reply = QMessageBox.StandardButton.Yes
            if reply == QMessageBox.StandardButton.Yes:
                self.ventas_model.clear()
                self.txt_cliente.setText("000001 - CONSUMIDOR FINAL")
                self.active_budget_id = None
                self.calcular_totales()
            else:
                self.active_budget_id = budget_id
                
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Error al generar presupuesto: {str(e)}")
        finally:
            db.close()
            
    def abrir_buscar_presupuesto(self):
        """
        Abre el buscador de presupuestos [F5] para recuperar una cotización
        y cargar sus artículos en la grilla de ventas lista para cobrar [F11].
        """
        from ui.budget_search_dialog import BudgetSearchDialog
        from PyQt6.QtWidgets import QMessageBox
        
        dlg = BudgetSearchDialog(self)
        if dlg.exec() and dlg.selected_budget:
            b = dlg.selected_budget
            
            if self.ventas_model.rowCount() > 0:
                reply = QMessageBox.question(
                    self,
                    "Reemplazar Carrito",
                    f"El carrito actual contiene artículos.\n\n¿Desea reemplazar el contenido con los artículos del Presupuesto {b['numero']}?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Cargar cliente
            if b.get('codcli') and b.get('cliente_nombre'):
                self.txt_cliente.setText(f"{b['codcli']} - {b['cliente_nombre']}")
            else:
                self.txt_cliente.setText("000001 - CONSUMIDOR FINAL")
                
            # Cargar artículos a la grilla de ventas
            from database import SessionLocal
            import models
            db = SessionLocal()
            try:
                self.ventas_model.clear()
                for it in b.get('items', []):
                    prod = db.query(models.Product).filter_by(art_codigo=it['codigo']).first()
                    if prod:
                        self.ventas_model.add_item(
                            prod, 
                            cantidad=_safe_dec(it['cantidad']), 
                            precio_override=_safe_dec(it['precio'])
                        )
                    else:
                        # Respaldo si el producto ya no está activo
                        self.ventas_model.items.append({
                            'codigo': it['codigo'],
                            'descripcion': it['descripcion'],
                            'cantidad': _safe_dec(it['cantidad']),
                            'precio': _safe_dec(it['precio']),
                            'impuesto_porc': it.get('impuesto_porc', 10),
                            'subtotal': _safe_dec(it['subtotal'])
                        })
                        self.ventas_model.layoutChanged.emit()
            finally:
                db.close()
                
            self.active_budget_id = b['id']
            self.calcular_totales()
            QMessageBox.information(
                self,
                "Presupuesto Cargado",
                f"Presupuesto {b['numero']} cargado exitosamente con {len(b['items'])} artículos.\n\nPresione [F11] para cobrar y emitir la factura."
            )
            
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

    def update_product_view(self, product=None):
        if self.chk_visor.isChecked():
            return
            
        from database import SessionLocal, format_stock_qty, resolve_image_path
        import models
        
        # Proteger contra objetos enviados por señales de Qt (QItemSelection, int, etc.)
        producto = product if (product is not None and hasattr(product, 'art_codigo')) else None
        if producto is None:
            indexes = self.table_detalle.selectionModel().selectedRows()
            row = None
            if indexes:
                row = indexes[0].row()
            else:
                curr = self.table_detalle.currentIndex()
                if curr.isValid() and 0 <= curr.row() < self.ventas_model.rowCount():
                    row = curr.row()
                    
            if row is None or row >= self.ventas_model.rowCount():
                self.lbl_visor_descri.setText("Seleccione un producto")
                self.lbl_visor_codigo.setText("Código: -")
                self.lbl_visor_precio.setText("Precio: -")
                self.lbl_visor_stock.setText("Stock Disponible: -")
                self.lbl_visor_img.clear()
                self.lbl_visor_img.setText("📷\nSin Imagen")
                return
                
            cod_art = self.ventas_model.items[row]['codigo']
            db = SessionLocal()
            producto = db.query(models.Product).filter_by(art_codigo=cod_art).first()
            db.close()
        
        if producto:
            self.lbl_visor_descri.setText(producto.art_descri)
            self.lbl_visor_codigo.setText(f"Código: {producto.art_codigo}")
            self.lbl_visor_precio.setText(f"Precio: ₲ {producto.art_preven:,.0f}".replace(",", "."))
            stk_str = format_stock_qty(producto.art_stkini)
            self.lbl_visor_stock.setText(f"Stock Disponible: {stk_str}")
            if _safe_dec(producto.art_stkini or 0) < Decimal('0'):
                self.lbl_visor_stock.setStyleSheet("color: #d32f2f; font-weight: bold;")
            else:
                self.lbl_visor_stock.setStyleSheet("color: #2e7d32; font-weight: bold;")
            
            img_path = resolve_image_path(getattr(producto, 'image_path', None), producto.art_codigo)
            if img_path:
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    self.lbl_visor_img.setPixmap(pixmap.scaled(
                        220, 180, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    ))
                else:
                    self.lbl_visor_img.clear()
                    self.lbl_visor_img.setText("📷\nSin Imagen")
            else:
                self.lbl_visor_img.clear()
                self.lbl_visor_img.setText("📷\nSin Imagen")
        else:
            self.lbl_visor_descri.setText("Producto no encontrado")
            self.lbl_visor_img.clear()
            self.lbl_visor_img.setText("📷\nSin Imagen")