import sys
from decimal import Decimal
import datetime
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QGroupBox, QGridLayout, QComboBox, QCompleter, QDateEdit)
from PyQt6.QtCore import Qt, QTimer, QStringListModel, QDate
from PyQt6.QtGui import QFont

from database import SessionLocal
import models
from utils.formatting import aplicar_formato_moneda, parsear_monto

class PurchaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛒 Registro de Compras a Proveedores")
        self.resize(1000, 700)
        
        self.items = [] # list of dicts: {'product': Product, 'qty': Decimal, 'cost': Decimal}
        self.total = Decimal('0')
        
        self.setup_ui()
        self.load_suppliers()
        self.cargar_lista_productos()
        

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Cabecera Factura ---
        group_cabecera = QGroupBox("Datos de la Factura de Compra")
        grid_cabecera = QGridLayout()
        
        self.cmb_proveedor = QComboBox()
        self.cmb_proveedor.setEditable(True)
        self.cmb_proveedor.setPlaceholderText("Seleccione o escriba un Proveedor")
        
        cmb_completer = self.cmb_proveedor.completer()
        if cmb_completer:
            cmb_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            cmb_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            
            
        self.cmb_proveedor.lineEdit().returnPressed.connect(self.handle_proveedor_enter)
        grid_cabecera.addWidget(QLabel("Proveedor:"), 0, 0)
        grid_cabecera.addWidget(self.cmb_proveedor, 0, 1, 1, 3)
        
        self.txt_factura = QLineEdit()
        self.txt_factura.setPlaceholderText("Ej: 001-001-0001234")
        grid_cabecera.addWidget(QLabel("Nro. Factura:"), 1, 0)
        grid_cabecera.addWidget(self.txt_factura, 1, 1)
        
        self.txt_timbrado = QLineEdit()
        grid_cabecera.addWidget(QLabel("Timbrado:"), 1, 2)
        grid_cabecera.addWidget(self.txt_timbrado, 1, 3)
        
        group_cabecera.setLayout(grid_cabecera)
        main_layout.addWidget(group_cabecera)
        
        # --- Buscador de Productos ---
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar producto por código o descripción [Enter]")
        self.txt_search.returnPressed.connect(self.buscar_producto)
        
        # Setup Completer
        self.completer_model = QStringListModel()
        completer = QCompleter(self.completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.activated.connect(self.on_completer_activated)
        self.txt_search.setCompleter(completer)
        
        self.txt_qty = QLineEdit("1")
        self.txt_qty.setPlaceholderText("Cant")
        self.txt_qty.setFixedWidth(60)
        
        self.lbl_uom = QLabel("")
        self.lbl_uom.setStyleSheet("color: gray; font-style: italic;")

        
        self.txt_cost = QLineEdit()
        self.txt_cost.setPlaceholderText("Costo Unit.")
        self.txt_cost.textChanged.connect(lambda t: aplicar_formato_moneda(t, "PYG", self.txt_cost))
        self.txt_cost.setFixedWidth(80)
        self.txt_cost.returnPressed.connect(lambda: self.txt_lote.setFocus())
        
        self.txt_lote = QLineEdit()
        self.txt_lote.setPlaceholderText("Lote (Opc.)")
        self.txt_lote.setFixedWidth(80)
        self.txt_lote.returnPressed.connect(lambda: self.date_venc.setFocus())
        
        self.date_venc = QDateEdit()
        self.date_venc.setDisplayFormat("dd-MM-yyyy")
        self.date_venc.setCalendarPopup(True)
        self.date_venc.setDate(QDate.currentDate().addYears(1))
        self.date_venc.setSpecialValueText("Sin Vencimiento")
        self.date_venc.setDate(self.date_venc.minimumDate()) 
        
        btn_add = QPushButton("Agregar")
        btn_add.setAutoDefault(False)
        btn_add.clicked.connect(self.agregar_item)
        
        search_layout.addWidget(QLabel("Producto:"))
        search_layout.addWidget(self.txt_search, stretch=1)
        search_layout.addWidget(QLabel("Cant:"))
        search_layout.addWidget(self.txt_qty)
        search_layout.addWidget(self.lbl_uom)
        search_layout.addWidget(QLabel("Costo Unit:"))
        search_layout.addWidget(self.txt_cost)
        search_layout.addWidget(self.txt_lote)
        search_layout.addWidget(self.date_venc)
        search_layout.addWidget(btn_add)
        main_layout.addLayout(search_layout)
        
        # --- Grilla de Items ---
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción", "Lote", "Vencimiento", "Cantidad", "Costo Unit.", "Subtotal"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table, stretch=1)
        
        # --- Pie de Totales ---
        footer_layout = QHBoxLayout()
        self.lbl_total = QLabel("Total Factura: ₲ 0")
        self.lbl_total.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #2c3e50;")
        
        btn_procesar = QPushButton("✅ Procesar Compra y Aumentar Stock")
        btn_procesar.setAutoDefault(False)
        btn_procesar.setMinimumHeight(50)
        btn_procesar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 14px;")
        btn_procesar.clicked.connect(self.procesar_compra)
        
        footer_layout.addWidget(self.lbl_total, stretch=1)
        footer_layout.addWidget(btn_procesar)
        main_layout.addLayout(footer_layout)
        
        # Variable temporal para producto encontrado
        self.current_product = None
        self.current_factor = Decimal("1")
        self.costo_registrado = Decimal("0")
        
    def handle_proveedor_enter(self):
        if not self.cmb_proveedor.currentText().strip():
            self.cmb_proveedor.showPopup()
        else:
            self.txt_factura.setFocus()
            
    def on_completer_activated(self, text):
        QTimer.singleShot(0, self.buscar_producto)
        
    def load_suppliers(self):
        db = SessionLocal()
        suppliers = db.query(models.Supplier).all()
        for sup in suppliers:
            self.cmb_proveedor.addItem(sup.sup_nombre, sup.id)
        db.close()
        
    def cargar_lista_productos(self):
        db = SessionLocal()
        productos = db.query(models.Product).filter_by(is_active=True).all()
        lista = []
        for p in productos:
            lista.append(f"{p.art_codigo} - {p.art_descri}")
        db.close()
        self.completer_model.setStringList(lista)
        
    def buscar_producto(self):
        query = self.txt_search.text().strip()
        if not query: return
        
        if " - " in query:
            codigo = query.split(" - ")[0].strip()
        else:
            codigo = query
            
        db = SessionLocal()
        prod = None
        factor = Decimal('1')
        barcode_name = ""
        
        prod = db.query(models.Product).filter(
            (models.Product.art_codigo == codigo) | (models.Product.art_cbarra == codigo)
        ).first()
        
        if not prod:
            pbc = db.query(models.ProductBarcode).filter_by(barcode=codigo).first()
            if pbc:
                prod = pbc.product
                factor = pbc.factor_conversion
                barcode_name = f" (Pack x{factor})"
                
        if not prod:
            prod = db.query(models.Product).filter(models.Product.art_descri.ilike(f"%{codigo}%")).first()
            
        if prod:
            self.current_product = prod
            self.current_factor = factor
            self.costo_registrado = Decimal(str(prod.art_costo or 0))
            uom_text = prod.uom if prod.uom else "Un"
            self.lbl_uom.setText(f"{uom_text}{barcode_name}")
            
            self.txt_search.setText(f"{prod.art_codigo} - {prod.art_descri}")
            
            # Suggest last cost for the SINGLE unit, or multiplied by factor?
            # Usually the user enters the cost of what they are scanning (the pack).
            # So we suggest the cost * factor.
            suggested_cost = (prod.art_costo or Decimal('0')) * factor
            self.txt_cost.setText(f"{float(suggested_cost):.0f}") 
            
            self.txt_qty.setFocus()
            self.txt_qty.selectAll()
        else:
            QMessageBox.warning(self, "No encontrado", "No se encontró el producto.")
            self.current_product = None
            self.lbl_uom.setText("")
            
        db.close()
        
    def agregar_item(self):
        # Si current_product no está listo pero hay texto, intentar buscar primero
        if not self.current_product:
            texto = self.txt_search.text().strip()
            if texto:
                self.buscar_producto()
            if not self.current_product:
                QMessageBox.warning(self, "Error", "Busque y seleccione un producto primero.")
                return
            
        try:
            qty_input = Decimal(self.txt_qty.text().replace(',', '.'))
            cost_input = Decimal(parsear_monto(self.txt_cost.text(), "PYG"))
        except:
            QMessageBox.warning(self, "Error", "Cantidad o Costo inválidos.")
            return
            
        if qty_input <= 0 or cost_input <= 0:
            QMessageBox.warning(self, "Error", "Valores deben ser mayores a cero.")
            return
            
        # Calculate real quantity and unit cost based on the pack factor
        real_qty = qty_input * self.current_factor
        unit_cost = cost_input / self.current_factor
        
        # Validation for lower cost: show CPP preview
        stock_actual = int(self.current_product.art_stkini or 0) if self.current_product.art_stkini else 0
        if self.costo_registrado > 0 and unit_cost < self.costo_registrado:
            cpp_nuevo = (stock_actual * self.costo_registrado + real_qty * unit_cost) / (stock_actual + real_qty) if (stock_actual + real_qty) > 0 else unit_cost
            resp = QMessageBox.question(
                self, 
                "Costo Inferior al Registrado", 
                f"El nuevo costo unitario (\u20b2 {unit_cost:,.0f}) es INFERIOR al costo actual (\u20b2 {self.costo_registrado:,.0f})."
                f"\n\nExisten {stock_actual} unidades en stock al precio anterior."
                f"\n\nSi confirma, el sistema calculará el Costo Promedio Ponderado:"
                f"\n  CPP = ({stock_actual} u × \u20b2{self.costo_registrado:,.0f} + {float(real_qty):g} u × \u20b2{unit_cost:,.0f}) / {stock_actual + int(real_qty)} u"
                f"\n  \u21d2 Nuevo Costo Promedio: \u20b2 {cpp_nuevo:,.0f}"
                f"\n\n\u00bfConfirmar precio rebajado y recalcular CPP?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.No:
                self.txt_cost.setFocus()
                self.txt_cost.selectAll()
                return
                
        subtotal = cost_input * qty_input
        
        lote_val = self.txt_lote.text().strip()
        venc_date = self.date_venc.date()
        venc_val = venc_date.toPyDate() if venc_date != self.date_venc.minimumDate() else None
        
        self.items.append({
            'cod': self.current_product.art_codigo,
            'desc': self.current_product.art_descri,
            'qty': real_qty,
            'cost': unit_cost,
            'subtotal': subtotal,
            'lote': lote_val,
            'vencimiento': venc_val
        })
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(self.current_product.art_codigo))
        
        desc_text = self.current_product.art_descri
        if self.current_factor > 1:
            desc_text += f" (Ingresado como Pack x{self.current_factor})"
            
        self.table.setItem(row, 1, QTableWidgetItem(desc_text))
        self.table.setItem(row, 2, QTableWidgetItem(lote_val or "-"))
        self.table.setItem(row, 3, QTableWidgetItem(venc_val.strftime("%d/%m/%Y") if venc_val else "-"))
        self.table.setItem(row, 4, QTableWidgetItem(f"{float(real_qty):g}"))
        self.table.setItem(row, 5, QTableWidgetItem(f"{float(unit_cost):,.0f}"))
        self.table.setItem(row, 6, QTableWidgetItem(f"{float(subtotal):,.0f}"))
        
        self.actualizar_total()
        
        self.current_product = None
        self.current_factor = Decimal("1")
        self.costo_registrado = Decimal("0")
        self.lbl_uom.setText("")
        self.txt_search.clear()
        self.txt_qty.setText("1")
        self.txt_cost.clear()
        self.txt_lote.clear()
        self.date_venc.setDate(self.date_venc.minimumDate())
        self.txt_search.setFocus()
        
    def actualizar_total(self):
        self.total = sum(i['subtotal'] for i in self.items)
        self.lbl_total.setText(f"Total Factura: ₲ {float(self.total):,.0f}")
        
    def procesar_compra(self):
        if not self.items:
            QMessageBox.warning(self, "Error", "No hay ítems para procesar.")
            return
            
        proveedor_text = self.cmb_proveedor.currentText().strip()
        nro_fac = self.txt_factura.text().strip()
        
        if not proveedor_text or not nro_fac:
            QMessageBox.warning(self, "Error", "Debe completar Proveedor y Nro. Factura.")
            return
            
        db = SessionLocal()
        
        # 1. Resolver Proveedor
        prov_id = self.cmb_proveedor.currentData()
        if not prov_id:
            # Crear proveedor al vuelo
            nuevo_prov = models.Supplier(sup_codigo=proveedor_text[:10].upper(), sup_nombre=proveedor_text)
            db.add(nuevo_prov)
            db.commit()
            db.refresh(nuevo_prov)
            prov_id = nuevo_prov.id
            
        # 2. Cabecera
        compra = models.Purchase(
            com_provee=prov_id,
            com_nrofac=nro_fac,
            com_timbra=self.txt_timbrado.text().strip(),
            com_total=self.total
        )
        db.add(compra)
        db.commit()
        db.refresh(compra)
        
        # 3. Detalles y Actualización de Stock
        for itm in self.items:
            detalle = models.PurchaseItem(
                cit_compra_id=compra.id,
                cit_articu=itm['cod'],
                cit_canti=itm['qty'],
                cit_precio=itm['cost']
            )
            db.add(detalle)
            
            # Actualizar Stock con CPP (Costo Promedio Ponderado)
            prod = db.query(models.Product).filter_by(art_codigo=itm['cod']).first()
            if prod:
                stock_anterior = int(prod.art_stkini) if prod.art_stkini else 0
                costo_anterior = float(prod.art_costo) if prod.art_costo else 0.0
                qty_nueva = int(itm['qty'])
                costo_nuevo = float(itm['cost'])
                
                stock_total = stock_anterior + qty_nueva
                if stock_total > 0:
                    cpp = (stock_anterior * costo_anterior + qty_nueva * costo_nuevo) / stock_total
                else:
                    cpp = costo_nuevo
                    
                prod.art_stkini = stock_total
                prod.art_costo = round(cpp, 2)
                
        db.commit()
        db.close()
        
        QMessageBox.information(self, "Éxito", f"Compra registrada correctamente.\nSe ha actualizado el stock de {len(self.items)} productos.")
        self.accept()