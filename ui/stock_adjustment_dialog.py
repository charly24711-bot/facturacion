"""
ui/stock_adjustment_dialog.py
==============================
Gestión de Mermas, Ajustes de Inventario y Donaciones.
Permite registrar bajas y correcciones de stock con trazabilidad completa.
Tipos: MERMA | DONACION | DEVOLUCION_PROVEEDOR | AJUSTE_POSITIVO | AJUSTE_NEGATIVO
"""

from decimal import Decimal, InvalidOperation
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QComboBox, QAbstractItemView, QFrame, QDateEdit,
    QCompleter, QWidget, QSplitter
)
from PyQt6.QtCore import Qt, QStringListModel, QDate
from PyQt6.QtGui import QFont, QIcon, QColor
from decimal import Decimal
import datetime
from database import SessionLocal
import models
from utils.formatting import aplicar_formato_moneda, parsear_monto


TIPOS_AJUSTE = {
    "MERMA": ("🗑️ Merma / Vencimiento", -1),          # resta stock
    "DONACION": ("❤️ Donación / Consumo Interno", -1),  # resta stock
    "DEVOLUCION_PROVEEDOR": ("↩️ Devolución a Proveedor", -1),  # resta stock
    "AJUSTE_NEGATIVO": ("⬇️ Ajuste Negativo (Corrección)", -1),  # resta stock
    "AJUSTE_POSITIVO": ("⬆️ Ajuste Positivo (Corrección)", +1),  # suma stock
}

TIPO_COLORS = {
    "MERMA":               QColor("#c62828"),
    "DONACION":            QColor("#6a1b9a"),
    "DEVOLUCION_PROVEEDOR": QColor("#e65100"),
    "AJUSTE_NEGATIVO":     QColor("#b71c1c"),
    "AJUSTE_POSITIVO":     QColor("#1b5e20"),
}


