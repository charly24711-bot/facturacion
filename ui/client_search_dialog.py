from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QHBoxLayout, QHeaderView
from PyQt6.QtCore import Qt
from database import SessionLocal
import models

class ClientSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Búsqueda de Clientes")
        self.resize(600, 400)
        
        self.selected_client = None
        
        layout = QVBoxLayout(self)
        
        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por nombre, código o RUC...")
        self.txt_search.textChanged.connect(self.search_clients)
        
        btn_search = QPushButton("Buscar")
        btn_search.clicked.connect(self.search_clients)
        
        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)
        
        # Tabla de resultados
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "RUC", "Límite Crédito"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.select_client)
        layout.addWidget(self.table)
        
        # Cargar todos al inicio
        self.search_clients()
        
    def search_clients(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        clients = db.query(models.Client).filter(
            (models.Client.cli_nombre.ilike(f"%{query_text}%")) |
            (models.Client.cli_codigo.ilike(f"%{query_text}%")) |
            (models.Client.cli_ruc.ilike(f"%{query_text}%"))
        ).limit(50).all()
        
        self.table.setRowCount(0)
        for row, client in enumerate(clients):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(client.cli_codigo))
            self.table.setItem(row, 1, QTableWidgetItem(client.cli_nombre))
            self.table.setItem(row, 2, QTableWidgetItem(client.cli_ruc))
            self.table.setItem(row, 3, QTableWidgetItem(f"{client.cli_limite:,.0f}"))
            
            # Guardamos el objeto cliente en el ítem de la fila 0 para fácil acceso
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, client)
            
        db.close()
        
    def select_client(self, item):
        row = item.row()
        client = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.selected_client = client
        self.accept()
