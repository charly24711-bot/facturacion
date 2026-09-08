import sys
import datetime
from decimal import Decimal
from sqlalchemy import func
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QStackedWidget, QMessageBox, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

import database
import models
from database import SessionLocal, format_stock_qty

class AdminWindow(QMainWindow):
    """
    Panel Administrativo y Gerencial (Back-Office) de Alta Gama.
    Centraliza el control de inventario, compras, fijación de precios,
    cuentas corrientes, auditoría, tesorería multidivisa y métricas del supermercado.
    """
    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user or {
            "id": 1,
            "username": "admin",
            "full_name": "Administrador General",
            "role": "ADMIN"
        }
        self.pos_window = None
        
        self.setWindowTitle("TRIFRONTERA STOCK - Panel Administrativo & Gerencial")
        self.resize(1260, 800)
        self.setMinimumSize(1080, 680)
        
        self.init_ui()
        self.refresh_dashboard_data()


    def init_ui(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QScrollArea, QGridLayout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 1. HEADER SUPERIOR ────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d1b2a, stop:1 #1b263b);
                border-bottom: 2px solid #415a77;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        lbl_title = QLabel("🏢 TRIFRONTERA STOCK  |  Plataforma ERP")
        lbl_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #e0e1dd; letter-spacing: 1px;")
        header_layout.addWidget(lbl_title)

        header_layout.addStretch()

        # Botón de acceso directo a POS (Caja)
        self.btn_open_pos = QPushButton("🛒 Facturación POS [F1]")
        self.btn_open_pos.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_open_pos.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: #ffffff;
                padding: 8px 18px;
                border-radius: 5px;
                border: 1px solid #388e3c;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_open_pos.clicked.connect(self.abrir_pos)
        header_layout.addWidget(self.btn_open_pos)

        # Información del usuario
        lbl_user = QLabel(f"👤 {self.current_user['full_name']} ({self.current_user['role']})")
        lbl_user.setFont(QFont("Arial", 10))
        lbl_user.setStyleSheet("color: #a9bcd0; margin: 0 14px;")
        header_layout.addWidget(lbl_user)

        # Botón cerrar sesión
        self.btn_logout = QPushButton("🔒 Cerrar Sesión")
        self.btn_logout.setFont(QFont("Arial", 9))
        self.btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: #ffffff;
                padding: 7px 14px;
                border-radius: 4px;
                border: 1px solid #b71c1c;
            }
            QPushButton:hover {
                background-color: #8e0000;
            }
        """)
        self.btn_logout.clicked.connect(self.cerrar_sesion)
        header_layout.addWidget(self.btn_logout)

        main_layout.addWidget(header)

        # ── 2. AREA CENTRAL (SCROLL AREA) ──────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f1f5f9; }")
        
        content_area = QWidget()
        content_area.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content_area)
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. Vista Dashboard (Ahora es el Grid Principal)
        self.view_dashboard = self.crear_vista_dashboard()
        self.content_layout.addWidget(self.view_dashboard)

        scroll.setWidget(content_area)
        main_layout.addWidget(scroll, stretch=1)

    # ── VISTA DASHBOARD ENRIQUECIDO ─────────────────────────────────────────────
    def crear_vista_dashboard(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QScrollArea, QGridLayout
        dash = QWidget()
        layout = QVBoxLayout(dash)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Barra superior con título y botón refrescar
        top_bar = QHBoxLayout()
        lbl_dash_title = QLabel("Seis Módulos, Una Sola Plataforma")
        lbl_dash_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        lbl_dash_title.setStyleSheet("color: #1e1b4b;")
        top_bar.addWidget(lbl_dash_title)

        self.lbl_timestamp = QLabel("")
        self.lbl_timestamp.setFont(QFont("Arial", 9))
        self.lbl_timestamp.setStyleSheet("color: #64748b; margin-left: 10px;")
        top_bar.addWidget(self.lbl_timestamp)

        top_bar.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizar Datos")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_dashboard_data)
        top_bar.addWidget(self.btn_refresh)
        layout.addLayout(top_bar)

        # Subtitulo
        lbl_sub = QLabel("Todos los datos se ingresan una sola vez y quedan disponibles para toda la operación en tiempo real.")
        lbl_sub.setFont(QFont("Arial", 11))
        lbl_sub.setStyleSheet("color: #475569; margin-bottom: 10px;")
        layout.addWidget(lbl_sub)

        # ── GRID DE 6 MODULOS ──
        grid_layout = QGridLayout()
        grid_layout.setSpacing(25)
        
        # 1. Sistema General
        c1 = self._crear_modulo_card("1. Sistema General", "#8b5cf6", [
            ("⚙️ Configuración del Entorno", self.abrir_configuracion),
            ("🔑 Gestión de Usuarios [F2]", self.abrir_usuarios),
            ("🏢 Datos de la Empresa", self.abrir_config_entorno)
        ])
        grid_layout.addWidget(c1, 0, 0)

        # 2. Control de Stock
        c2 = self._crear_modulo_card("2. Control de Stock", "#3b82f6", [
            ("📦 Catálogo de Productos", self.abrir_productos),
            ("⏳ Control de Lotes FIFO", self.abrir_lotes),
            ("🗑️ Mermas y Ajustes [F4]", self.abrir_mermas),
            ("🏷️ Etiquetas de Góndola [F3]", self.abrir_etiquetas)
        ])
        grid_layout.addWidget(c2, 0, 1)

        # 3. Finanzas
        c3 = self._crear_modulo_card("3. Finanzas", "#10b981", [
            ("💳 Cuentas Corrientes (Créditos)", self.abrir_cuentas_corrientes),
            ("📑 Auditoría de Cajas (Z)", self.abrir_auditoria_caja),
            ("📊 Dashboard de Ventas", None) # Placeholder
        ])
        grid_layout.addWidget(c3, 0, 2)

        # 4. Contabilidad
        c4 = self._crear_modulo_card("4. Contabilidad", "#6366f1", [
            ("📊 Exportar DNIT Hechauka [F6]", self.abrir_hechauka),
            ("⚙️ Configuración Fiscal DNIT", self.abrir_configuracion)
        ])
        grid_layout.addWidget(c4, 1, 0)

        # 5. Facturación y Ventas
        c5 = self._crear_modulo_card("5. Facturación y Ventas", "#f59e0b", [
            ("🛒 Punto de Venta (POS)", self.abrir_pos),
            ("👥 Gestión de Clientes", self.abrir_clientes),
            ("🏷️ Listas de Precios & Escalas", self.abrir_precios)
        ])
        grid_layout.addWidget(c5, 1, 1)

        # 6. Compras
        c6 = self._crear_modulo_card("6. Compras", "#ec4899", [
            ("🚚 Compras y Proveedores", self.abrir_compras),
            ("🧾 Ingreso de Facturas", self.abrir_compras)
        ])
        grid_layout.addWidget(c6, 1, 2)
        
        layout.addLayout(grid_layout)
        
        # ── SECCION INFERIOR (KPIs y Ventas Recientes) ──
        layout.addSpacing(30)
        
        kpi_title = QLabel("Resumen Ejecutivo de Operaciones")
        kpi_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        kpi_title.setStyleSheet("color: #334155;")
        layout.addWidget(kpi_title)
        
        self.kpi_layout = QHBoxLayout()
        self.kpi_ventas = self._crear_kpi_card("Ventas Hoy", "₲ 0", "#3b82f6", "0 tickets emitidos")
        self.kpi_layout.addWidget(self.kpi_ventas)
        self.kpi_compras = self._crear_kpi_card("Compras Hoy", "₲ 0", "#ef4444", "0 facturas reg.")
        self.kpi_layout.addWidget(self.kpi_compras)
        self.kpi_caja = self._crear_kpi_card("Caja Actual", "₲ 0", "#10b981", "Efectivo disponible")
        self.kpi_layout.addWidget(self.kpi_caja)
        layout.addLayout(self.kpi_layout)

        layout.addSpacing(20)

        lbl_vr = QLabel("Últimas Ventas Registradas")
        lbl_vr.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(lbl_vr)

        self.table_ventas_recientes = QTableWidget(0, 6)
        self.table_ventas_recientes.setHorizontalHeaderLabels(
            ["Hora", "Ticket", "Cliente", "Total (₲)", "Método Pago", "Cajero"])
        self.table_ventas_recientes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_ventas_recientes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_ventas_recientes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_ventas_recientes.setStyleSheet("""
            QTableWidget {
                background-color: white; border: 1px solid #e2e8f0; border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #f8fafc; font-weight: bold; border: none; padding: 6px;
            }
        """)
        self.table_ventas_recientes.setFixedHeight(200)
        self.table_ventas_recientes.itemClicked.connect(self.abrir_detalle_venta)
        self.table_ventas_recientes.itemDoubleClicked.connect(self.abrir_detalle_venta)
        layout.addWidget(self.table_ventas_recientes)
        
        lbl_hint = QLabel("💡 Haga clic sobre cualquier venta para abrir el detalle completo y ticket")
        lbl_hint.setStyleSheet("color: #64748b;")
        layout.addWidget(lbl_hint)
        
        layout.addStretch()
        return dash

    def _crear_modulo_card(self, title, color, actions):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        card = QFrame()
        card.setMinimumHeight(220)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            QFrame:hover {{
                border: 1px solid {color};
                background-color: #f8fafc;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {color}; border: none;")
        layout.addWidget(lbl_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #f1f5f9; border: none;")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        layout.addSpacing(10)
        
        for text, callback in actions:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    background-color: transparent;
                    border: none;
                    color: #334155;
                    font-size: 13px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                    color: #0f172a;
                    font-weight: bold;
                }
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if callback:
                btn.clicked.connect(callback)
            layout.addWidget(btn)
            
        layout.addStretch()
        return card

    def _crear_kpi_card(self, titulo, valor_inicial, color_borde, subtitulo):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                border-left: 5px solid {color_borde};
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        lbl_sub = QLabel(titulo.upper())
        lbl_sub.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        lbl_sub.setStyleSheet("color: #64748b; border: none;")

        lbl_val = QLabel(valor_inicial)
        lbl_val.setObjectName("kpi_value")
        lbl_val.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_borde}; border: none;")

        lbl_desc = QLabel(subtitulo)
        lbl_desc.setFont(QFont("Arial", 8))
        lbl_desc.setStyleSheet("color: #94a3b8; border: none;")

        layout.addWidget(lbl_sub)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_desc)
        return card

    def abrir_config_entorno(self):
        from ui.configuracion_entorno import ConfiguracionEntornoDialog
        dlg = ConfiguracionEntornoDialog(self)
        dlg.exec()

    def _btn_style(self, bg_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                font-weight: bold;
                padding: 7px;
                border-radius: 4px;
                border: none;
                font-size: 11px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """

    # ── MÉTODOS DE APERTURA DE MÓDULOS ──────────────────────────────────────────
    def abrir_detalle_venta(self, item=None):
        row = self.table_ventas_recientes.currentRow()
        if row < 0 and item:
            row = item.row()
        if row >= 0:
            fac_item = self.table_ventas_recientes.item(row, 0)
            if fac_item:
                txt = fac_item.text().replace('#', '').strip()
                try:
                    invoice_id = int(txt)
                    from ui.invoice_detail_dialog import InvoiceDetailDialog
                    dlg = InvoiceDetailDialog(invoice_id, self)
                    dlg.exec()
                except Exception as e:
                    print(f"Error abriendo detalle de venta: {e}")

    def abrir_pos(self):
        from ui.main_window import MainWindow
        if not self.pos_window:
            self.pos_window = MainWindow(current_user=self.current_user)
        self.pos_window.show()
        self.pos_window.activateWindow()

    def abrir_productos(self):
        from ui.product_management import ProductManagementDialog
        dlg = ProductManagementDialog(self)
        dlg.exec()
        self.refresh_dashboard_data()

    def abrir_precios(self):
        from ui.price_lists_dialog import PriceListsDialog
        dlg = PriceListsDialog(self)
        dlg.exec()

    def abrir_compras(self):
        from ui.purchase_dialog import PurchaseDialog
        dlg = PurchaseDialog(self)
        dlg.exec()
        self.refresh_dashboard_data()

    def abrir_lotes(self):
        from ui.batches_dialog import BatchesDialog
        dlg = BatchesDialog(self)
        dlg.exec()

    def abrir_cuentas_corrientes(self):
        from ui.customer_accounts_dialog import CustomerAccountsDialog
        dlg = CustomerAccountsDialog(self)
        dlg.exec()

    def abrir_clientes(self):
        from ui.client_management import ClientManagementDialog
        dlg = ClientManagementDialog(self)
        dlg.exec()

    def abrir_auditoria_caja(self):
        from ui.arqueo_dialog import ArqueoDialog
        db = SessionLocal()
        try:
            sesion = db.query(models.CashSession).order_by(models.CashSession.id.desc()).first()
            session_id = sesion.id if sesion else 1
        finally:
            db.close()
        dlg = ArqueoDialog(session_id, self)
        dlg.exec()

    def abrir_configuracion(self):
        from ui.company_settings_dialog import CompanySettingsDialog
        dlg = CompanySettingsDialog(self)
        dlg.exec()

    # ─── FASE 2: Módulos Nuevos ──────────────────────────────────────────────
    def abrir_usuarios(self):
        """Gestión de Usuarios y Cajeros [F2]"""
        from ui.users_management_dialog import UsersManagementDialog
        dlg = UsersManagementDialog(current_user=self.current_user, parent=self)
        dlg.exec()

    def abrir_mermas(self):
        """Mermas y Ajustes de Inventario [F4]"""
        from ui.stock_adjustment_dialog import StockAdjustmentDialog
        dlg = StockAdjustmentDialog(current_user=self.current_user, parent=self)
        dlg.exec()
        self.refresh_dashboard_data()

    def abrir_hechauka(self):
        """Exportación DNIT Hechauka / Marangatú [F6]"""
        from ui.hechauka_export_dialog import HechaukaExportDialog
        dlg = HechaukaExportDialog(current_user=self.current_user, parent=self)
        dlg.exec()

    # ─── FASE 3: Utilidades de Góndola ───────────────────────────────────────
    def abrir_etiquetas(self):
        """Impresión de Etiquetas de Góndola y Códigos de Barras [F3]"""
        from ui.shelf_labels_dialog import ShelfLabelsDialog
        dlg = ShelfLabelsDialog(parent=self)
        dlg.exec()

    def cerrar_sesion(self):
        reply = QMessageBox.question(
            self, "Cerrar Sesión", "¿Está seguro que desea salir del Panel Administrativo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ui.login_dialog import LoginDialog
            self.close()
            dlg = LoginDialog(auto_login=False)
            if dlg.exec():
                if dlg.target_module == 'POS':
                    from ui.main_window import MainWindow
                    pos = MainWindow(current_user=dlg.authenticated_user)
                    pos.show()
                else:
                    admin = AdminWindow(current_user=dlg.authenticated_user)
                    admin.show()

    # ── CARGA Y CÁLCULO DE KPIS (DECIMAL ESTRICTO) ──────────────────────────────
    def refresh_dashboard_data(self):
        db = SessionLocal()
        try:
            now = datetime.datetime.now()
            today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
            self.lbl_timestamp.setText(f"Actualizado: {now.strftime('%d/%m/%Y %H:%M:%S')}")
            
            # 1. Facturas de hoy
            invoices_today = db.query(models.Invoice).filter(models.Invoice.ven_fecha >= today_start).all()
            total_facturado = Decimal('0')
            total_iva_recaudado = Decimal('0')
            
            for inv in invoices_today:
                if inv.ven_total:
                    total_facturado += Decimal(str(inv.ven_total))
                # Calcular IVA de la factura
                if inv.items:
                    for it in inv.items:
                        sub = Decimal(str(it.vit_canti or 0)) * Decimal(str(it.vit_precio or 0))
                        iva_pct = Decimal(str(it.product.art_impu if it.product and it.product.art_impu is not None else 10))
                        if iva_pct == 10:
                            total_iva_recaudado += (sub / Decimal('11'))
                        elif iva_pct == 5:
                            total_iva_recaudado += (sub / Decimal('21'))
                            
            # 2. Stock crítico (menor o igual a 0)
            productos_criticos = db.query(models.Product).filter(models.Product.art_stkini <= 0).count()
            
            # 3. Lotes próximos a vencer (en los próximos 7 días)
            limite_vencimiento = today_start + datetime.timedelta(days=7)
            lotes_proximos = db.query(models.ProductBatch).filter(
                models.ProductBatch.stock_actual > 0,
                models.ProductBatch.fecha_vencimiento <= limite_vencimiento
            ).order_by(models.ProductBatch.fecha_vencimiento.asc()).limit(3).all()

            # 4. Cálculo de Ticket Promedio
            cant_tickets = len(invoices_today)
            ticket_promedio = (total_facturado / Decimal(str(cant_tickets))) if cant_tickets > 0 else Decimal('0')

            # Actualizar labels de KPIs
            if hasattr(self, 'card_ventas'):
                self.card_ventas.findChild(QLabel, "kpi_value").setText(f"Gs. {total_facturado:,.0f}")
                self.card_tickets.findChild(QLabel, "kpi_value").setText(f"{cant_tickets}")
                self.card_ticket_prom.findChild(QLabel, "kpi_value").setText(f"Gs. {ticket_promedio:,.0f}")
                self.card_iva.findChild(QLabel, "kpi_value").setText(f"Gs. {total_iva_recaudado:,.0f}")
                self.card_stock.findChild(QLabel, "kpi_value").setText(f"{productos_criticos} ítems / {len(lotes_proximos)} lotes")

            # 5. Cómputo de Medios de Pago y Multidivisa de Hoy
            pagos_hoy = db.query(models.Payment).filter(models.Payment.cob_fecha >= today_start).all()
            tot_efectivo_pyg = Decimal('0')
            tot_tarjeta_pyg = Decimal('0')
            tot_brl = Decimal('0')
            tot_usd = Decimal('0')
            tot_ars = Decimal('0')

            for p in pagos_hoy:
                mnd = (p.cob_mndori or 'PYG').upper()
                met = (p.cob_metodo or 'Efectivo').lower()
                monto = Decimal(str(p.cob_monto or 0))
                monto_pyg = Decimal(str(p.cob_monto_pyg or monto))

                if mnd == 'BRL' or 'pix' in met:
                    tot_brl += monto
                elif mnd == 'USD':
                    tot_usd += monto
                elif mnd == 'ARS':
                    tot_ars += monto
                elif 'tarjeta' in met or 'pos' in met:
                    tot_tarjeta_pyg += monto_pyg
                else:
                    tot_efectivo_pyg += monto_pyg

            if hasattr(self, 'lbl_pay_pyg'):
                self.lbl_pay_pyg.setText(f"💵 Efectivo: Gs. {tot_efectivo_pyg:,.0f}")
                self.lbl_pay_tarj.setText(f"💳 Tarjetas: Gs. {tot_tarjeta_pyg:,.0f}")
                self.lbl_pay_brl.setText(f"🇧🇷 BRL / PIX: R$ {tot_brl:,.2f}")
                self.lbl_pay_usd.setText(f"🇺🇸 USD: US$ {tot_usd:,.2f}")
                self.lbl_pay_ars.setText(f"🇦🇷 ARS: $ {tot_ars:,.0f}")

            # 6. Cargar tabla de últimas 10 ventas
            recent_invoices = db.query(models.Invoice).order_by(models.Invoice.ven_numero.desc()).limit(10).all()
            self.table_ventas_recientes.setRowCount(len(recent_invoices))
            
            for row, inv in enumerate(recent_invoices):
                num_item = QTableWidgetItem(f"#{inv.ven_numero:06d}")
                fecha_str = inv.ven_fecha.strftime("%d/%m %H:%M") if inv.ven_fecha else "-"
                fecha_item = QTableWidgetItem(fecha_str)
                
                cli_nombre = "Consumidor Final"
                if inv.client:
                    cli_nombre = f"{inv.client.cli_nombre} ({inv.client.cli_ruc or inv.client.cli_codigo})"
                cli_item = QTableWidgetItem(cli_nombre)
                
                monto = Decimal(str(inv.ven_total or 0))
                monto_item = QTableWidgetItem(f"Gs. {monto:,.0f}")
                monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                estado_item = QTableWidgetItem("PAGADO")
                estado_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                estado_item.setForeground(QColor("#059669"))
                
                self.table_ventas_recientes.setItem(row, 0, num_item)
                self.table_ventas_recientes.setItem(row, 1, fecha_item)
                self.table_ventas_recientes.setItem(row, 2, cli_item)
                self.table_ventas_recientes.setItem(row, 3, monto_item)
                self.table_ventas_recientes.setItem(row, 4, estado_item)

            # 7. Cargar Top 5 Artículos Más Vendidos
            top_query = db.query(
                models.Product.art_descri,
                func.sum(models.InvoiceItem.vit_canti).label('total_cant'),
                func.sum(models.InvoiceItem.vit_canti * models.InvoiceItem.vit_precio).label('total_gs')
            ).join(models.Invoice, models.Invoice.ven_numero == models.InvoiceItem.vit_numero)\
             .join(models.Product, models.Product.art_codigo == models.InvoiceItem.vit_articu)\
             .filter(models.Invoice.ven_fecha >= today_start)\
             .group_by(models.Product.art_descri)\
             .order_by(func.sum(models.InvoiceItem.vit_canti).desc())\
             .limit(5).all()

            # Si no hay ventas registradas con fecha de hoy, buscar las más vendidas generales
            if not top_query:
                top_query = db.query(
                    models.Product.art_descri,
                    func.sum(models.InvoiceItem.vit_canti).label('total_cant'),
                    func.sum(models.InvoiceItem.vit_canti * models.InvoiceItem.vit_precio).label('total_gs')
                ).join(models.Invoice, models.Invoice.ven_numero == models.InvoiceItem.vit_numero)\
                 .join(models.Product, models.Product.art_codigo == models.InvoiceItem.vit_articu)\
                 .group_by(models.Product.art_descri)\
                 .order_by(func.sum(models.InvoiceItem.vit_canti).desc())\
                 .limit(5).all()

            if hasattr(self, 'table_top_productos'):
                self.table_top_productos.setRowCount(len(top_query))
                for r_idx, row_data in enumerate(top_query):
                    desc_item = QTableWidgetItem(str(row_data[0])[:25])
                    cant_val = Decimal(str(row_data[1] or 0))
                    cant_item = QTableWidgetItem(format_stock_qty(cant_val))
                    cant_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    
                    total_val = Decimal(str(row_data[2] or 0))
                    tot_item = QTableWidgetItem(f"Gs. {total_val:,.0f}")
                    tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    
                    self.table_top_productos.setItem(r_idx, 0, desc_item)
                    self.table_top_productos.setItem(r_idx, 1, cant_item)
                    self.table_top_productos.setItem(r_idx, 2, tot_item)

            # 8. Monitor de Cajas Activas
            sesion_activa = db.query(models.CashSession).filter_by(status='OPEN').order_by(models.CashSession.id.desc()).first()
            if hasattr(self, 'lbl_caja_estado'):
                if sesion_activa:
                    cajero_nombre = sesion_activa.user.full_name if sesion_activa.user else "Cajero Principal"
                    hora_apertura = sesion_activa.opened_at.strftime("%H:%M") if sesion_activa.opened_at else "08:00"
                    self.lbl_caja_estado.setText(f"Caja 01: ABIERTA (Sesión #{sesion_activa.id})")
                    self.lbl_caja_detalle.setText(f"👤 {cajero_nombre} | Desde {hora_apertura}")
                    self.card_caja_status.setStyleSheet("background-color: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0; padding: 6px 10px;")
                else:
                    self.lbl_caja_estado.setText("Cajas: TODAS CERRADAS")
                    self.lbl_caja_detalle.setText("No hay turnos activos en este momento")
                    self.card_caja_status.setStyleSheet("background-color: #fef2f2; border-radius: 6px; border: 1px solid #fecaca; padding: 6px 10px;")

            if hasattr(self, 'lbl_lotes_info'):
                if lotes_proximos:
                    lines = []
                    for b in lotes_proximos:
                        dias = (b.fecha_vencimiento.date() - datetime.date.today()).days if b.fecha_vencimiento else 0
                        prod_nom = b.product.art_descri[:18] if b.product else "Ítem"
                        lines.append(f"• Lote {b.lote}: {prod_nom} ({dias}d restantes)")
                    self.lbl_lotes_info.setText("\n".join(lines))
                    self.lbl_lotes_info.setStyleSheet("color: #b91c1c; background-color: #fef2f2; padding: 6px; border-radius: 4px; border: 1px solid #fecaca; font-size: 11px;")
                else:
                    self.lbl_lotes_info.setText("✅ Todos los lotes en regla (sin vencimientos en < 7 días).")
                    self.lbl_lotes_info.setStyleSheet("color: #15803d; background-color: #f0fdf4; padding: 6px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 11px;")

        except Exception as e:
            print(f"Error cargando KPIs en dashboard enriquecido: {e}")
        finally:
            db.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F1:
            self.abrir_pos()
        elif event.key() == Qt.Key.Key_F2:
            self.abrir_usuarios()
        elif event.key() == Qt.Key.Key_F3:
            self.abrir_etiquetas()
        elif event.key() == Qt.Key.Key_F4:
            self.abrir_mermas()
        elif event.key() == Qt.Key.Key_F5:
            self.refresh_dashboard_data()
        elif event.key() == Qt.Key.Key_F6:
            self.abrir_hechauka()
        else:
            super().keyPressEvent(event)

    def cambiar_modulo(self, row_idx):
        """Maneja el cambio de módulo desde el menú lateral."""
        HANDLERS = {
            0: self.refresh_dashboard_data,
            1: self.abrir_productos,
            2: self.abrir_precios,
            3: self.abrir_compras,
            4: self.abrir_lotes,
            5: self.abrir_cuentas_corrientes,
            6: self.abrir_clientes,
            7: self.abrir_auditoria_caja,
            8: self.abrir_configuracion,
            9: self.abrir_usuarios,
            10: self.abrir_mermas,
            11: self.abrir_hechauka,
            12: self.abrir_etiquetas,
        }
        fn = HANDLERS.get(row_idx)
        if fn:
            fn()
