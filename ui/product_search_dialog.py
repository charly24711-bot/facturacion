from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QLineEdit, QPushButton, QHBoxLayout, QHeaderView,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle, QApplication,
    QGroupBox, QLabel, QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap, QIcon
from decimal import Decimal
from database import SessionLocal, format_stock_qty, format_iva_rate, resolve_image_path, _safe_dec
import models

class StockItemDelegate(QStyledItemDelegate):
    """
    Delegado para la columna de stock que garantiza que el stock negativo
    se pinte SIEMPRE en color rojo y negrita, tanto cuando la fila está
    seleccionada (resaltada en azul) como cuando no está seleccionada.
    """
    def paint(self, painter, option, index):
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "").strip()
        is_negative = text.startswith('-')
        
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        if is_negative:
            opt.text = ""
            style = opt.widget.style() if opt.widget else QApplication.style()
            
            is_selected = bool(opt.state & QStyle.StateFlag.State_Selected)
            if not is_selected:
                painter.fillRect(option.rect, QColor("#ffebee"))
                
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
            
            painter.save()
            font = opt.font
            font.setBold(True)
            painter.setFont(font)
            
            # En selección (fondo azul): rojo brillante #ff5252 para máximo contraste
            # Sin selección (fondo claro): rojo carmesí #c62828
            color_rojo = QColor("#ff5252") if is_selected else QColor("#c62828")
            painter.setPen(color_rojo)
            
            text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
            text_rect.adjust(0, 0, -6, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
            painter.restore()
        else:
            super().paint(painter, option, index)

class NumericTableWidgetItem(QTableWidgetItem):
    """
    QTableWidgetItem que preserva el texto formateado (ej. '15,860', '-8', '5%')
    pero se ordena en base al valor numérico real (Decimal o float).
    """
    def __init__(self, display_text: str, sort_value, icon=None):
        if icon:
            super().__init__(icon, display_text)
        else:
            super().__init__(display_text)
        self.sort_value = sort_value

    def __lt__(self, other):
        if hasattr(other, 'sort_value'):
            return self.sort_value < other.sort_value
        return super().__lt__(other)

class ProductSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Búsqueda de Artículos [F2 / F4]")
        self.resize(880, 520)
        
        self.selected_product = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por descripción, código o código de barras...")
        self.txt_search.textChanged.connect(self.search_products)
        
        btn_search = QPushButton("Buscar")
        btn_search.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        btn_search.clicked.connect(self.search_products)
        
        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(btn_search)
        main_layout.addLayout(search_layout)
        
        # Contenedor central dividido: Tabla (Izquierda) y Tarjeta de Foto (Derecha)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # Tabla de resultados
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción del Artículo", "Precio (Gs)", "Stock", "IVA %"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setIconSize(QSize(28, 28))
        self.table.setItemDelegateForColumn(3, StockItemDelegate(self.table))
        self.table.itemSelectionChanged.connect(self.update_preview)
        self.table.itemDoubleClicked.connect(self.select_product)
        content_layout.addWidget(self.table, stretch=3)
        
        # Panel lateral con foto grande del producto seleccionado
        self.preview_group = QGroupBox("Foto del Producto")
        self.preview_group.setFixedWidth(240)
        preview_layout = QVBoxLayout(self.preview_group)
        preview_layout.setContentsMargins(8, 12, 8, 8)
        preview_layout.setSpacing(6)
        
        self.lbl_preview_img = QLabel("📷\nSin Imagen")
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; color: #888;")
        self.lbl_preview_img.setFixedHeight(170)
        self.lbl_preview_img.setFont(QFont("Segoe UI Emoji", 24))
        preview_layout.addWidget(self.lbl_preview_img)
        
        self.lbl_preview_descri = QLabel("Seleccione un producto")
        self.lbl_preview_descri.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.lbl_preview_descri.setWordWrap(True)
        preview_layout.addWidget(self.lbl_preview_descri)
        
        self.lbl_preview_codigo = QLabel("Código: -")
        self.lbl_preview_codigo.setFont(QFont("Arial", 10))
        preview_layout.addWidget(self.lbl_preview_codigo)
        
        self.lbl_preview_precio = QLabel("Precio: -")
        self.lbl_preview_precio.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.lbl_preview_precio.setStyleSheet("color: #2e7d32;")
        preview_layout.addWidget(self.lbl_preview_precio)
        
        self.lbl_preview_stock = QLabel("Stock: -")
        self.lbl_preview_stock.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        preview_layout.addWidget(self.lbl_preview_stock)
        
        preview_layout.addStretch()
        
        self.btn_select = QPushButton("✔ Seleccionar [Enter]")
        self.btn_select.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_select.clicked.connect(self.select_current_row)
        preview_layout.addWidget(self.btn_select)
        
        content_layout.addWidget(self.preview_group, stretch=1)
        main_layout.addLayout(content_layout, stretch=1)
        
        # Cargar todos al inicio
        self.search_products()
        
    def search_products(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        products = db.query(models.Product).filter(
            models.Product.is_active == True,
            ((models.Product.art_descri.ilike(f"%{query_text}%")) |
            (models.Product.art_codigo.ilike(f"%{query_text}%")) |
            (models.Product.art_cbarra.ilike(f"%{query_text}%")))
        ).limit(100).all()
        
        # Deshabilitar ordenamiento mientras se llena para máxima velocidad
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for row, prod in enumerate(products):
            self.table.insertRow(row)
            
            # 0. Código
            self.table.setItem(row, 0, QTableWidgetItem(prod.art_codigo))
            
            # 1. Descripción con Thumbnail Icon
            img_path = resolve_image_path(prod.image_path, prod.art_codigo)
            if img_path:
                item_desc = QTableWidgetItem(QIcon(img_path), prod.art_descri)
            else:
                item_desc = QTableWidgetItem(prod.art_descri)
            self.table.setItem(row, 1, item_desc)
            
            # 2. Precio (Gs) - Orden numérico
            precio_val = Decimal(str(prod.art_preven or 0))
            item_preven = NumericTableWidgetItem(f"{precio_val:,.0f}".replace(",", "."), precio_val)
            item_preven.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, item_preven)
            
            # 3. Stock - Orden numérico
            stock_val = Decimal(str(prod.art_stkini or 0))
            item_stock = NumericTableWidgetItem(format_stock_qty(prod.art_stkini), stock_val)
            item_stock.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, item_stock)
            
            # 4. IVA % - Orden numérico
            iva_val = Decimal(str(prod.art_impu or 10))
            item_iva = NumericTableWidgetItem(format_iva_rate(prod.art_impu), iva_val)
            item_iva.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, item_iva)
            
            # Guardamos el objeto producto en el ítem de la columna 0
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, prod)
            
        db.close()
        
        # Habilitar ordenamiento interactivo por cabecera
        self.table.setSortingEnabled(True)
        
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.update_preview()
            
    def update_preview(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            self.lbl_preview_descri.setText("Seleccione un producto")
            self.lbl_preview_codigo.setText("Código: -")
            self.lbl_preview_precio.setText("Precio: -")
            self.lbl_preview_stock.setText("Stock: -")
            self.lbl_preview_img.clear()
            self.lbl_preview_img.setText("📷\nSin Imagen")
            return
            
        row = selected[0].row()
        item_0 = self.table.item(row, 0)
        if not item_0:
            return
            
        prod = item_0.data(Qt.ItemDataRole.UserRole)
        if prod:
            self.lbl_preview_descri.setText(prod.art_descri)
            self.lbl_preview_codigo.setText(f"Código: {prod.art_codigo} • EAN: {prod.art_cbarra or '-'}")
            self.lbl_preview_precio.setText(f"₲ {Decimal(str(prod.art_preven or 0)):,.0f}".replace(",", "."))
            stk_str = format_stock_qty(prod.art_stkini)
            self.lbl_preview_stock.setText(f"Stock: {stk_str}")
            if _safe_dec(prod.art_stkini or 0) < Decimal('0'):
                self.lbl_preview_stock.setStyleSheet("color: #d32f2f; font-weight: bold;")
            else:
                self.lbl_preview_stock.setStyleSheet("color: #2e7d32; font-weight: bold;")
                
            img_path = resolve_image_path(prod.image_path, prod.art_codigo)
            if img_path:
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    self.lbl_preview_img.setPixmap(pixmap.scaled(
                        210, 160, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    ))
                else:
                    self.lbl_preview_img.clear()
                    self.lbl_preview_img.setText("📷\nSin Imagen")
            else:
                self.lbl_preview_img.clear()
                self.lbl_preview_img.setText("📷\nSin Imagen")
                
    def select_current_row(self):
        selected = self.table.selectionModel().selectedRows()
        if selected:
            row = selected[0].row()
            item_0 = self.table.item(row, 0)
            if item_0:
                self.selected_product = item_0.data(Qt.ItemDataRole.UserRole)
                self.accept()
                
    def select_product(self, item):
        row = item.row()
        product = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_product = product
        self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.select_current_row()
        else:
            super().keyPressEvent(event)
