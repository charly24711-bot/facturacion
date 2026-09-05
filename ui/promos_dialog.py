import datetime
from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QDateEdit, QCompleter, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate, QStringListModel
from PyQt6.QtGui import QFont, QColor

from database import SessionLocal
import models


class PromosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏷️ Gestión de Precios Promocionales")
        self.resize(1050, 650)
        self.setup_ui()
        self.load_promos()


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
        main = QVBoxLayout(self)

        # ── Formulario de nueva promo ──────────────────────────────────────
        grp = QGroupBox("Nueva Promoción")
        grid = QGridLayout()

        self.txt_prod = QLineEdit()
        self.txt_prod.setPlaceholderText("Buscar producto [Enter]")
        self.txt_prod.returnPressed.connect(self.buscar_producto)

        # Completer
        self._cmodel = QStringListModel()
        comp = QCompleter(self._cmodel, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.activated.connect(lambda _: self._auto_buscar())
        self.txt_prod.setCompleter(comp)
        self._load_products_completer()

        self.lbl_prod_nombre = QLabel("—")
        self.lbl_prod_nombre.setStyleSheet("font-weight:bold; color:#2980b9;")

        self.txt_precio = QLineEdit()
        self.txt_precio.setPlaceholderText("Precio promo (₲)")
        self.txt_precio.textChanged.connect(lambda t, le=self.txt_precio: self.auto_format_thousands(t, le))
        self.txt_precio.setFixedWidth(130)

        self.txt_descri = QLineEdit()
        self.txt_descri.setPlaceholderText("Descripción  ej: Oferta Julio")

        today = QDate.currentDate()
        self.date_desde = QDateEdit(today)
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("dd/MM/yyyy")

        self.date_hasta = QDateEdit(today.addDays(30))
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("dd/MM/yyyy")

        grid.addWidget(QLabel("Producto:"), 0, 0)
        grid.addWidget(self.txt_prod, 0, 1, 1, 3)
        grid.addWidget(self.lbl_prod_nombre, 0, 4, 1, 2)

        grid.addWidget(QLabel("Precio Promo ₲:"), 1, 0)
        grid.addWidget(self.txt_precio, 1, 1)
        grid.addWidget(QLabel("Descripción:"), 1, 2)
        grid.addWidget(self.txt_descri, 1, 3, 1, 3)

        grid.addWidget(QLabel("Desde:"), 2, 0)
        grid.addWidget(self.date_desde, 2, 1)
        grid.addWidget(QLabel("Hasta:"), 2, 2)
        grid.addWidget(self.date_hasta, 2, 3)

        btn_add = QPushButton("➕ Agregar Promo")
        btn_add.setAutoDefault(False)
        btn_add.setStyleSheet("background:#27ae60;color:white;font-weight:bold;padding:6px;")
        btn_add.clicked.connect(self.agregar_promo)
        grid.addWidget(btn_add, 2, 4, 1, 2)

        grp.setLayout(grid)
        main.addWidget(grp)

        # ── Tabla de promos ────────────────────────────────────────────────
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Producto", "Precio Promo", "Descripción", "Desde", "Hasta", "Estado"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        main.addWidget(self.table, stretch=1)

        # ── Botones de acción ──────────────────────────────────────────────
        foot = QHBoxLayout()
        btn_toggle = QPushButton("⏸️ Activar / Desactivar")
        btn_toggle.setAutoDefault(False)
        btn_toggle.clicked.connect(self.toggle_promo)
        btn_delete = QPushButton("🗑️ Eliminar")
        btn_delete.setAutoDefault(False)
        btn_delete.setStyleSheet("background:#c0392b;color:white;")
        btn_delete.clicked.connect(self.eliminar_promo)
        foot.addStretch()
        foot.addWidget(btn_toggle)
        foot.addWidget(btn_delete)
        main.addLayout(foot)

        self.current_product_cod = None

    # ── Helpers ────────────────────────────────────────────────────────────
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
            self.lbl_prod_nombre.setText(
                f"{prod.art_descri}  |  Precio actual: ₲ {float(prod.art_preven or 0):,.0f}"
            )
            # Sugerir precio normal como base
            if not self.txt_precio.text():
                self.txt_precio.setText(f"{float(prod.art_preven or 0):.0f}")
        else:
            self.current_product_cod = None
            self.lbl_prod_nombre.setText("— No encontrado —")
        db.close()

    def agregar_promo(self):
        if not self.current_product_cod:
            QMessageBox.warning(self, "Error", "Seleccione un producto primero.")
            return
        try:
            precio = Decimal(self.txt_precio.text().replace(",", "."))
        except Exception:
            QMessageBox.warning(self, "Error", "Precio inválido.")
            return
        desde = self.date_desde.date().toPyDate()
        hasta = self.date_hasta.date().toPyDate()
        if hasta < desde:
            QMessageBox.warning(self, "Error", "La fecha Hasta debe ser posterior a Desde.")
            return

        db = SessionLocal()
        promo = models.ProductPromo(
            pro_articu=self.current_product_cod,
            pro_precio=float(precio),
            pro_desde=datetime.datetime.combine(desde, datetime.time.min),
            pro_hasta=datetime.datetime.combine(hasta, datetime.time(23, 59, 59)),
            pro_descri=self.txt_descri.text().strip() or "Promo",
            is_active=True
        )
        db.add(promo)
        db.commit()
        db.close()

        self.txt_prod.clear()
        self.txt_precio.clear()
        self.txt_descri.clear()
        self.lbl_prod_nombre.setText("—")
        self.current_product_cod = None
        self.load_promos()
        QMessageBox.information(self, "OK", "Promoción agregada correctamente.")

    def load_promos(self):
        self.table.setRowCount(0)
        db = SessionLocal()
        promos = db.query(models.ProductPromo).order_by(models.ProductPromo.pro_hasta.desc()).all()
        now = datetime.datetime.now()
        for promo in promos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(promo.id)))
            prod_desc = promo.product.art_descri if promo.product else promo.pro_articu
            self.table.setItem(row, 1, QTableWidgetItem(prod_desc))
            self.table.setItem(row, 2, QTableWidgetItem(f"₲ {float(promo.pro_precio):,.0f}"))
            self.table.setItem(row, 3, QTableWidgetItem(promo.pro_descri or ""))
            self.table.setItem(row, 4, QTableWidgetItem(promo.pro_desde.strftime("%d/%m/%Y")))
            self.table.setItem(row, 5, QTableWidgetItem(promo.pro_hasta.strftime("%d/%m/%Y")))

            # Estado
            if not promo.is_active:
                estado, color = "⏸️ Desactivada", QColor("#e74c3c")
            elif promo.pro_hasta < now:
                estado, color = "🔴 Vencida", QColor("#c0392b")
            elif promo.pro_desde > now:
                estado, color = "🟡 Pendiente", QColor("#f39c12")
            else:
                estado, color = "🟢 Vigente", QColor("#27ae60")

            estado_item = QTableWidgetItem(estado)
            estado_item.setForeground(color)
            self.table.setItem(row, 6, estado_item)
        db.close()

    def toggle_promo(self):
        row = self.table.currentRow()
        if row < 0:
            return
        promo_id = int(self.table.item(row, 0).text())
        db = SessionLocal()
        promo = db.query(models.ProductPromo).get(promo_id)
        if promo:
            promo.is_active = not promo.is_active
            db.commit()
        db.close()
        self.load_promos()

    def eliminar_promo(self):
        row = self.table.currentRow()
        if row < 0:
            return
        promo_id = int(self.table.item(row, 0).text())
        resp = QMessageBox.question(self, "Confirmar", "¿Eliminar esta promoción definitivamente?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.No:
            return
        db = SessionLocal()
        promo = db.query(models.ProductPromo).get(promo_id)
        if promo:
            db.delete(promo)
            db.commit()
        db.close()
        self.load_promos()