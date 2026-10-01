"""
ui/touch_catalog_dialog.py - Catálogo Táctil para Góndolas, Balanzas y Productos sin Código
Interfaz táctil fullscreen / modal ergonómica con tarjetas visuales, selector de categorías
y pesaje integrado.
"""

from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QWidget, QFrame, QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QFont, QKeyEvent

from database import SessionLocal, resolve_image_path, format_stock_qty
import models
from ui.touch_numpad_dialog import TouchQuantityDialog
from utils.scale_driver import MockScaleDriver, BaseScaleDriver


class TouchProductCard(QFrame):
    """Tarjeta táctil individual de producto."""
    clicked = pyqtSignal(object)  # Emite el modelo Product

    def __init__(self, product: models.Product, parent=None):
        super().__init__(parent)
        self.product = product
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(160, 175)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            TouchProductCard {
                background-color: #1a2333;
                border: 2px solid #2a3550;
                border-radius: 10px;
            }
            TouchProductCard:hover {
                background-color: #242f46;
                border: 2px solid #7aa2f7;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Imagen
        self.lbl_img = QLabel()
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img.setFixedHeight(80)
        self.lbl_img.setStyleSheet("background-color: #10141e; border-radius: 6px;")

        img_path = resolve_image_path(getattr(self.product, 'image_path', None), self.product.art_codigo)
        if img_path:
            pix = QPixmap(img_path)
            if not pix.isNull():
                self.lbl_img.setPixmap(pix.scaled(130, 75, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                self._set_placeholder_img()
        else:
            self._set_placeholder_img()

        layout.addWidget(self.lbl_img)

        # Descripción
        desc = self.product.art_descri or "Sin Descripción"
        if len(desc) > 28:
            desc = desc[:26] + "..."
        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet("font-size: 11px; font-weight: bold; color: #e0e6ed; border: none; background: transparent;")
        layout.addWidget(lbl_desc)

        # Código PLU y Precio
        uom = getattr(self.product, 'uom', 'Un') or 'Un'
        price = getattr(self.product, 'art_preven', Decimal('0')) or Decimal('0')
        lbl_price = QLabel(f"₲ {price:,.0f} /{uom}".replace(",", "."))
        lbl_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_price.setStyleSheet("font-size: 13px; font-weight: bold; color: #9ece6a; border: none; background: transparent;")
        layout.addWidget(lbl_price)

    def _set_placeholder_img(self):
        uom = getattr(self.product, 'uom', 'Un') or 'Un'
        icon = "⚖️" if uom.lower() == "kg" else "📦"
        self.lbl_img.setText(icon)
        self.lbl_img.setStyleSheet("font-size: 28px; background-color: #10141e; border-radius: 6px; color: #7aa2f7;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.product)
        super().mousePressEvent(event)


class TouchCatalogDialog(QDialog):
    """Diálogo principal del Catálogo Táctil de Góndola y Balanza."""

    def __init__(self, scale_driver: BaseScaleDriver = None, parent=None):
        super().__init__(parent)
        self.scale_driver = scale_driver or MockScaleDriver()
        self.selected_product = None
        self.selected_quantity = Decimal('1.000')

        self.setWindowTitle("Catálogo Táctil de Góndola y Balanza")
        self.resize(1024, 700)
        self.setMinimumSize(850, 600)

        self._init_ui()
        self._load_products()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1117;
                color: #a9b1d6;
                font-family: 'Segoe UI', Arial;
            }
            QLabel {
                color: #e0e6ed;
            }
            QLineEdit {
                background-color: #131929;
                border: 2px solid #2a3550;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 16px;
                font-weight: bold;
                color: #9ece6a;
            }
            QLineEdit:focus {
                border-color: #7aa2f7;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 15)
        main_layout.setSpacing(12)

        # --- BARRA SUPERIOR ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        lbl_title = QLabel("🖐️ Catálogo Táctil de Góndola")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #7aa2f7;")
        top_bar.addWidget(lbl_title)

        # Badge de Balanza en Vivo
        weight, stable = self.scale_driver.read_weight()
        weight_val = weight or Decimal('0.000')
        self.lbl_scale_status = QLabel(f"⚖️ Balanza: {weight_val:,.3f} Kg".replace(",", "."))
        self.lbl_scale_status.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                background-color: #1b382b;
                color: #06d6a0;
                padding: 6px 14px;
                border-radius: 6px;
                border: 1px solid #23654b;
            }
        """)
        top_bar.addWidget(self.lbl_scale_status)

        top_bar.addStretch()

        # Buscador Rápido
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar producto...")
        self.txt_search.setFixedWidth(280)
        self.txt_search.textChanged.connect(self._filter_products)
        top_bar.addWidget(self.txt_search)

        btn_close = QPushButton("✖ Salir [Esc]")
        btn_close.setFixedHeight(40)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #3b2020;
                color: #ff6b6b;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #702e2e;
                border-radius: 6px;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #4f2828; }
        """)
        btn_close.clicked.connect(self.reject)
        top_bar.addWidget(btn_close)

        main_layout.addLayout(top_bar)

        # --- SELECTOR DE CATEGORÍAS (TABS TÁCTILES) ---
        self.cat_bar_layout = QHBoxLayout()
        self.cat_bar_layout.setSpacing(8)
        self.category_group = QButtonGroup(self)

        categories = [
            ("⭐ Favoritos", None),
            ("🍎 Frutas & Verduras", "Frutas"),
            ("🥖 Panadería", "Panaderia"),
            ("🧀 Fiambrería", "Fiambreria"),
            ("🥩 Carnicería", "Carniceria"),
            ("🥤 Bebidas", "Bebidas"),
            ("📦 Todos", "ALL")
        ]

        for idx, (cat_name, cat_filter) in enumerate(categories):
            btn_cat = QPushButton(cat_name)
            btn_cat.setCheckable(True)
            btn_cat.setFixedHeight(45)
            btn_cat.setStyleSheet("""
                QPushButton {
                    background-color: #1c2333;
                    color: #a9b1d6;
                    font-size: 13px;
                    font-weight: bold;
                    border: 1px solid #2a3550;
                    border-radius: 8px;
                    padding: 0 14px;
                }
                QPushButton:hover {
                    background-color: #2a3550;
                    color: #ffffff;
                }
                QPushButton:checked {
                    background-color: #7aa2f7;
                    color: #0f1117;
                    border: 1px solid #9bb8f9;
                }
            """)
            if idx == 0:
                btn_cat.setChecked(True)

            btn_cat.clicked.connect(lambda checked, f=cat_filter: self._set_category_filter(f))
            self.category_group.addButton(btn_cat)
            self.cat_bar_layout.addWidget(btn_cat)

        self.cat_bar_layout.addStretch()
        main_layout.addLayout(self.cat_bar_layout)

        # --- ÁREA DE SCROLL CON GRILLA DE TARJETAS ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_area.setWidget(self.cards_container)

        main_layout.addWidget(self.scroll_area, stretch=1)

    def _load_products(self):
        db = SessionLocal()
        try:
            self.all_products = db.query(models.Product).filter(models.Product.is_active == True).all()
        finally:
            db.close()

        self._render_grid(self.all_products)

    def _set_category_filter(self, cat_filter: str):
        self.current_cat_filter = cat_filter
        self._filter_products(self.txt_search.text())

    def _filter_products(self, query: str = ""):
        filtered = self.all_products
        query = (query or "").strip().lower()

        # Filtro de texto
        if query:
            filtered = [
                p for p in filtered
                if query in (p.art_descri or "").lower() or query in (p.art_codigo or "").lower()
            ]

        # Filtro de categoría
        cat_f = getattr(self, 'current_cat_filter', None)
        if cat_f and cat_f != "ALL":
            cat_lower = cat_f.lower()
            keyword_map = {
                "frutas": ["fruta", "verdura", "banana", "manzana", "naranja", "tomate", "papa", "cebolla", "limon", "pera", "uva"],
                "panaderia": ["pan", "confiteria", "medialuna", "factura", "torta", "baguette", "bizcocho", "chipa", "galleta"],
                "fiambreria": ["fiambr", "queso", "jamon", "salame", "mortadela", "lacteo", "leche", "manteca", "yogurt"],
                "carniceria": ["carne", "asado", "costilla", "vacio", "pollo", "cerdo", "molida", "bife"],
                "bebidas": ["gaseosa", "coca", "pepsi", "agua", "jugo", "cerveza", "vino", "soda"]
            }
            keywords = keyword_map.get(cat_lower, [cat_lower])

            def match_cat(p):
                desc = (p.art_descri or "").lower()
                cat_name = (p.category.name if hasattr(p, 'category') and p.category else "").lower()
                for kw in keywords:
                    if kw in desc or kw in cat_name:
                        return True
                return False

            filtered = [p for p in filtered if match_cat(p)]

        self._render_grid(filtered)

    def _render_grid(self, products_list):
        # Limpiar grilla previa
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not products_list:
            lbl_empty = QLabel("No se encontraron productos en esta sección.")
            lbl_empty.setStyleSheet("font-size: 16px; color: #555e75; padding: 40px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(lbl_empty, 0, 0, 1, 4)
            return

        columns = 5
        for idx, prod in enumerate(products_list):
            card = TouchProductCard(prod)
            card.clicked.connect(self._on_product_clicked)
            row = idx // columns
            col = idx % columns
            self.cards_layout.addWidget(card, row, col)

    def _on_product_clicked(self, product: models.Product):
        """Maneja la selección de una tarjeta."""
        uom = (getattr(product, 'uom', 'Un') or 'Un').lower()
        is_frac = bool(getattr(product, 'is_fractional', False))

        weight, stable = self.scale_driver.read_weight()
        live_scale = weight or Decimal('0.000')

        if uom == 'kg' or is_frac:
            # Abrir selector numérico táctil / peso
            dialog = TouchQuantityDialog(
                product_name=product.art_descri,
                unit_price=product.art_preven or Decimal('0'),
                uom=getattr(product, 'uom', 'Kg'),
                initial_qty=live_scale if live_scale > Decimal('0') else Decimal('1.000'),
                live_scale_weight=live_scale,
                parent=self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.selected_product = product
                self.selected_quantity = dialog.get_quantity()
                self.accept()
        else:
            # Producto unitario simple: 1 unidad directa
            self.selected_product = product
            self.selected_quantity = Decimal('1.000')
            self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def get_selection(self):
        """Devuelve (Product, quantity: Decimal)"""
        return self.selected_product, self.selected_quantity
