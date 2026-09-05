from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QCompleter, QAbstractItemView, QSpinBox
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QColor

from database import SessionLocal
import models


class PriceTiersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💰 Precios por Volumen (Escalas de Precio)")
        self.resize(850, 580)
        self.current_product_cod = None
        self.setup_ui()


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

        # ── Selector de Producto ───────────────────────────────────────────
        grp_prod = QGroupBox("Seleccionar Producto")
        prod_layout = QHBoxLayout()

        self.txt_prod = QLineEdit()
        self.txt_prod.setPlaceholderText("Buscar producto por código o descripción [Enter]")
        self.txt_prod.returnPressed.connect(self.buscar_producto)

        self._cmodel = QStringListModel()
        comp = QCompleter(self._cmodel, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.activated.connect(self._auto_buscar)
        self.txt_prod.setCompleter(comp)
        self._load_products_completer()

        self.lbl_prod = QLabel("— Seleccione un producto —")
        self.lbl_prod.setStyleSheet("font-weight:bold; color:#2980b9; min-width: 300px;")

        prod_layout.addWidget(self.txt_prod, stretch=1)
        prod_layout.addWidget(self.lbl_prod)
        grp_prod.setLayout(prod_layout)
        main.addWidget(grp_prod)

        # ── Tabla de escalas actuales ──────────────────────────────────────
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Cant. Mínima", "Precio Especial (₲)", "Descripción", "Activo"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        main.addWidget(self.table, stretch=1)

        # ── Formulario para agregar escala ─────────────────────────────────
        grp_add = QGroupBox("Agregar Nueva Escala de Precio")
        add_layout = QVBoxLayout()

        self.spin_qty = QSpinBox()
        self.spin_qty.setMinimum(2)
        self.spin_qty.setMaximum(99999)
        self.spin_qty.setValue(6)
        self.spin_qty.setSuffix(" unidades")

        self.txt_precio = QLineEdit()
        self.txt_precio.setPlaceholderText("Precio especial (₲)")
        self.txt_precio.textChanged.connect(lambda t, le=self.txt_precio: self.auto_format_thousands(t, le))

        self.txt_descri = QLineEdit()
        self.txt_descri.setPlaceholderText("Descripción  ej: Precio Mayorista")

        btn_add = QPushButton("➕ Agregar Escala")
        btn_add.setAutoDefault(False)
        btn_add.setStyleSheet("background:#2980b9; color:white; font-weight:bold; padding:6px;")
        btn_add.clicked.connect(self.agregar_tier)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Cant. mínima:"))
        row1.addWidget(self.spin_qty, stretch=1)
        row1.addWidget(QLabel("  Precio Especial (₲):"))
        row1.addWidget(self.txt_precio, stretch=2)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Descripción:"))
        row2.addWidget(self.txt_descri, stretch=1)
        row2.addWidget(btn_add)
        
        add_layout.addLayout(row1)
        add_layout.addLayout(row2)

        grp_add.setLayout(add_layout)
        main.addWidget(grp_add)

        # ── Botones de acción ──────────────────────────────────────────────
        foot = QHBoxLayout()
        btn_toggle = QPushButton("⏸️ Activar / Desactivar")
        btn_toggle.setAutoDefault(False)
        btn_toggle.clicked.connect(self.toggle_tier)
        btn_delete = QPushButton("🗑️ Eliminar")
        btn_delete.setAutoDefault(False)
        btn_delete.setStyleSheet("background:#c0392b; color:white;")
        btn_delete.clicked.connect(self.eliminar_tier)
        foot.addStretch()
        foot.addWidget(btn_toggle)
        foot.addWidget(btn_delete)
        main.addLayout(foot)

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
            self.lbl_prod.setText(
                f"{prod.art_descri}  |  Precio normal: ₲ {float(prod.art_preven or 0):,.0f}"
            )
            if not self.txt_precio.text():
                self.txt_precio.setText(f"{float(prod.art_preven or 0):.0f}")
            self.load_tiers()
        else:
            self.current_product_cod = None
            self.lbl_prod.setText("— No encontrado —")
            self.table.setRowCount(0)
        db.close()

    def load_tiers(self):
        if not self.current_product_cod:
            return
        self.table.setRowCount(0)
        db = SessionLocal()
        tiers = (db.query(models.PriceTier)
                   .filter_by(pt_articu=self.current_product_cod)
                   .order_by(models.PriceTier.pt_qty_min)
                   .all())
        for t in tiers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f"{t.pt_qty_min}+"))
            self.table.setItem(row, 1, QTableWidgetItem(f"₲ {float(t.pt_precio):,.0f}"))
            self.table.setItem(row, 2, QTableWidgetItem(t.pt_descri or ""))
            activo_item = QTableWidgetItem("✅ Activo" if t.is_active else "⏸️ Inactivo")
            activo_item.setForeground(QColor("#27ae60") if t.is_active else QColor("#e74c3c"))
            # Store ID in column 3
            activo_item.setData(Qt.ItemDataRole.UserRole, t.id)
            self.table.setItem(row, 3, activo_item)
        db.close()

    def agregar_tier(self):
        if not self.current_product_cod:
            QMessageBox.warning(self, "Error", "Seleccione un producto primero.")
            return
        try:
            precio = Decimal(self.txt_precio.text().replace(",", "."))
        except Exception:
            QMessageBox.warning(self, "Error", "Precio inválido.")
            return
        qty_min = self.spin_qty.value()
        db = SessionLocal()
        # Check if tier for this qty already exists
        exist = db.query(models.PriceTier).filter_by(
            pt_articu=self.current_product_cod, pt_qty_min=qty_min
        ).first()
        if exist:
            QMessageBox.warning(self, "Error", f"Ya existe una escala para {qty_min}+ unidades.")
            db.close()
            return
        tier = models.PriceTier(
            pt_articu=self.current_product_cod,
            pt_qty_min=qty_min,
            pt_precio=float(precio),
            pt_descri=self.txt_descri.text().strip() or f"Precio {qty_min}+",
            is_active=True
        )
        db.add(tier)
        db.commit()
        db.close()
        self.txt_precio.clear()
        self.txt_descri.clear()
        self.load_tiers()

    def _get_selected_tier_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 3)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def toggle_tier(self):
        tid = self._get_selected_tier_id()
        if tid is None:
            return
        db = SessionLocal()
        tier = db.query(models.PriceTier).get(tid)
        if tier:
            tier.is_active = not tier.is_active
            db.commit()
        db.close()
        self.load_tiers()

    def eliminar_tier(self):
        tid = self._get_selected_tier_id()
        if tid is None:
            return
        resp = QMessageBox.question(self, "Confirmar", "¿Eliminar esta escala?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.No:
            return
        db = SessionLocal()
        tier = db.query(models.PriceTier).get(tid)
        if tier:
            db.delete(tier)
            db.commit()
        db.close()
        self.load_tiers()