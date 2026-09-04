from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QHBoxLayout, QHeaderView
from PyQt6.QtCore import Qt
from database import SessionLocal
import models

class ProductSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Búsqueda de Artículos")
        self.resize(700, 450)
        
        self.selected_product = None
        
        layout = QVBoxLayout(self)
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por descripción, código o código de barras...")
        self.txt_search.textChanged.connect(self.search_products)
        
        btn_search = QPushButton("Buscar")
        btn_search.clicked.connect(self.search_products)
        
        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)
        
        # Tabla de resultados
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción", "Precio (Gs)", "Stock", "IVA %"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.select_product)
        layout.addWidget(self.table)
        
        # Cargar todos al inicio
        self.search_products()
        
    def search_products(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        products = db.query(models.Product).filter(
            (models.Product.art_descri.ilike(f"%{query_text}%")) |
            (models.Product.art_codigo.ilike(f"%{query_text}%")) |
            (models.Product.art_cbarra.ilike(f"%{query_text}%"))
        ).limit(50).all()
        
        self.table.setRowCount(0)
        for row, prod in enumerate(products):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(prod.art_codigo))
            self.table.setItem(row, 1, QTableWidgetItem(prod.art_descri))
            self.table.setItem(row, 2, QTableWidgetItem(f"{prod.art_preven:,.0f}"))
            self.table.setItem(row, 3, QTableWidgetItem(str(prod.art_stkini)))
            self.table.setItem(row, 4, QTableWidgetItem(str(prod.art_impu)))
            
            # Guardamos el objeto producto en el ítem
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, prod)
            
        db.close()
        
    def select_product(self, item):
        row = item.row()
        product = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_product = product
        self.accept()
