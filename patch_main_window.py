import os

filepath = 'ui/main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add scanner layout
search_layout = """        group_cabecera = QGroupBox("Datos Factura")
        group_cabecera.setLayout(cabecera_layout)
        top_panel_layout.addWidget(group_cabecera, stretch=1)
        
        main_layout.addLayout(top_panel_layout, stretch=1)
        
        # --- PANEL CENTRAL (Detalle de Factura) ---"""

replace_layout = """        group_cabecera = QGroupBox("Datos Factura")
        group_cabecera.setLayout(cabecera_layout)
        top_panel_layout.addWidget(group_cabecera, stretch=1)
        
        main_layout.addLayout(top_panel_layout, stretch=1)
        
        # --- BUSCADOR / ESCANER DE CÓDIGO DE BARRAS ---
        scanner_layout = QHBoxLayout()
        scanner_layout.addWidget(QLabel("Código de Barras / Artículo:"))
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Escanee el código de barras y presione ENTER")
        self.txt_codigo.returnPressed.connect(self.buscar_producto)
        scanner_layout.addWidget(self.txt_codigo, stretch=1)
        
        btn_buscar = QPushButton("Buscar [F4]")
        btn_buscar.clicked.connect(self.open_product_search)
        scanner_layout.addWidget(btn_buscar)
        
        main_layout.addLayout(scanner_layout)
        
        # --- PANEL CENTRAL (Detalle de Factura) ---"""

content = content.replace(search_layout, replace_layout)

# 2. Add buscar_producto and update add_product_to_grid
search_methods = """    def add_product_to_grid(self, product, cantidad=1):
        row = self.table_detalle.rowCount()
        self.table_detalle.insertRow(row)
        
        # ["Nro", "Codigo", "Descripcion", "Dp", "Cantidad", "Imp", "Iva", "Precio", "Total"]
        precio = product.art_preven
        total = precio * cantidad
        
        self.table_detalle.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table_detalle.setItem(row, 1, QTableWidgetItem(product.art_codigo))
        self.table_detalle.setItem(row, 2, QTableWidgetItem(product.art_descri))
        self.table_detalle.setItem(row, 3, QTableWidgetItem("DC")) # Deposito por defecto
        self.table_detalle.setItem(row, 4, QTableWidgetItem(str(cantidad)))
        self.table_detalle.setItem(row, 5, QTableWidgetItem("I")) # Impuesto Incluido
        self.table_detalle.setItem(row, 6, QTableWidgetItem(str(product.art_impu)))
        self.table_detalle.setItem(row, 7, QTableWidgetItem(f"{precio:,.0f}"))
        self.table_detalle.setItem(row, 8, QTableWidgetItem(f"{total:,.0f}"))
        
        self.calcular_totales()"""

replace_methods = """    def buscar_producto(self):
        codigo = self.txt_codigo.text().strip()
        if not codigo:
            return
            
        from database import SessionLocal
        import models
        db = SessionLocal()
        
        prod = db.query(models.Product).filter(
            models.Product.is_active == True,
            (models.Product.art_codigo == codigo) | (models.Product.art_cbarra == codigo)
        ).first()
        
        factor_conversion = 1.0
        
        if not prod:
            barcode = db.query(models.ProductBarcode).filter_by(barcode=codigo).first()
            if barcode and barcode.product.is_active:
                prod = barcode.product
                factor_conversion = barcode.factor_conversion
                
        db.close()
        
        if prod:
            self.add_product_to_grid(prod, cantidad=1.0 * factor_conversion)
            self.txt_codigo.clear()
            self.txt_codigo.setFocus()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Encontrado", "Artículo no encontrado o inactivo.")
            self.txt_codigo.selectAll()

    def add_product_to_grid(self, product, cantidad=1.0):
        # Verificar si ya existe en la grilla para sumar cantidad
        for row in range(self.table_detalle.rowCount()):
            if self.table_detalle.item(row, 1).text() == product.art_codigo:
                current_qty = float(self.table_detalle.item(row, 4).text())
                new_qty = current_qty + cantidad
                self.table_detalle.item(row, 4).setText(str(new_qty))
                
                precio = product.art_preven
                subtotal = new_qty * precio
                self.table_detalle.item(row, 8).setText(f"{subtotal:,.0f}")
                self.calcular_totales()
                return
                
        # Si no existe, agregar nueva fila
        row = self.table_detalle.rowCount()
        self.table_detalle.insertRow(row)
        
        precio = product.art_preven
        total = precio * cantidad
        
        self.table_detalle.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table_detalle.setItem(row, 1, QTableWidgetItem(product.art_codigo))
        
        descri = product.art_descri
        if getattr(product, 'is_fractional', False):
            descri += " (Balanza)"
            
        self.table_detalle.setItem(row, 2, QTableWidgetItem(descri))
        self.table_detalle.setItem(row, 3, QTableWidgetItem("DC")) 
        self.table_detalle.setItem(row, 4, QTableWidgetItem(str(cantidad)))
        self.table_detalle.setItem(row, 5, QTableWidgetItem("I")) 
        self.table_detalle.setItem(row, 6, QTableWidgetItem(str(product.art_impu)))
        self.table_detalle.setItem(row, 7, QTableWidgetItem(f"{precio:,.0f}"))
        self.table_detalle.setItem(row, 8, QTableWidgetItem(f"{total:,.0f}"))
        
        self.calcular_totales()"""

content = content.replace(search_methods, replace_methods)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Parche aplicado con éxito.")