class StockAdjustmentDialog(QDialog):
    """
    Back-Office: Mermas y Ajustes de Inventario.
    Requiere rol ADMIN o GERENTE.
    """
    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user or {'id': 1, 'username': 'admin', 'role': 'ADMIN'}
        self.current_product = None
        self.setWindowTitle("📦 Mermas y Ajustes de Inventario")
        self.resize(1060, 640)
        self.setMinimumSize(860, 500)
        self.setup_ui()
        self.load_historial()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)

        lbl_title = QLabel("📦 MERMAS Y AJUSTES DE INVENTARIO")
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #b71c1c; padding: 4px 0 8px 0;")
        root.addWidget(lbl_title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        # ─── Panel Izquierdo: Formulario ────────────────────────────────────
        left = QGroupBox("📋 Registrar Ajuste")
        left.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 12px; border: 2px solid #b71c1c;
                        border-radius: 6px; margin-top: 8px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #b71c1c; }
        """)
        form = QGridLayout(left)
        form.setSpacing(10)
        form.setContentsMargins(14, 14, 14, 14)

        # Buscador de artículo
        form.addWidget(QLabel("Artículo:"), 0, 0)
        self.txt_art = QLineEdit()
        self.txt_art.setPlaceholderText("Código o Descripción [Enter]")
        self.txt_art.returnPressed.connect(self.buscar_articulo)
        self._cmodel = QStringListModel()
        comp = QCompleter(self._cmodel, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.activated.connect(self._auto_buscar)
        self.txt_art.setCompleter(comp)
        self._cargar_completer()
        form.addWidget(self.txt_art, 0, 1, 1, 2)

        # Info del producto seleccionado
        self.lbl_prod_info = QLabel("— Seleccione un producto —")
        self.lbl_prod_info.setStyleSheet("color:#555; font-style:italic;")
        self.lbl_prod_info.setFont(QFont("Segoe UI", 10))
        form.addWidget(self.lbl_prod_info, 1, 0, 1, 3)

        self.lbl_stock_actual = QLabel("Stock actual: —")
        self.lbl_stock_actual.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_stock_actual.setStyleSheet("color: #1565c0;")
        form.addWidget(self.lbl_stock_actual, 2, 0, 1, 3)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: 1px solid #e2e8f0;")
        form.addWidget(sep, 3, 0, 1, 3)

        # Tipo de ajuste
        form.addWidget(QLabel("Tipo de Ajuste:"), 4, 0)
        self.cmb_tipo = QComboBox()
        for key, (label, _) in TIPOS_AJUSTE.items():
            self.cmb_tipo.addItem(label, key)
        self.cmb_tipo.setStyleSheet("padding: 5px; font-weight: bold;")
        form.addWidget(self.cmb_tipo, 4, 1, 1, 2)

        # Cantidad
        form.addWidget(QLabel("Cantidad:"), 5, 0)
        self.txt_cantidad = QLineEdit()
        self.txt_cantidad.setPlaceholderText("Ej: 5 o 2.500")
        self.txt_cantidad.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.txt_cantidad.textChanged.connect(self._actualizar_perdida)
        form.addWidget(self.txt_cantidad, 5, 1, 1, 2)

        # Costo unitario (referencia)
        form.addWidget(QLabel("Costo Unitario (₲):"), 6, 0)
        self.txt_costo = QLineEdit("0")
        self.txt_costo.textChanged.connect(lambda t: aplicar_formato_moneda(t, "PYG", self.txt_costo))
        self.txt_costo.textChanged.connect(self._actualizar_perdida)
        form.addWidget(self.txt_costo, 6, 1, 1, 2)

        # Pérdida calculada
        form.addWidget(QLabel("Monto Pérdida (₲):"), 7, 0)
        self.lbl_perdida = QLabel("₲ 0")
        self.lbl_perdida.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_perdida.setStyleSheet("color: #c62828;")
        form.addWidget(self.lbl_perdida, 7, 1, 1, 2)

        # Motivo
        form.addWidget(QLabel("Motivo / Descripción:"), 8, 0)
        self.txt_motivo = QLineEdit()
        self.txt_motivo.setPlaceholderText("Ej: Vencido batch 2025-01, Dañado transporte...")
        form.addWidget(self.txt_motivo, 8, 1, 1, 2)

        # Preview stock resultante
        self.lbl_stock_nuevo = QLabel("Stock resultante: —")
        self.lbl_stock_nuevo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_stock_nuevo.setStyleSheet("color: #2e7d32;")
        form.addWidget(self.lbl_stock_nuevo, 9, 0, 1, 3)

        form.setRowStretch(10, 1)

        # Botón registrar
        btn_registrar = QPushButton("✅ Registrar Ajuste")
        btn_registrar.setStyleSheet("""
            QPushButton { background:#b71c1c; color:white; font-weight:bold;
                          font-size:13px; padding:10px; border-radius:5px; }
            QPushButton:hover { background:#c62828; }
        """)
        btn_registrar.clicked.connect(self.registrar_ajuste)
        form.addWidget(btn_registrar, 11, 0, 1, 3)

        splitter.addWidget(left)

        # ─── Panel Derecho: Historial ────────────────────────────────────────
        right = QGroupBox("📜 Historial de Ajustes")
        right.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 12px; border: 2px solid #546e7a;
                        border-radius: 6px; margin-top: 8px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #546e7a; }
        """)
        rlay = QVBoxLayout(right)

        # Filtros historial
        filt_row = QHBoxLayout()
        filt_row.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_desde.setCalendarPopup(True)
        filt_row.addWidget(self.date_desde)
        filt_row.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit(QDate.currentDate())
        self.date_hasta.setCalendarPopup(True)
        filt_row.addWidget(self.date_hasta)
        btn_filt = QPushButton("🔍 Filtrar")
        btn_filt.clicked.connect(self.load_historial)
        filt_row.addWidget(btn_filt)
        filt_row.addStretch()
        rlay.addLayout(filt_row)

        self.tabla_hist = QTableWidget(0, 6)
        self.tabla_hist.setHorizontalHeaderLabels(["Fecha", "Código", "Descripción", "Tipo", "Cantidad", "Pérdida (₲)"])
        self.tabla_hist.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla_hist.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_hist.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_hist.setAlternatingRowColors(True)
        self.tabla_hist.setStyleSheet("""
            QTableWidget { font-size: 11px; }
            QHeaderView::section { background:#37474f; color:white; font-weight:bold; padding:4px; }
        """)
        rlay.addWidget(self.tabla_hist, stretch=1)

        # Totales
        tot_row = QHBoxLayout()
        tot_row.addStretch()
        self.lbl_total_perdida = QLabel("Total Pérdidas del Período: ₲ 0")
        self.lbl_total_perdida.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_total_perdida.setStyleSheet("color: #c62828; padding: 4px;")
        tot_row.addWidget(self.lbl_total_perdida)
        rlay.addLayout(tot_row)

        splitter.addWidget(right)
        splitter.setSizes([380, 620])

        # Botón cerrar
        bot = QHBoxLayout()
        bot.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet("padding: 7px 20px;")
        btn_cerrar.clicked.connect(self.accept)
        bot.addWidget(btn_cerrar)
        root.addLayout(bot)

    # ── Autocompletado de artículos ──────────────────────────────────────────
    def _cargar_completer(self):
        db = SessionLocal()
        try:
            prods = db.query(models.Product).filter_by(is_active=True).all()
            self._cmodel.setStringList([f"{p.art_codigo} - {p.art_descri}" for p in prods])
        finally:
            db.close()

    def _auto_buscar(self):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.buscar_articulo)

    def buscar_articulo(self):
        q = self.txt_art.text().strip()
        if not q:
            return
        codigo = q.split(" - ")[0].strip() if " - " in q else q
        db = SessionLocal()
        try:
            prod = db.query(models.Product).filter(
                (models.Product.art_codigo == codigo) |
                models.Product.art_descri.ilike(f"%{codigo}%")
            ).first()
            if prod:
                self.current_product = {
                    'codigo': prod.art_codigo,
                    'descri': prod.art_descri,
                    'stock': Decimal(str(prod.art_stkini or '0')),
                    'costo': Decimal(str(prod.art_costo or '0')),
                }
                self.lbl_prod_info.setText(f"[{prod.art_codigo}] {prod.art_descri}")
                self.lbl_prod_info.setStyleSheet("color:#1a237e; font-style:normal; font-weight:bold;")
                stock_str = f"{self.current_product['stock']:,.3f}".rstrip('0').rstrip('.')
                self.lbl_stock_actual.setText(f"Stock actual: {stock_str} unidades")
                costo_str = f"{self.current_product['costo']:,.0f}"
                self.txt_costo.setText(costo_str)
                self._actualizar_perdida()
            else:
                self.current_product = None
                self.lbl_prod_info.setText("— Artículo no encontrado —")
                self.lbl_prod_info.setStyleSheet("color:#c62828; font-style:italic;")
                self.lbl_stock_actual.setText("Stock actual: —")
        finally:
            db.close()

    # ── Cálculo de pérdida en tiempo real ───────────────────────────────────
    def _actualizar_perdida(self):
        try:
            qty_str = self.txt_cantidad.text().replace(',', '.').strip()
            qty = Decimal(qty_str) if qty_str else Decimal('0')
            costo_str = parsear_monto(self.txt_costo.text(), "PYG")
            costo = Decimal(costo_str) if costo_str else Decimal('0')
            perdida = (qty * costo).quantize(Decimal('1'))
            self.lbl_perdida.setText(f"₲ {perdida:,.0f}".replace(',', '.'))

            if self.current_product:
                tipo_key = self.cmb_tipo.currentData()
                signo = TIPOS_AJUSTE[tipo_key][1]
                nuevo_stock = self.current_product['stock'] + (Decimal(str(signo)) * qty)
                nuevo_str = f"{nuevo_stock:,.3f}".rstrip('0').rstrip('.')
                color = '#2e7d32' if nuevo_stock >= 0 else '#c62828'
                self.lbl_stock_nuevo.setStyleSheet(f"color: {color};")
                self.lbl_stock_nuevo.setText(f"Stock resultante: {nuevo_str} unidades")
        except (InvalidOperation, ValueError):
            self.lbl_perdida.setText("₲ 0")
            self.lbl_stock_nuevo.setText("Stock resultante: —")

    # ── Registro ─────────────────────────────────────────────────────────────
    def registrar_ajuste(self):
        if not self.current_product:
            QMessageBox.warning(self, "Artículo requerido",
                                "Seleccione un artículo antes de registrar el ajuste.")
            return

        motivo = self.txt_motivo.text().strip()
        if not motivo:
            QMessageBox.warning(self, "Motivo requerido",
                                "Describa el motivo del ajuste.")
            self.txt_motivo.setFocus()
            return

        try:
            qty_str = self.txt_cantidad.text().replace(',', '.').strip()
            cantidad = Decimal(qty_str)
            if cantidad <= Decimal('0'):
                raise ValueError("Cantidad debe ser > 0")
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Cantidad inválida",
                                "Ingrese una cantidad válida mayor a cero.")
            self.txt_cantidad.setFocus()
            return

        try:
            costo_str = parsear_monto(self.txt_costo.text(), "PYG") or "0"
            costo = Decimal(costo_str)
        except InvalidOperation:
            costo = Decimal('0')

        tipo_key = self.cmb_tipo.currentData()
        signo = Decimal(str(TIPOS_AJUSTE[tipo_key][1]))
        perdida = (cantidad * costo).quantize(Decimal('1'))
        delta_stock = signo * cantidad

        resp = QMessageBox.question(
            self, "Confirmar Ajuste",
            f"¿Confirma el ajuste?\n\n"
            f"Artículo: {self.current_product['descri']}\n"
            f"Tipo: {tipo_key}\n"
            f"Cantidad: {cantidad}\n"
            f"Pérdida: ₲ {perdida:,.0f}\n"
            f"Stock actual → {self.current_product['stock']} → {self.current_product['stock'] + delta_stock}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        db = SessionLocal()
        try:
            # 1. Crear registro de ajuste
            ajuste = models.StockAdjustment(
                art_codigo=self.current_product['codigo'],
                tipo=tipo_key,
                cantidad=cantidad,
                motivo=motivo,
                costo_unitario=costo,
                monto_perdida=perdida,
                user_id=self.current_user.get('id'),
            )
            db.add(ajuste)

            # 2. Actualizar stock del producto (art_stkini)
            prod = db.query(models.Product).filter_by(
                art_codigo=self.current_product['codigo']
            ).first()
            if prod:
                nuevo_stock = Decimal(str(prod.art_stkini or '0')) + delta_stock
                prod.art_stkini = nuevo_stock
                
                # Regla de Negocio: Si es devolución (delta_stock > 0), restituir al lote con vencimiento más lejano
                if delta_stock > Decimal('0'):
                    lote_lejano = (db.query(models.ProductBatch)
                                     .filter_by(product_id=prod.id)
                                     .order_by(models.ProductBatch.fecha_vencimiento.desc())
                                     .first())
                    if lote_lejano:
                        lote_lejano.stock_actual = Decimal(str(lote_lejano.stock_actual or '0')) + delta_stock
                    else:
                        # Si no hay lotes (ej. producto nuevo o sin lotes), creamos un lote genérico de devolución
                        from datetime import datetime, timedelta
                        import uuid
                        lote_generico = models.ProductBatch(
                            product_id=prod.id,
                            lote=f"DEV-{datetime.now().strftime('%Y%m%d%H%M')}",
                            fecha_vencimiento=datetime.now() + timedelta(days=365),
                            stock_actual=delta_stock
                        )
                        db.add(lote_generico)
                elif delta_stock < Decimal('0'):
                    # Si es merma, deducir de los lotes FIFO (los más próximos a vencer)
                    qty_to_deduct = abs(delta_stock)
                    batches = (db.query(models.ProductBatch)
                                 .filter(models.ProductBatch.product_id == prod.id, 
                                         models.ProductBatch.stock_actual > 0)
                                 .order_by(models.ProductBatch.fecha_vencimiento.asc())
                                 .all())
                    for b in batches:
                        if qty_to_deduct <= Decimal('0'):
                            break
                        available = Decimal(str(b.stock_actual or '0'))
                        if available >= qty_to_deduct:
                            b.stock_actual = available - qty_to_deduct
                            qty_to_deduct = Decimal('0')
                        else:
                            b.stock_actual = Decimal('0')
                            qty_to_deduct = qty_to_deduct - available
            
            db.commit()

            QMessageBox.information(
                self, "Ajuste Registrado",
                f"✅ Ajuste registrado correctamente.\n"
                f"Stock actualizado: {prod.art_stkini if prod else '—'}"
            )
            # Limpiar formulario
            self.txt_art.clear()
            self.txt_cantidad.clear()
            self.txt_motivo.clear()
            self.current_product = None
            self.lbl_prod_info.setText("— Seleccione un producto —")
            self.lbl_prod_info.setStyleSheet("color:#555; font-style:italic;")
            self.lbl_stock_actual.setText("Stock actual: —")
            self.lbl_stock_nuevo.setText("Stock resultante: —")
            self.lbl_perdida.setText("₲ 0")

            self.load_historial()

        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error al registrar", str(e))
        finally:
            db.close()

    # ── Historial ────────────────────────────────────────────────────────────
    def load_historial(self):
        from datetime import datetime, time
        db = SessionLocal()
        try:
            d_desde = self.date_desde.date().toPyDate()
            d_hasta = self.date_hasta.date().toPyDate()
            dt_desde = datetime.combine(d_desde, time.min)
            dt_hasta = datetime.combine(d_hasta, time.max)

            ajustes = (db.query(models.StockAdjustment)
                         .filter(models.StockAdjustment.fecha >= dt_desde,
                                 models.StockAdjustment.fecha <= dt_hasta)
                         .order_by(models.StockAdjustment.fecha.desc())
                         .all())

            self.tabla_hist.setRowCount(0)
            total_perdida = Decimal('0')

            for row, a in enumerate(ajustes):
                self.tabla_hist.insertRow(row)
                self.tabla_hist.setItem(row, 0, QTableWidgetItem(
                    a.fecha.strftime("%d/%m/%y %H:%M")))
                self.tabla_hist.setItem(row, 1, QTableWidgetItem(a.art_codigo))
                descri = a.product.art_descri if a.product else "—"
                self.tabla_hist.setItem(row, 2, QTableWidgetItem(descri))

                tipo_item = QTableWidgetItem(a.tipo)
                tipo_item.setForeground(TIPO_COLORS.get(a.tipo, QColor('#333')))
                tipo_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.tabla_hist.setItem(row, 3, tipo_item)

                qty_str = f"{Decimal(str(a.cantidad)):,.3f}".rstrip('0').rstrip('.')
                self.tabla_hist.setItem(row, 4, QTableWidgetItem(qty_str))

                perdida = Decimal(str(a.monto_perdida or '0'))
                p_item = QTableWidgetItem(f"{perdida:,.0f}".replace(',', '.'))
                p_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if perdida > Decimal('0'):
                    p_item.setForeground(QColor('#c62828'))
                self.tabla_hist.setItem(row, 5, p_item)

                signo = TIPOS_AJUSTE.get(a.tipo, (None, -1))[1]
                if signo < 0:
                    total_perdida += perdida

            self.lbl_total_perdida.setText(
                f"Total Pérdidas del Período: ₲ {total_perdida:,.0f}".replace(',', '.'))
        finally:
            db.close()
