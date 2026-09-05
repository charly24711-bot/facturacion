from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QCompleter, QAbstractItemView, QListWidget, QInputDialog
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QColor

from database import SessionLocal
import models


class PriceListsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Listas de Precios (Minorista / Mayorista)")
        self.resize(900, 600)
        self.current_list_id = None
        self.current_product_cod = None
        self.setup_ui()
        self.load_lists()


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

    def setup_ui(self):
        main = QHBoxLayout(self)

        # ── Panel Izquierdo: Gestión de Listas ─────────────────────────────
        left_panel = QVBoxLayout()
        grp_lists = QGroupBox("Listas de Precios")
        lists_layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_list_selected)
        lists_layout.addWidget(self.list_widget)

        btn_new_list = QPushButton("➕ Nueva Lista")
        btn_new_list.clicked.connect(self.crear_lista)
        btn_del_list = QPushButton("🗑️ Eliminar Lista")
        btn_del_list.setStyleSheet("color: #c0392b;")
        btn_del_list.clicked.connect(self.eliminar_lista)

        lists_layout.addWidget(btn_new_list)
        lists_layout.addWidget(btn_del_list)
        grp_lists.setLayout(lists_layout)
        left_panel.addWidget(grp_lists)
        
        main.addLayout(left_panel, stretch=1)

        # ── Panel Derecho: Productos en la Lista ───────────────────────────
        right_panel = QVBoxLayout()
        self.grp_items = QGroupBox("Precios Específicos de la Lista")
        self.grp_items.setEnabled(False)
        items_layout = QVBoxLayout()

        # Agregar producto a la lista
        add_layout = QHBoxLayout()
        self.txt_prod = QLineEdit()
        self.txt_prod.setPlaceholderText("Buscar producto [Enter]")
        self.txt_prod.returnPressed.connect(self.buscar_producto)

        self._cmodel = QStringListModel()
        comp = QCompleter(self._cmodel, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.activated.connect(self._auto_buscar)
        self.txt_prod.setCompleter(comp)
        self._load_products_completer()

        self.lbl_prod = QLabel("—")
        self.lbl_prod.setMinimumWidth(150)
        
        self.txt_precio = QLineEdit()
        self.txt_precio.setPlaceholderText("Precio (₲)")
        self.txt_precio.textChanged.connect(lambda t, le=self.txt_precio: self.auto_format_thousands(t, le))
        self.txt_precio.setFixedWidth(100)

        btn_add_item = QPushButton("➕ Agregar Precio")
        btn_add_item.clicked.connect(self.agregar_precio_lista)

        add_layout.addWidget(self.txt_prod, stretch=1)
        add_layout.addWidget(self.lbl_prod)
        add_layout.addWidget(self.txt_precio)
        add_layout.addWidget(btn_add_item)

        items_layout.addLayout(add_layout)

        # Tabla de productos en la lista
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Cód.", "Producto", "Precio en Lista (₲)", "Precio Base (₲)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        items_layout.addWidget(self.table, stretch=1)

        btn_del_item = QPushButton("🗑️ Quitar de la Lista")
        btn_del_item.clicked.connect(self.quitar_precio_lista)
        items_layout.addWidget(btn_del_item, alignment=Qt.AlignmentFlag.AlignRight)

        self.grp_items.setLayout(items_layout)
        right_panel.addWidget(self.grp_items, stretch=3)
        
        main.addLayout(right_panel, stretch=3)

    # ── Gestión de Listas ──────────────────────────────────────────────────
    def load_lists(self):
        self.list_widget.clear()
        db = SessionLocal()
        lists = db.query(models.PriceList).all()
        for lst in lists:
            self.list_widget.addItem(f"[{lst.id}] {lst.pl_nombre}")
        db.close()

    def crear_lista(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Lista", "Nombre de la Lista de Precios:")
        if ok and nombre.strip():
            db = SessionLocal()
            nueva = models.PriceList(pl_nombre=nombre.strip())
            db.add(nueva)
            db.commit()
            db.close()
            self.load_lists()

    def eliminar_lista(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        text = self.list_widget.item(row).text()
        list_id = int(text.split("]")[0][1:])
        
        resp = QMessageBox.question(self, "Confirmar", "¿Eliminar esta lista completa?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            db = SessionLocal()
            lst = db.query(models.PriceList).get(list_id)
            if lst:
                db.query(models.PriceListItem).filter_by(pli_list_id=list_id).delete()
                db.delete(lst)
                db.commit()
            db.close()
            self.load_lists()
            self.grp_items.setEnabled(False)
            self.table.setRowCount(0)

    def on_list_selected(self, row):
        if row < 0:
            self.current_list_id = None
            self.grp_items.setEnabled(False)
            return
        
        text = self.list_widget.item(row).text()
        self.current_list_id = int(text.split("]")[0][1:])
        self.grp_items.setTitle(f"Precios Específicos: {text}")
        self.grp_items.setEnabled(True)
        self.load_list_items()

    # ── Gestión de Productos en la Lista ───────────────────────────────────
    def _load_products_completer(self):
        db = SessionLocal()
        prods = db.query(models.Product).filter_by(is_active=True).all()
        self._cmodel.setStringList([f"{p.art_codigo} - {p.art_descri}" for p in prods])
        db.close()

    def _auto_buscar(self):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.buscar_producto)

    def buscar_producto(self):
        q = self.txt_prod.text().strip()
        if not q:
            return
        codigo = q.split(" - ")[0].strip() if " - " in q else q
        db = SessionLocal()
        prod = db.query(models.Product).filter(
            (models.Product.art_codigo == codigo) |
            (models.Product.art_descri.ilike(f"%{codigo}%"))
        ).first()
        if prod:
            self.current_product_cod = prod.art_codigo
            self.lbl_prod.setText(prod.art_descri)
            if not self.txt_precio.text():
                self.txt_precio.setText(f"{float(prod.art_preven or 0):.0f}")
        else:
            self.current_product_cod = None
            self.lbl_prod.setText("— No encontrado —")
        db.close()

    def agregar_precio_lista(self):
        if not self.current_list_id or not self.current_product_cod:
            return
        try:
            precio = Decimal(self.txt_precio.text().replace(",", "."))
        except Exception:
            QMessageBox.warning(self, "Error", "Precio inválido.")
            return

        db = SessionLocal()
        item = db.query(models.PriceListItem).filter_by(
            pli_list_id=self.current_list_id, pli_articu=self.current_product_cod
        ).first()
        if item:
            item.pli_precio = precio
        else:
            nuevo = models.PriceListItem(
                pli_list_id=self.current_list_id,
                pli_articu=self.current_product_cod,
                pli_precio=precio
            )
            db.add(nuevo)
        db.commit()
        db.close()
        
        self.txt_prod.clear()
        self.txt_precio.clear()
        self.lbl_prod.setText("—")
        self.current_product_cod = None
        self.load_list_items()

    def load_list_items(self):
        self.table.setRowCount(0)
        if not self.current_list_id:
            return
        db = SessionLocal()
        items = db.query(models.PriceListItem).filter_by(pli_list_id=self.current_list_id).all()
        for it in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(it.pli_articu))
            descri = it.product.art_descri if it.product else "Desconocido"
            self.table.setItem(row, 1, QTableWidgetItem(descri))
            
            # Precio en Lista vs Precio Base
            precio_lista = float(it.pli_precio)
            precio_base = float(it.product.art_preven or 0) if it.product else 0
            
            i_lista = QTableWidgetItem(f"₲ {precio_lista:,.0f}")
            i_lista.setForeground(QColor("#27ae60"))
            i_lista.setFont(self._bold_font())
            self.table.setItem(row, 2, i_lista)
            
            self.table.setItem(row, 3, QTableWidgetItem(f"₲ {precio_base:,.0f}"))
        db.close()

    def _bold_font(self):
        f = self.table.font()
        f.setBold(True)
        return f

    def quitar_precio_lista(self):
        row = self.table.currentRow()
        if row < 0 or not self.current_list_id:
            return
        cod = self.table.item(row, 0).text()
        db = SessionLocal()
        db.query(models.PriceListItem).filter_by(
            pli_list_id=self.current_list_id, pli_articu=cod
        ).delete()
        db.commit()
        db.close()
        self.load_list_items()