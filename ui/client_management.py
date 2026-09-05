from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QFormLayout, 
                             QHeaderView, QMessageBox, QGroupBox, QSplitter, QComboBox)
from PyQt6.QtCore import Qt
from database import SessionLocal
import models

class ClientManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Clientes (ABM)")
        self.resize(900, 500)
        
        self.current_client_id = None
        
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- PANEL IZQUIERDO: Buscador y Lista ---
        left_widget = QGroupBox("Lista de Clientes")
        left_layout = QVBoxLayout(left_widget)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por código, nombre o RUC...")
        self.txt_search.textChanged.connect(self.load_clients)
        left_layout.addWidget(self.txt_search)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "RUC"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.table)
        
        # --- PANEL DERECHO: Ficha de Cliente ---
        right_widget = QGroupBox("Ficha de Cliente")
        right_layout = QVBoxLayout(right_widget)
        
        form_layout = QFormLayout()
        
        self.txt_codigo = QLineEdit()
        self.txt_nombre = QLineEdit()
        self.txt_ruc = QLineEdit()
        self.txt_ci = QLineEdit()
        self.txt_direcc = QLineEdit()
        self.txt_telefo = QLineEdit()
        self.txt_limite = QLineEdit("0.0")
        
        self.cmb_price_list = QComboBox()
        self.cmb_price_list.addItem("— Sin Lista Especial —", None)
        self._load_price_lists()
        
        form_layout.addRow("Código (*):", self.txt_codigo)
        form_layout.addRow("Nombre (*):", self.txt_nombre)
        form_layout.addRow("RUC:", self.txt_ruc)
        form_layout.addRow("Cédula (CI):", self.txt_ci)
        form_layout.addRow("Dirección:", self.txt_direcc)
        form_layout.addRow("Teléfono:", self.txt_telefo)
        form_layout.addRow("Límite de Crédito (Gs):", self.txt_limite)
        form_layout.addRow("Lista de Precios:", self.cmb_price_list)
        
        right_layout.addLayout(form_layout)
        
        # Botones de Acción
        btn_layout = QHBoxLayout()
        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.clear_form)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.save_client)
        
        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.setStyleSheet("background-color: darkred; color: white;")
        btn_eliminar.clicked.connect(self.delete_client)
        
        btn_layout.addWidget(btn_nuevo)
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_eliminar)
        
        right_layout.addStretch()
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        
        main_layout.addWidget(splitter)
        
        self.load_clients()
        
    def _load_price_lists(self):
        db = SessionLocal()
        lists = db.query(models.PriceList).all()
        for lst in lists:
            self.cmb_price_list.addItem(lst.pl_nombre, lst.id)
        db.close()

    def load_clients(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        clients = db.query(models.Client).filter(
            (models.Client.cli_nombre.ilike(f"%{query_text}%")) |
            (models.Client.cli_codigo.ilike(f"%{query_text}%")) |
            (models.Client.cli_ruc.ilike(f"%{query_text}%"))
        ).limit(100).all()
        
        self.table.setRowCount(0)
        for row, cli in enumerate(clients):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(cli.cli_codigo))
            self.table.setItem(row, 1, QTableWidgetItem(cli.cli_nombre))
            self.table.setItem(row, 2, QTableWidgetItem(cli.cli_ruc or ""))
            
            # Guardar el ID oculto
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, cli.id)
            
        db.close()
        
    def on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        client_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        db = SessionLocal()
        cli = db.query(models.Client).filter_by(id=client_id).first()
        if cli:
            self.current_client_id = cli.id
            self.txt_codigo.setText(cli.cli_codigo)
            self.txt_nombre.setText(cli.cli_nombre)
            self.txt_ruc.setText(cli.cli_ruc)
            self.txt_ci.setText(cli.cli_ci)
            self.txt_direcc.setText(cli.cli_direcc)
            self.txt_telefo.setText(cli.cli_telefo)
            self.txt_limite.setText(str(cli.cli_limite))
            
            idx = self.cmb_price_list.findData(cli.price_list_id)
            if idx >= 0:
                self.cmb_price_list.setCurrentIndex(idx)
            else:
                self.cmb_price_list.setCurrentIndex(0)
            
            self.txt_codigo.setReadOnly(True)
        db.close()
        
    def clear_form(self):
        self.current_client_id = None
        self.txt_codigo.clear()
        self.txt_codigo.setReadOnly(False)
        self.txt_nombre.clear()
        self.txt_ruc.clear()
        self.txt_ci.clear()
        self.txt_direcc.clear()
        self.txt_telefo.clear()
        self.txt_limite.setText("0.0")
        self.cmb_price_list.setCurrentIndex(0)
        self.txt_codigo.setFocus()
        
    def save_client(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()
        
        if not codigo or not nombre:
            QMessageBox.warning(self, "Error", "El Código y el Nombre son obligatorios.")
            return
            
        db = SessionLocal()
        try:
            if self.current_client_id:
                # Actualizar
                cli = db.query(models.Client).filter_by(id=self.current_client_id).first()
                if not cli:
                    raise Exception("No se encontró el cliente.")
            else:
                # Verificar que el código no exista
                existente = db.query(models.Client).filter_by(cli_codigo=codigo).first()
                if existente:
                    QMessageBox.warning(self, "Error", "El código de cliente ya existe.")
                    return
                # Crear nuevo
                cli = models.Client()
                cli.cli_codigo = codigo
                db.add(cli)
                
            cli.cli_nombre = nombre
            cli.cli_ruc = self.txt_ruc.text()
            cli.cli_ci = self.txt_ci.text()
            cli.cli_direcc = self.txt_direcc.text()
            cli.cli_telefo = self.txt_telefo.text()
            cli.cli_limite = float(self.txt_limite.text() or 0.0)
            
            db.commit()
            QMessageBox.information(self, "Éxito", "Cliente guardado correctamente.")
            self.load_clients()
        except ValueError:
            db.rollback()
            QMessageBox.warning(self, "Error", "Verifique que el límite de crédito sea un número válido.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()
            
    def delete_client(self):
        if not self.current_client_id:
            return
            
        reply = QMessageBox.question(self, 'Confirmar', '¿Seguro que desea eliminar este cliente?', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db = SessionLocal()
            try:
                cli = db.query(models.Client).filter_by(id=self.current_client_id).first()
                if cli:
                    db.delete(cli)
                    db.commit()
                    self.clear_form()
                    self.load_clients()
                    QMessageBox.information(self, "Éxito", "Cliente eliminado.")
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", "No se pudo eliminar el cliente. Es posible que tenga facturas asociadas.")
            finally:
                db.close()
