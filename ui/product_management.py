from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QFormLayout, 
                             QHeaderView, QMessageBox, QGroupBox, QSplitter)
from PyQt6.QtCore import Qt
from database import SessionLocal
import models

class ProductManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Artículos (ABM)")
        self.resize(900, 500)
        
        self.current_product_id = None
        
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- PANEL IZQUIERDO: Buscador y Lista ---
        left_widget = QGroupBox("Lista de Artículos")
        left_layout = QVBoxLayout(left_widget)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por código o descripción...")
        self.txt_search.textChanged.connect(self.load_products)
        left_layout.addWidget(self.txt_search)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción", "Precio"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.table)
        
        # --- PANEL DERECHO: Ficha de Producto ---
        right_widget = QGroupBox("Ficha de Artículo")
        right_layout = QVBoxLayout(right_widget)
        
        form_layout = QFormLayout()
        
        self.txt_codigo = QLineEdit()
        self.txt_cbarra = QLineEdit()
        self.txt_descri = QLineEdit()
        self.txt_costo = QLineEdit()
        self.txt_preven = QLineEdit()
        self.txt_impu = QLineEdit("10.0")
        self.txt_stkini = QLineEdit("0")
        
        form_layout.addRow("Código (*):", self.txt_codigo)
        form_layout.addRow("Cód. Barras:", self.txt_cbarra)
        form_layout.addRow("Descripción (*):", self.txt_descri)
        form_layout.addRow("Costo Base:", self.txt_costo)
        form_layout.addRow("Precio de Venta:", self.txt_preven)
        form_layout.addRow("IVA (%):", self.txt_impu)
        form_layout.addRow("Stock Inicial:", self.txt_stkini)
        
        right_layout.addLayout(form_layout)
        
        # Botones de Acción
        btn_layout = QHBoxLayout()
        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.clear_form)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.save_product)
        
        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.setStyleSheet("background-color: darkred; color: white;")
        btn_eliminar.clicked.connect(self.delete_product)
        
        btn_layout.addWidget(btn_nuevo)
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_eliminar)
        
        right_layout.addStretch()
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        
        main_layout.addWidget(splitter)
        
        self.load_products()
        
    def load_products(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        products = db.query(models.Product).filter(
            (models.Product.art_descri.ilike(f"%{query_text}%")) |
            (models.Product.art_codigo.ilike(f"%{query_text}%"))
        ).limit(100).all()
        
        self.table.setRowCount(0)
        for row, prod in enumerate(products):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(prod.art_codigo))
            self.table.setItem(row, 1, QTableWidgetItem(prod.art_descri))
            self.table.setItem(row, 2, QTableWidgetItem(f"{prod.art_preven:,.0f}"))
            
            # Guardar el ID oculto
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, prod.id)
            
        db.close()
        
    def on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        product_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        db = SessionLocal()
        prod = db.query(models.Product).filter_by(id=product_id).first()
        if prod:
            self.current_product_id = prod.id
            self.txt_codigo.setText(prod.art_codigo)
            self.txt_cbarra.setText(prod.art_cbarra)
            self.txt_descri.setText(prod.art_descri)
            self.txt_costo.setText(str(prod.art_costo))
            self.txt_preven.setText(str(prod.art_preven))
            self.txt_impu.setText(str(prod.art_impu))
            self.txt_stkini.setText(str(prod.art_stkini))
            
            self.txt_codigo.setReadOnly(True) # No editar código una vez creado
        db.close()
        
    def clear_form(self):
        self.current_product_id = None
        self.txt_codigo.clear()
        self.txt_codigo.setReadOnly(False)
        self.txt_cbarra.clear()
        self.txt_descri.clear()
        self.txt_costo.setText("0")
        self.txt_preven.setText("0")
        self.txt_impu.setText("10.0")
        self.txt_stkini.setText("0")
        self.txt_codigo.setFocus()
        
    def save_product(self):
        codigo = self.txt_codigo.text().strip()
        descri = self.txt_descri.text().strip()
        
        if not codigo or not descri:
            QMessageBox.warning(self, "Error", "El Código y la Descripción son obligatorios.")
            return
            
        db = SessionLocal()
        try:
            if self.current_product_id:
                # Actualizar
                prod = db.query(models.Product).filter_by(id=self.current_product_id).first()
                if not prod:
                    raise Exception("No se encontró el producto.")
            else:
                # Verificar que el código no exista
                existente = db.query(models.Product).filter_by(art_codigo=codigo).first()
                if existente:
                    QMessageBox.warning(self, "Error", "El código de producto ya existe.")
                    return
                # Crear nuevo
                prod = models.Product()
                prod.art_codigo = codigo
                db.add(prod)
                
            prod.art_cbarra = self.txt_cbarra.text()
            prod.art_descri = descri
            prod.art_costo = float(self.txt_costo.text() or 0)
            prod.art_preven = float(self.txt_preven.text() or 0)
            prod.art_impu = float(self.txt_impu.text() or 10.0)
            prod.art_stkini = int(self.txt_stkini.text() or 0)
            
            db.commit()
            QMessageBox.information(self, "Éxito", "Artículo guardado correctamente.")
            self.load_products()
        except ValueError:
            db.rollback()
            QMessageBox.warning(self, "Error", "Verifique que los montos numéricos sean válidos.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()
            
    def delete_product(self):
        if not self.current_product_id:
            return
            
        reply = QMessageBox.question(self, 'Confirmar', '¿Seguro que desea eliminar este artículo?', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db = SessionLocal()
            try:
                prod = db.query(models.Product).filter_by(id=self.current_product_id).first()
                if prod:
                    db.delete(prod)
                    db.commit()
                    self.clear_form()
                    self.load_products()
                    QMessageBox.information(self, "Éxito", "Artículo eliminado.")
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", "No se pudo eliminar el artículo. Es posible que tenga ventas asociadas.")
            finally:
                db.close()
