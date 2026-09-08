import re

with open("ui/admin_window.py", "r", encoding="utf-8") as f:
    content = f.read()

new_ui = """
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
        header.setStyleSheet(\"\"\"
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d1b2a, stop:1 #1b263b);
                border-bottom: 2px solid #415a77;
            }
        \"\"\")
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
        self.btn_open_pos.setStyleSheet(\"\"\"
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
        \"\"\")
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
        self.btn_logout.setStyleSheet(\"\"\"
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
        \"\"\")
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

        top_bar.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizar Datos")
        self.btn_refresh.setStyleSheet(\"\"\"
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
        \"\"\")
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
        self.table_ventas_recientes.setStyleSheet(\"\"\"
            QTableWidget {
                background-color: white; border: 1px solid #e2e8f0; border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #f8fafc; font-weight: bold; border: none; padding: 6px;
            }
        \"\"\")
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
        card.setStyleSheet(f\"\"\"
            QFrame {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            QFrame:hover {{
                border: 1px solid {color};
                background-color: #f8fafc;
            }}
        \"\"\")
        
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
            btn.setStyleSheet(\"\"\"
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
            \"\"\")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if callback:
                btn.clicked.connect(callback)
            layout.addWidget(btn)
            
        layout.addStretch()
        return card
"""

pattern = re.compile(r"    def init_ui\(self\):.*?    def _crear_kpi_card", re.DOTALL)
new_content = pattern.sub(new_ui + "\n    def _crear_kpi_card", content)

# Remove the cambiar_modulo method entirely since list_menu doesn't exist.
pattern2 = re.compile(r"    def cambiar_modulo\(self, row.*?\n\n    def", re.DOTALL)
new_content = pattern2.sub("    def", new_content)

with open("ui/admin_window.py", "w", encoding="utf-8") as f:
    f.write(new_content)
print("Patch aplicado con exito.")
