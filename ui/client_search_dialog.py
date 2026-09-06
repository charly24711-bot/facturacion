from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QPushButton, QHBoxLayout, QHeaderView
from PyQt6.QtCore import Qt
from database import SessionLocal, strip_accents
from sqlalchemy import func
import models
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))
from ruc_validator.ruc_validator import obtener_contribuyente, formatear_ruc

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
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.itemDoubleClicked.connect(self.select_client)
        layout.addWidget(self.table)
        
        # Cargar todos al inicio
        self.search_clients()
        
    def search_clients(self):
        query_text = self.txt_search.text().strip()
        clean_text = strip_accents(query_text)
        db = SessionLocal()
        
        if clean_text:
            norm_ruc = formatear_ruc(query_text)
            ruc_term = norm_ruc if norm_ruc else query_text
            clients = db.query(models.Client).filter(
                (func.unaccent(models.Client.cli_nombre).like(f"%{clean_text}%")) |
                (models.Client.cli_codigo.like(f"%{query_text}%")) |
                (models.Client.cli_ruc.like(f"%{query_text}%")) |
                (models.Client.cli_ruc.like(f"%{ruc_term}%"))
            ).limit(50).all()
        else:
            clients = db.query(models.Client).limit(50).all()
        
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row, client in enumerate(clients):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(client.cli_codigo))
            self.table.setItem(row, 1, QTableWidgetItem(client.cli_nombre))
            self.table.setItem(row, 2, QTableWidgetItem(client.cli_ruc or ""))
            self.table.setItem(row, 3, QTableWidgetItem(f"{client.cli_limite or 0:,.0f}"))
            
            # Guardamos el objeto cliente en el ítem de la fila 0 para fácil acceso
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, client)
            
        # Si el usuario busca y hay término de búsqueda, consultar también el Padrón DNIT
        if clean_text and len(clean_text) >= 3:
            norm_ruc = formatear_ruc(query_text)
            ruc_base = norm_ruc.split('-')[0].strip() if norm_ruc else query_text.split('-')[0].strip()
            padron_contribuyentes = db.query(models.TaxpayerRegistry).filter(
                (models.TaxpayerRegistry.ruc == ruc_base) |
                (models.TaxpayerRegistry.ruc.like(f"%{ruc_base}%")) |
                (func.unaccent(models.TaxpayerRegistry.razon_social).like(f"%{clean_text}%"))
            ).limit(10).all()
            
            # Si se buscó un RUC o Cédula numérica y no está en los resultados locales, consultar online
            if ruc_base.isdigit() and len(ruc_base) >= 5:
                if not any(p.ruc == ruc_base for p in padron_contribuyentes):
                    contrib_online = obtener_contribuyente(db, ruc_base, auto_cache=True)
                    if contrib_online:
                        p_nuevo = db.query(models.TaxpayerRegistry).filter_by(ruc=contrib_online['ruc']).first()
                        if p_nuevo and p_nuevo not in padron_contribuyentes:
                            padron_contribuyentes.append(p_nuevo)
            
            rucs_ya_en_grilla = {str(c.cli_ruc).split('-')[0] for c in clients if c.cli_ruc}
            
            for p in padron_contribuyentes:
                if p.ruc in rucs_ya_en_grilla:
                    continue
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                item_cod = QTableWidgetItem("[+DNIT]")
                item_cod.setToolTip("Doble clic para registrar cliente al vuelo desde Padrón")
                self.table.setItem(row, 0, item_cod)
                
                item_nom = QTableWidgetItem(f"➕ {p.razon_social} (Padrón DNIT)")
                self.table.setItem(row, 1, item_nom)
                
                self.table.setItem(row, 2, QTableWidgetItem(f"{p.ruc}-{p.dv}"))
                self.table.setItem(row, 3, QTableWidgetItem("0"))
                
                self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, {
                    "is_padron": True,
                    "ruc": f"{p.ruc}-{p.dv}",
                    "nombre": p.razon_social
                })
            
        db.close()
        self.table.setSortingEnabled(True)
        
    def select_client(self, item):
        row = item.row()
        data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if isinstance(data, dict) and data.get("is_padron"):
            db = SessionLocal()
            try:
                # Generar código autoincremental de 6 dígitos
                codes = db.query(models.Client.cli_codigo).all()
                max_val = 0
                for (code,) in codes:
                    if code and str(code).strip().isdigit():
                        max_val = max(max_val, int(code.strip()))
                next_code = str(max_val + 1).zfill(6)
                
                nuevo_cli = models.Client(
                    cli_codigo=next_code,
                    cli_nombre=data["nombre"],
                    cli_ruc=data["ruc"]
                )
                db.add(nuevo_cli)
                db.commit()
                db.refresh(nuevo_cli)
                self.selected_client = nuevo_cli
            finally:
                db.close()
        else:
            self.selected_client = data
            
        self.accept()
