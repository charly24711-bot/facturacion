import sys
import datetime
from decimal import Decimal
from sqlalchemy import func
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QStackedWidget, QMessageBox, QListWidget, QListWidgetItem
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
        
        self.setWindowTitle("Supermercado Central - Panel Administrativo & Gerencial")
        self.resize(1260, 800)
        self.setMinimumSize(1080, 680)
        
        self.init_ui()
        self.refresh_dashboard_data()

    def init_ui(self):
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

        lbl_title = QLabel("🏢 SUPERMERCADO CENTRAL  |  Panel Gerencial")
        lbl_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #e0e1dd; letter-spacing: 1px;")
        header_layout.addWidget(lbl_title)

        header_layout.addStretch()

        # Botón de acceso directo a POS (Caja)
        self.btn_open_pos = QPushButton("🛒 Punto de Venta (POS) [F1]")
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

        # ── 2. CUERPO PRINCIPAL (SIDEBAR + CONTENIDO) ──────────────────────────
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(8)

        lbl_menu = QLabel("MENÚ PRINCIPAL")
        lbl_menu.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        lbl_menu.setStyleSheet("color: #64748b; letter-spacing: 1px; padding: 4px 6px;")
        sidebar_layout.addWidget(lbl_menu)

        self.list_menu = QListWidget()
        self.list_menu.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #e2e8f0;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 3px;
            }
            QListWidget::item:hover {
                background-color: #1e293b;
                color: #38bdf8;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
            }
        """)

        menu_items = [
            ("📊 Dashboard General", 0),
            ("📦 Catálogo de Productos", 1),
            ("🏷️ Listas de Precios & Escalas", 2),
            ("🚚 Compras y Proveedores", 3),
            ("⏳ Control de Lotes FIFO", 4),
            ("💳 Cuentas Corrientes (Crédito)", 5),
            ("👥 Gestión de Clientes", 6),
            ("📑 Auditoría de Cajas (Z)", 7),
            ("⚙️ Configuración Fiscal DNIT", 8),
            # ─── FASE 2 ────────────────────────────────────────────────────
            ("🔑 Usuarios y Cajeros [F2]", 9),
            ("🗑️ Mermas y Ajustes Inv. [F4]", 10),
            ("📊 Exportar DNIT Hechauka [F6]", 11),
        ]

        for text, idx in menu_items:
            item = QListWidgetItem(text)
            item.setSizeHint(QSize(200, 38))
            self.list_menu.addItem(item)

        self.list_menu.setCurrentRow(0)
        self.list_menu.currentRowChanged.connect(self.cambiar_modulo)
        sidebar_layout.addWidget(self.list_menu)
        
        sidebar_layout.addStretch()
        
        # Versión y copyright
        lbl_version = QLabel("v2.6.0 | Triple Frontera\nReglas DNIT / SIFEN")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_version.setFont(QFont("Arial", 8))
        lbl_version.setStyleSheet("color: #475569; padding: 8px 0;")
        sidebar_layout.addWidget(lbl_version)

        body_layout.addWidget(sidebar)

        # Área de Contenido
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #f1f5f9;")
        self.content_layout = QVBoxLayout(content_area)
        self.content_layout.setContentsMargins(20, 16, 20, 16)

        # Vistas de Módulos (Stacked)
        self.stack = QStackedWidget()
        
        # 1. Vista Dashboard
        self.view_dashboard = self.crear_vista_dashboard()
        self.stack.addWidget(self.view_dashboard)

        self.content_layout.addWidget(self.stack)
        body_layout.addWidget(content_area, stretch=1)

        main_layout.addLayout(body_layout)

    # ── VISTA DASHBOARD ENRIQUECIDO ─────────────────────────────────────────────
    def crear_vista_dashboard(self):
        dash = QWidget()
        layout = QVBoxLayout(dash)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Barra superior con título y botón refrescar
        top_bar = QHBoxLayout()
        lbl_dash_title = QLabel("Resumen Ejecutivo de Operaciones")
        lbl_dash_title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        lbl_dash_title.setStyleSheet("color: #0f172a;")
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
                padding: 6px 14px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_dashboard_data)
        top_bar.addWidget(self.btn_refresh)
        layout.addLayout(top_bar)

        # ── 1. FILA DE 5 KPI CARDS ────────────────────────────────────────────
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)

        # Card 1: Ventas de Hoy
        self.card_ventas = self._crear_kpi_card("Ventas de Hoy", "Gs. 0", "#2563eb", "🛒 Total facturado")
        kpi_grid.addWidget(self.card_ventas, 0, 0)

        # Card 2: Facturas Emitidas
        self.card_tickets = self._crear_kpi_card("Comprobantes", "0", "#059669", "📄 Tickets y Facturas")
        kpi_grid.addWidget(self.card_tickets, 0, 1)

        # Card 3: Ticket Promedio
        self.card_ticket_prom = self._crear_kpi_card("Ticket Promedio", "Gs. 0", "#7c3aed", "📊 Gasto medio por cliente")
        kpi_grid.addWidget(self.card_ticket_prom, 0, 2)

        # Card 4: IVA Total Liquidado
        self.card_iva = self._crear_kpi_card("I.V.A. Liquidado", "Gs. 0", "#d97706", "⚖️ IVA 10% + IVA 5%")
        kpi_grid.addWidget(self.card_iva, 0, 3)

        # Card 5: Stock Crítico & Vencimientos
        self.card_stock = self._crear_kpi_card("Alertas Stock / FIFO", "0 ítems", "#dc2626", "⚠️ Stock <= 0 | Vence < 7d")
        kpi_grid.addWidget(self.card_stock, 0, 4)

        layout.addLayout(kpi_grid)

        # ── 2. BARRA DE COBROS MULTIDIVISA & MEDIOS DE PAGO (TRIPLE FRONTERA) ───
        strip_multidivisa = QFrame()
        strip_multidivisa.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                padding: 6px 12px;
            }
        """)
        strip_layout = QHBoxLayout(strip_multidivisa)
        strip_layout.setContentsMargins(8, 6, 8, 6)
        strip_layout.setSpacing(14)

        lbl_strip_tag = QLabel("💵 TESORERÍA DEL DÍA:")
        lbl_strip_tag.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        lbl_strip_tag.setStyleSheet("color: #475569; border: none;")
        strip_layout.addWidget(lbl_strip_tag)

        # Badges de monedas
        self.lbl_pay_pyg = QLabel("💵 Efectivo: Gs. 0")
        self.lbl_pay_pyg.setStyleSheet("background-color: #e8f5e9; color: #1b5e20; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
        strip_layout.addWidget(self.lbl_pay_pyg)

        self.lbl_pay_tarj = QLabel("💳 Tarjetas / POS: Gs. 0")
        self.lbl_pay_tarj.setStyleSheet("background-color: #e0f2fe; color: #0369a1; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
        strip_layout.addWidget(self.lbl_pay_tarj)

        self.lbl_pay_brl = QLabel("🇧🇷 BRL / PIX: R$ 0.00")
        self.lbl_pay_brl.setStyleSheet("background-color: #fef3c7; color: #b45309; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
        strip_layout.addWidget(self.lbl_pay_brl)

        self.lbl_pay_usd = QLabel("🇺🇸 USD: US$ 0.00")
        self.lbl_pay_usd.setStyleSheet("background-color: #f3e8ff; color: #6b21a8; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
        strip_layout.addWidget(self.lbl_pay_usd)

        self.lbl_pay_ars = QLabel("🇦🇷 ARS: $ 0")
        self.lbl_pay_ars.setStyleSheet("background-color: #f1f5f9; color: #334155; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
        strip_layout.addWidget(self.lbl_pay_ars)

        strip_layout.addStretch()
        layout.addWidget(strip_multidivisa)

        # ── 3. CUERPO CENTRAL (3 COLUMNAS: VENTAS, TOP PRODUCTOS, MONITOREO) ────
        split_layout = QHBoxLayout()
        split_layout.setSpacing(12)

        # ── COLUMNA 1: ÚLTIMAS VENTAS (Stretch 5) ──
        ventas_box = QFrame()
        ventas_box.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e2e8f0;")
        ventas_box_layout = QVBoxLayout(ventas_box)
        ventas_box_layout.setContentsMargins(14, 12, 14, 12)

        lbl_recientes = QLabel("📋 Últimas Ventas del Sistema")
        lbl_recientes.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_recientes.setStyleSheet("color: #1e293b; border: none;")
        ventas_box_layout.addWidget(lbl_recientes)

        self.table_ventas_recientes = QTableWidget()
        self.table_ventas_recientes.setColumnCount(5)
        self.table_ventas_recientes.setHorizontalHeaderLabels(["Nº Factura", "Fecha / Hora", "Cliente", "Total (Gs.)", "Estado"])
        self.table_ventas_recientes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_ventas_recientes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_ventas_recientes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_ventas_recientes.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #f1f5f9;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 6px;
            }
        """)
        self.table_ventas_recientes.itemClicked.connect(self.abrir_detalle_venta)
        self.table_ventas_recientes.itemDoubleClicked.connect(self.abrir_detalle_venta)
        ventas_box_layout.addWidget(self.table_ventas_recientes)

        lbl_hint = QLabel("💡 Haga clic sobre cualquier venta para abrir el detalle completo y ticket")
        lbl_hint.setFont(QFont("Arial", 8))
        lbl_hint.setStyleSheet("color: #64748b; font-style: italic; border: none; margin-top: 3px;")
        ventas_box_layout.addWidget(lbl_hint)

        split_layout.addWidget(ventas_box, stretch=4)

        # ── COLUMNA 2: TOP 5 ARTÍCULOS MÁS VENDIDOS (Stretch 3) ──
        top_box = QFrame()
        top_box.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e2e8f0;")
        top_box_layout = QVBoxLayout(top_box)
        top_box_layout.setContentsMargins(14, 12, 14, 12)

        lbl_top = QLabel("🔥 Top 5 Más Vendidos")
        lbl_top.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_top.setStyleSheet("color: #1e293b; border: none;")
        top_box_layout.addWidget(lbl_top)

        self.table_top_productos = QTableWidget()
        self.table_top_productos.setColumnCount(3)
        self.table_top_productos.setHorizontalHeaderLabels(["Artículo", "Cant.", "Total (Gs.)"])
        self.table_top_productos.setColumnWidth(0, 130)
        self.table_top_productos.setColumnWidth(1, 55)
        self.table_top_productos.setColumnWidth(2, 85)
        self.table_top_productos.horizontalHeader().setStretchLastSection(True)
        self.table_top_productos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_top_productos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_top_productos.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #f1f5f9;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 6px;
            }
        """)
        top_box_layout.addWidget(self.table_top_productos)
        split_layout.addWidget(top_box, stretch=3)

        # ── COLUMNA 3: MONITOR DE CAJAS & ACCESOS RÁPIDOS (Stretch 3) ──
        side_ops_box = QFrame()
        side_ops_box.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e2e8f0;")
        side_ops_layout = QVBoxLayout(side_ops_box)
        side_ops_layout.setContentsMargins(14, 12, 14, 12)
        side_ops_layout.setSpacing(10)

        # Monitor de caja
        lbl_caja_title = QLabel("🟢 Monitor de Cajas POS")
        lbl_caja_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl_caja_title.setStyleSheet("color: #1e293b; border: none;")
        side_ops_layout.addWidget(lbl_caja_title)

        self.card_caja_status = QFrame()
        self.card_caja_status.setStyleSheet("""
            QFrame {
                background-color: #f0fdf4;
                border-radius: 6px;
                border: 1px solid #bbf7d0;
                padding: 6px 10px;
            }
        """)
        caja_stat_layout = QVBoxLayout(self.card_caja_status)
        caja_stat_layout.setSpacing(2)
        caja_stat_layout.setContentsMargins(6, 4, 6, 4)
        
        self.lbl_caja_estado = QLabel("Caja 01: ABIERTA")
        self.lbl_caja_estado.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.lbl_caja_estado.setStyleSheet("color: #166534; border: none;")
        
        self.lbl_caja_detalle = QLabel("Sesión activa | Cajero Principal")
        self.lbl_caja_detalle.setFont(QFont("Arial", 8))
        self.lbl_caja_detalle.setStyleSheet("color: #15803d; border: none;")
        
        caja_stat_layout.addWidget(self.lbl_caja_estado)
        caja_stat_layout.addWidget(self.lbl_caja_detalle)
        side_ops_layout.addWidget(self.card_caja_status)

        # Alertas de Lotes Próximos a Vencer
        lbl_lotes_title = QLabel("⏳ Alertas FIFO (Próximos Vencimientos)")
        lbl_lotes_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_lotes_title.setStyleSheet("color: #1e293b; border: none; margin-top: 4px;")
        side_ops_layout.addWidget(lbl_lotes_title)

        self.lbl_lotes_info = QLabel("No hay lotes críticos en los próximos 7 días.")
        self.lbl_lotes_info.setFont(QFont("Arial", 8))
        self.lbl_lotes_info.setWordWrap(True)
        self.lbl_lotes_info.setStyleSheet("color: #64748b; background-color: #f8fafc; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0;")
        side_ops_layout.addWidget(self.lbl_lotes_info)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e2e8f0; margin: 2px 0;")
        side_ops_layout.addWidget(sep)

        # Botones de accesos operativos
        lbl_acciones = QLabel("⚡ Accesos Directos")
        lbl_acciones.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_acciones.setStyleSheet("color: #1e293b; border: none;")
        side_ops_layout.addWidget(lbl_acciones)

        btn_acc_prod = QPushButton("📦 Administrar Productos")
        btn_acc_prod.setStyleSheet(self._btn_style("#3b82f6"))
        btn_acc_prod.clicked.connect(self.abrir_productos)
        side_ops_layout.addWidget(btn_acc_prod)

        btn_acc_comp = QPushButton("🚚 Cargar Factura de Compra")
        btn_acc_comp.setStyleSheet(self._btn_style("#059669"))
        btn_acc_comp.clicked.connect(self.abrir_compras)
        side_ops_layout.addWidget(btn_acc_comp)

        btn_acc_lotes = QPushButton("⏳ Auditoría Lotes FIFO")
        btn_acc_lotes.setStyleSheet(self._btn_style("#d97706"))
        btn_acc_lotes.clicked.connect(self.abrir_lotes)
        side_ops_layout.addWidget(btn_acc_lotes)

        btn_acc_cc = QPushButton("💳 Cuentas Corrientes")
        btn_acc_cc.setStyleSheet(self._btn_style("#6366f1"))
        btn_acc_cc.clicked.connect(self.abrir_cuentas_corrientes)
        side_ops_layout.addWidget(btn_acc_cc)

        side_ops_layout.addStretch()
        split_layout.addWidget(side_ops_box, stretch=3)

        layout.addLayout(split_layout)
        return dash

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

    def cambiar_modulo(self, row):
        if row == 0:
            self.refresh_dashboard_data()
        elif row == 1:
            self.abrir_productos()
            self.list_menu.setCurrentRow(0)
        elif row == 2:
            self.abrir_precios()
            self.list_menu.setCurrentRow(0)
        elif row == 3:
            self.abrir_compras()
            self.list_menu.setCurrentRow(0)
        elif row == 4:
            self.abrir_lotes()
            self.list_menu.setCurrentRow(0)
        elif row == 5:
            self.abrir_cuentas_corrientes()
            self.list_menu.setCurrentRow(0)
        elif row == 6:
            self.abrir_clientes()
            self.list_menu.setCurrentRow(0)
        elif row == 7:
            self.abrir_auditoria_caja()
            self.list_menu.setCurrentRow(0)
        elif row == 8:
            self.abrir_configuracion()
            self.list_menu.setCurrentRow(0)

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

            # 9. Actualizar texto de lotes próximos a vencer
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
        }
        fn = HANDLERS.get(row_idx)
        if fn:
            fn()
