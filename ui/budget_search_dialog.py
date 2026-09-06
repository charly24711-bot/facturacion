from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QLineEdit, QPushButton, QComboBox, QLabel, QSplitter, QHeaderView,
    QMessageBox, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from decimal import Decimal
import datetime
from database import SessionLocal, strip_accents, format_stock_qty
from sqlalchemy import func
import models
from ui.budget_dialog import BudgetDialog

class NumericTableWidgetItem(QTableWidgetItem):
    """Permite ordenamiento numérico correcto (▲/▼) en QTableWidget."""
    def __init__(self, value, display_text=None):
        super().__init__(display_text if display_text is not None else str(value))
        try:
            self.numeric_val = Decimal(str(value).replace(',', '').replace(' ', ''))
        except Exception:
            self.numeric_val = Decimal('0')

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_val < other.numeric_val
        return super().__lt__(other)


class BudgetSearchDialog(QDialog):
    """
    Diálogo para buscar, consultar y cargar presupuestos pendientes [F5]
    hacia la grilla de ventas activa.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar y Cargar Presupuestos [F5]")
        self.resize(850, 580)
        
        self.selected_budget = None
        self.selected_budget_id = None
        
        self.setup_ui()
        self.search_budgets()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # Filtros superiores
        filter_layout = QHBoxLayout()
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por Nº de presupuesto, cliente o RUC...")
        self.txt_search.textChanged.connect(self.search_budgets)
        
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Solo PENDIENTES", "Todos los Estados", "FACTURADOS", "ANULADOS"])
        self.combo_estado.currentIndexChanged.connect(self.search_budgets)
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.search_budgets)
        
        filter_layout.addWidget(QLabel("Filtrar:"))
        filter_layout.addWidget(self.txt_search, stretch=2)
        filter_layout.addWidget(QLabel("Estado:"))
        filter_layout.addWidget(self.combo_estado, stretch=1)
        filter_layout.addWidget(btn_refresh)
        main_layout.addLayout(filter_layout)
        
        # Splitter vertical: Lista de Presupuestos (Arriba) y Detalle de Ítems (Abajo)
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Tabla Principal de Presupuestos
        table_container = QGroupBox("Presupuestos Registrados")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(6, 6, 6, 6)
        
        self.table_budgets = QTableWidget(0, 7)
        self.table_budgets.setHorizontalHeaderLabels([
            "Nº Presupuesto", "Fecha", "Válido Hasta", "Cliente", "Total PYG", "Total USD", "Estado"
        ])
        self.table_budgets.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_budgets.horizontalHeader().setSectionsClickable(True)
        self.table_budgets.horizontalHeader().setSortIndicatorShown(True)
        self.table_budgets.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_budgets.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_budgets.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_budgets.itemSelectionChanged.connect(self.on_budget_selected)
        self.table_budgets.itemDoubleClicked.connect(self.cargar_al_carrito)
        table_layout.addWidget(self.table_budgets)
        splitter.addWidget(table_container)
        
        # Detalle de Ítems del Presupuesto Seleccionado
        detail_container = QGroupBox("Detalle de Artículos del Presupuesto")
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(6, 6, 6, 6)
        
        self.table_items = QTableWidget(0, 6)
        self.table_items.setHorizontalHeaderLabels([
            "Código", "Descripción", "Cantidad", "Precio Unitario", "IVA %", "Subtotal Gs."
        ])
        self.table_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        detail_layout.addWidget(self.table_items)
        splitter.addWidget(detail_container)
        
        splitter.setSizes([320, 180])
        main_layout.addWidget(splitter, stretch=1)
        
        # Botones de Acción
        btn_layout = QHBoxLayout()
        
        self.btn_cargar = QPushButton("📥 Cargar al Carrito de Venta [Enter]")
        self.btn_cargar.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_cargar.clicked.connect(self.cargar_al_carrito)
        
        self.btn_ver = QPushButton("👁️ Ver / Imprimir Presupuesto")
        self.btn_ver.setStyleSheet("""
            QPushButton {
                background-color: #0288d1;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0277bd;
            }
        """)
        self.btn_ver.clicked.connect(self.ver_presupuesto)
        
        self.btn_cancelar = QPushButton("Cerrar [Esc]")
        self.btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        self.btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cargar)
        btn_layout.addWidget(self.btn_ver)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        main_layout.addLayout(btn_layout)
        
    def search_budgets(self):
        query_text = self.txt_search.text().strip()
        filtro_estado = self.combo_estado.currentText()
        
        db = SessionLocal()
        try:
            q = db.query(models.Budget)
            
            # Filtro por estado
            if filtro_estado == "Solo PENDIENTES":
                q = q.filter(models.Budget.estado == 'PENDIENTE')
            elif filtro_estado == "FACTURADOS":
                q = q.filter(models.Budget.estado == 'FACTURADO')
            elif filtro_estado == "ANULADOS":
                q = q.filter(models.Budget.estado == 'ANULADO')
                
            # Filtro por texto
            if query_text:
                q = q.filter(
                    (models.Budget.numero.like(f"%{query_text}%")) |
                    (models.Budget.cliente_nombre.like(f"%{query_text}%")) |
                    (models.Budget.cliente_ruc.like(f"%{query_text}%")) |
                    (models.Budget.codcli.like(f"%{query_text}%"))
                )
                
            budgets = q.order_by(models.Budget.id.desc()).all()
            
            self.table_budgets.setSortingEnabled(False)
            self.table_budgets.setRowCount(len(budgets))
            
            for row, b in enumerate(budgets):
                # Nº Presupuesto
                item_nro = QTableWidgetItem(b.numero or f"PRES-{b.id:06d}")
                item_nro.setData(Qt.ItemDataRole.UserRole, b.id)
                self.table_budgets.setItem(row, 0, item_nro)
                
                # Fecha
                f_str = b.fecha.strftime("%d/%m/%Y %H:%M") if b.fecha else ""
                self.table_budgets.setItem(row, 1, QTableWidgetItem(f_str))
                
                # Válido Hasta
                v_str = ""
                if b.fecha:
                    venc = b.fecha + datetime.timedelta(days=b.validez_dias or 15)
                    v_str = venc.strftime("%d/%m/%Y")
                self.table_budgets.setItem(row, 2, QTableWidgetItem(v_str))
                
                # Cliente
                cli_info = f"{b.codcli or ''} - {b.cliente_nombre or ''}".strip(" -")
                self.table_budgets.setItem(row, 3, QTableWidgetItem(cli_info))
                
                # Total PYG
                tot_pyg = b.total_pyg or Decimal('0')
                item_pyg = NumericTableWidgetItem(tot_pyg, f"₲ {tot_pyg:,.0f}".replace(",", "."))
                item_pyg.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_budgets.setItem(row, 4, item_pyg)
                
                # Total USD
                tot_usd = b.total_usd or Decimal('0.00')
                item_usd = NumericTableWidgetItem(tot_usd, f"${tot_usd:,.2f}")
                item_usd.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_budgets.setItem(row, 5, item_usd)
                
                # Estado
                item_est = QTableWidgetItem(b.estado)
                item_est.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                font_bold = QFont()
                font_bold.setBold(True)
                item_est.setFont(font_bold)
                if b.estado == 'PENDIENTE':
                    item_est.setForeground(QColor("#2e7d32"))
                elif b.estado == 'FACTURADO':
                    item_est.setForeground(QColor("#1565c0"))
                else:
                    item_est.setForeground(QColor("#c62828"))
                self.table_budgets.setItem(row, 6, item_est)
                
            self.table_budgets.setSortingEnabled(True)
            self.table_items.setRowCount(0)
            
            if len(budgets) > 0:
                self.table_budgets.selectRow(0)
                
        finally:
            db.close()
            
    def on_budget_selected(self):
        selected_rows = self.table_budgets.selectionModel().selectedRows()
        if not selected_rows:
            self.table_items.setRowCount(0)
            return
            
        row = selected_rows[0].row()
        item_0 = self.table_budgets.item(row, 0)
        if not item_0:
            return
            
        budget_id = item_0.data(Qt.ItemDataRole.UserRole)
        
        db = SessionLocal()
        try:
            items = db.query(models.BudgetItem).filter_by(budget_id=budget_id).all()
            self.table_items.setRowCount(len(items))
            for r, it in enumerate(items):
                self.table_items.setItem(r, 0, QTableWidgetItem(it.articu))
                
                desc = it.descripcion or (it.product.art_descri if it.product else "")
                self.table_items.setItem(r, 1, QTableWidgetItem(desc))
                
                canti_str = format_stock_qty(it.canti)
                it_canti = NumericTableWidgetItem(it.canti, canti_str)
                it_canti.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_items.setItem(r, 2, it_canti)
                
                it_pr = NumericTableWidgetItem(it.precio, f"{it.precio:,.0f}".replace(",", "."))
                it_pr.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_items.setItem(r, 3, it_pr)
                
                it_iva = QTableWidgetItem(f"{it.impuesto_porc}%")
                it_iva.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_items.setItem(r, 4, it_iva)
                
                it_sub = NumericTableWidgetItem(it.subtotal, f"{it.subtotal:,.0f}".replace(",", "."))
                it_sub.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_items.setItem(r, 5, it_sub)
        finally:
            db.close()
            
    def ver_presupuesto(self):
        selected_rows = self.table_budgets.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Atención", "Seleccione un presupuesto de la lista.")
            return
            
        row = selected_rows[0].row()
        budget_id = self.table_budgets.item(row, 0).data(Qt.ItemDataRole.UserRole)
        dlg = BudgetDialog(budget_id, self)
        dlg.exec()
        
    def cargar_al_carrito(self):
        selected_rows = self.table_budgets.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Atención", "Seleccione un presupuesto para cargar.")
            return
            
        row = selected_rows[0].row()
        budget_id = self.table_budgets.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        db = SessionLocal()
        try:
            budget = db.query(models.Budget).filter_by(id=budget_id).first()
            if not budget:
                QMessageBox.critical(self, "Error", "El presupuesto no fue encontrado.")
                return
                
            if budget.estado == 'FACTURADO':
                reply = QMessageBox.question(
                    self, 
                    "Presupuesto Ya Facturado", 
                    f"El presupuesto {budget.numero} ya fue facturado anteriormente.\n\n¿Desea volver a cargarlo al carrito de todas formas?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            elif budget.estado == 'ANULADO':
                QMessageBox.warning(self, "Presupuesto Anulado", "No se puede cargar un presupuesto que ha sido anulado.")
                return
                
            self.selected_budget_id = budget.id
            self.selected_budget = {
                'id': budget.id,
                'numero': budget.numero or f"PRES-{budget.id:06d}",
                'codcli': budget.codcli,
                'cliente_nombre': budget.cliente_nombre,
                'cliente_ruc': budget.cliente_ruc,
                'items': [
                    {
                        'codigo': it.articu,
                        'descripcion': it.descripcion or (it.product.art_descri if it.product else "ARTICULO"),
                        'cantidad': it.canti,
                        'precio': it.precio,
                        'impuesto_porc': it.impuesto_porc,
                        'subtotal': it.subtotal
                    }
                    for it in budget.items
                ]
            }
            self.accept()
        finally:
            db.close()
            
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.cargar_al_carrito()
        elif event.key() == Qt.Key.Key_F5:
            self.cargar_al_carrito()
        else:
            super().keyPressEvent(event)
