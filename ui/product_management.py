from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QFormLayout, 
                             QHeaderView, QMessageBox, QGroupBox, QSplitter, 
                             QTabWidget, QWidget, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt
from database import SessionLocal
import models

class ProductManagementDialog(QDialog):
    def auto_format_thousands(self, text, line_edit):
        if not text: return
        clean_text = text.replace(",", "").replace(".", "")
        if not clean_text.isdigit(): return
        
        formatted = f"{int(clean_text):,}"
        if line_edit.text() != formatted:
            cursor = line_edit.cursorPosition()
            old_len = len(line_edit.text())
            line_edit.blockSignals(True)
            line_edit.setText(formatted)
            line_edit.blockSignals(False)
            new_len = len(formatted)
            line_edit.setCursorPosition(cursor + (new_len - old_len))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Artículos (Supermercado)")
        self.resize(1000, 600)
        
        self.current_product_id = None
        self.current_image_path = None
        
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
        
        # --- PANEL DERECHO: Ficha de Producto (Tabs) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.tabs = QTabWidget()
        
        # TAB 1: General
        tab_general = QWidget()
        general_main_layout = QHBoxLayout(tab_general)
        
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        self.txt_codigo = QLineEdit()
        self.txt_cbarra = QLineEdit()
        self.txt_descri = QLineEdit()
        
        self.combo_cat = QComboBox()
        self.combo_brand = QComboBox()
        self.combo_uom = QComboBox()
        self.combo_uom.addItems(["Un", "Kg", "Lts", "Mts"])
        
        self.chk_fractional = QCheckBox("Permitir Venta Fraccionada (Decimales)")
        self.chk_active = QCheckBox("Producto Activo")
        self.chk_active.setChecked(True)
        
        self.txt_location = QLineEdit()
        self.txt_costo = QLineEdit()
        self.txt_costo.textChanged.connect(lambda t, le=self.txt_costo: self.auto_format_thousands(t, le))
        self.txt_preven = QLineEdit()
        self.txt_impu = QLineEdit("10.0")
        
        self.txt_stkmin = QLineEdit("10")
        self.txt_stkmax = QLineEdit("200")
        self.txt_stkini = QLineEdit("0")
        
        form_layout.addRow("Código Interno (*):", self.txt_codigo)
        form_layout.addRow("Cód. Barras Principal:", self.txt_cbarra)
        form_layout.addRow("Descripción (*):", self.txt_descri)
        form_layout.addRow("Categoría:", self.combo_cat)
        form_layout.addRow("Marca:", self.combo_brand)
        form_layout.addRow("Unidad de Medida:", self.combo_uom)
        form_layout.addRow("", self.chk_fractional)
        form_layout.addRow("Ubicación Física:", self.txt_location)
        form_layout.addRow("Costo Base:", self.txt_costo)
        form_layout.addRow("Precio de Venta:", self.txt_preven)
        form_layout.addRow("IVA (%):", self.txt_impu)
        form_layout.addRow("Stock Actual (Solo Ref.):", self.txt_stkini)
        form_layout.addRow("Stock Mínimo:", self.txt_stkmin)
        form_layout.addRow("Stock Máximo:", self.txt_stkmax)
        form_layout.addRow("", self.chk_active)
        
        photo_widget = QWidget()
        photo_layout = QVBoxLayout(photo_widget)
        
        from PyQt6.QtWidgets import QLabel
        self.lbl_product_photo = QLabel("Sin Foto")
        self.lbl_product_photo.setFixedSize(150, 150)
        self.lbl_product_photo.setStyleSheet("background-color: #eee; border: 1px solid #aaa;")
        self.lbl_product_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_take_photo = QPushButton("📸 Tomar Foto")
        self.btn_take_photo.clicked.connect(self.open_camera)
        
        photo_layout.addWidget(self.lbl_product_photo)
        photo_layout.addWidget(self.btn_take_photo)
        photo_layout.addStretch()
        
        general_main_layout.addWidget(form_widget, stretch=1)
        general_main_layout.addWidget(photo_widget)
        
        self.tabs.addTab(tab_general, "General")
        
        # TAB 2: Códigos de Barras Adicionales
        tab_barcodes = QWidget()
        barcode_layout = QVBoxLayout(tab_barcodes)
        self.table_barcodes = QTableWidget(0, 2)
        self.table_barcodes.setHorizontalHeaderLabels(["Código de Barras", "Factor (Ej. 6 si es pack)"])
        self.table_barcodes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        barcode_layout.addWidget(self.table_barcodes)
        # Nota: Por simplicidad visual, en esta versión no hacemos la UI compleja de edición de filas, solo lectura/vista.
        self.tabs.addTab(tab_barcodes, "Cód. Adicionales (Packs)")
        
        # TAB 3: Lotes
        tab_batches = QWidget()
        batch_layout = QVBoxLayout(tab_batches)
        self.table_batches = QTableWidget(0, 3)
        self.table_batches.setHorizontalHeaderLabels(["Lote", "Vencimiento", "Stock Disponible"])
        self.table_batches.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        batch_layout.addWidget(self.table_batches)
        self.tabs.addTab(tab_batches, "Lotes / Vencimientos")
        
        right_layout.addWidget(self.tabs)
        
        # Botones de Acción
        btn_layout = QHBoxLayout()
        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.clear_form)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.save_product)
        
        btn_layout.addWidget(btn_nuevo)
        btn_layout.addWidget(btn_guardar)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([350, 650])
        
        main_layout.addWidget(splitter)
        
        self.load_combos()
        self.load_products()
        
    def load_combos(self):
        db = SessionLocal()
        cats = db.query(models.Category).all()
        for c in cats:
            self.combo_cat.addItem(c.name, c.id)
            
        brands = db.query(models.Brand).all()
        for b in brands:
            self.combo_brand.addItem(b.name, b.id)
        db.close()
        
    def load_products(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        products = db.query(models.Product).filter(
            (models.Product.art_descri.ilike(f"%{query_text}%")) |
            (models.Product.art_codigo.ilike(f"%{query_text}%")) |
            (models.Product.art_cbarra.ilike(f"%{query_text}%"))
        ).limit(100).all()
        
        self.table.setRowCount(0)
        for row, prod in enumerate(products):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(prod.art_codigo))
            
            # Mostrar inactivos en gris
            descri_item = QTableWidgetItem(prod.art_descri)
            if not prod.is_active:
                descri_item.setText(f"(INACTIVO) {prod.art_descri}")
            
            self.table.setItem(row, 1, descri_item)
            self.table.setItem(row, 2, QTableWidgetItem(f"{prod.art_preven:,.0f}"))
            
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
            self.txt_cbarra.setText(prod.art_cbarra or "")
            self.txt_descri.setText(prod.art_descri)
            self.txt_costo.setText(f"{float(prod.art_costo):g}")
            self.txt_preven.setText(f"{float(prod.art_preven):.0f}")
            self.txt_impu.setText(f"{float(prod.art_impu):g}")
            self.txt_stkini.setText(str(prod.art_stkini))
            self.txt_stkmin.setText(str(prod.art_stkmin))
            self.txt_stkmax.setText(str(prod.art_stkmax))
            
            # Combos y Checkboxes
            if prod.category_id:
                idx = self.combo_cat.findData(prod.category_id)
                self.combo_cat.setCurrentIndex(idx)
            
            if prod.brand_id:
                idx = self.combo_brand.findData(prod.brand_id)
                self.combo_brand.setCurrentIndex(idx)
                
            self.combo_uom.setCurrentText(prod.uom)
            self.chk_fractional.setChecked(prod.is_fractional)
            self.chk_active.setChecked(prod.is_active)
            self.txt_location.setText(prod.location or "")
            
            self.txt_codigo.setReadOnly(True) 
            
            self.current_image_path = prod.image_path
            if prod.image_path:
                import os
                from PyQt6.QtGui import QPixmap
                if os.path.exists(prod.image_path):
                    pixmap = QPixmap(prod.image_path)
                    self.lbl_product_photo.setPixmap(pixmap.scaled(self.lbl_product_photo.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.lbl_product_photo.clear()
                    self.lbl_product_photo.setText("Sin Foto")
            else:
                self.lbl_product_photo.clear()
                self.lbl_product_photo.setText("Sin Foto")
            
            # Cargar Códigos Adicionales
            self.table_barcodes.setRowCount(0)
            for r, bc in enumerate(prod.barcodes):
                self.table_barcodes.insertRow(r)
                self.table_barcodes.setItem(r, 0, QTableWidgetItem(bc.barcode))
                self.table_barcodes.setItem(r, 1, QTableWidgetItem(f"{float(bc.factor_conversion or 0):g}"))
                
            # Cargar Lotes
            self.table_batches.setRowCount(0)
            for r, bt in enumerate(prod.batches):
                self.table_batches.insertRow(r)
                self.table_batches.setItem(r, 0, QTableWidgetItem(bt.lote))
                venc = bt.fecha_vencimiento.strftime("%d/%m/%Y") if bt.fecha_vencimiento else "Sin fecha"
                self.table_batches.setItem(r, 1, QTableWidgetItem(venc))
                self.table_batches.setItem(r, 2, QTableWidgetItem(f"{float(bt.stock_actual or 0):g}"))
                
        db.close()
        
    def clear_form(self):
        self.current_product_id = None
        self.current_image_path = None
        self.lbl_product_photo.clear()
        self.lbl_product_photo.setText("Sin Foto")
        
        self.txt_codigo.clear()
        self.txt_codigo.setReadOnly(False)
        self.txt_cbarra.clear()
        self.txt_descri.clear()
        self.txt_costo.setText("0")
        self.txt_preven.setText("0")
        self.txt_impu.setText("10.0")
        self.txt_stkini.setText("0")
        self.txt_stkmin.setText("10")
        self.txt_stkmax.setText("200")
        self.txt_location.clear()
        self.chk_fractional.setChecked(False)
        self.chk_active.setChecked(True)
        self.table_barcodes.setRowCount(0)
        self.table_batches.setRowCount(0)
        
        self.tabs.setCurrentIndex(0)
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
                prod = db.query(models.Product).filter_by(id=self.current_product_id).first()
                if not prod:
                    raise Exception("No se encontró el producto.")
            else:
                existente = db.query(models.Product).filter_by(art_codigo=codigo).first()
                if existente:
                    QMessageBox.warning(self, "Error", "El código de producto ya existe.")
                    return
                prod = models.Product()
                prod.art_codigo = codigo
                db.add(prod)
                
            prod.art_cbarra = self.txt_cbarra.text()
            prod.art_descri = descri
            prod.art_costo = float(str(self.txt_costo.text()).replace(',', '') or 0)
            prod.art_preven = float(str(self.txt_preven.text()).replace(',', '') or 0)
            prod.art_impu = float(str(self.txt_impu.text()).replace(',', '') or 10.0)
            prod.art_stkini = float(str(self.txt_stkini.text()).replace(',', '') or 0)
            prod.art_stkmin = int(self.txt_stkmin.text() or 10)
            prod.art_stkmax = int(self.txt_stkmax.text() or 200)
            
            prod.category_id = self.combo_cat.currentData()
            prod.brand_id = self.combo_brand.currentData()
            prod.uom = self.combo_uom.currentText()
            prod.is_fractional = self.chk_fractional.isChecked()
            prod.location = self.txt_location.text()
            prod.is_active = self.chk_active.isChecked()
            
            if hasattr(self, 'current_image_path') and self.current_image_path:
                prod.image_path = self.current_image_path
            
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

    def open_camera(self):
        codigo = self.txt_codigo.text().strip()
        if not codigo:
            QMessageBox.warning(self, "Atención", "Debe ingresar un Código Interno primero para guardar la foto.")
            self.txt_codigo.setFocus()
            return
            
        from ui.camera_dialog import CameraDialog
        dialog = CameraDialog(product_code=codigo, parent=self)
        if dialog.exec():
            if dialog.saved_image_path:
                self.current_image_path = dialog.saved_image_path
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap(self.current_image_path)
                self.lbl_product_photo.setPixmap(pixmap.scaled(self.lbl_product_photo.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))