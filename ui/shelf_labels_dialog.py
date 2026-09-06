"""
ui/shelf_labels_dialog.py
=========================
Diálogo comercial para generación, visualización e impresión de etiquetas de góndola:
  - Formatos: Pliego A4 Adhesivo (24 o 14 etiquetas/hoja) y Rollos Térmicos (60x30mm, 50x25mm).
  - Códigos de barras vectoriales nítidos (EAN-13 / Code-128).
  - Precios destacados en Guaraníes (PYG) y secundarios en Dólares (USD).
  - Vista previa en tiempo real, exportación directa a PDF e impresión por QPrinter.
  - Precisión Decimal estricta en cálculos de cotización y precios.
"""

from decimal import Decimal
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QAbstractItemView, QSpinBox, QComboBox, QCheckBox,
    QSplitter, QWidget, QFileDialog, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QRectF, QSizeF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QPageSize, QPageLayout
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

from database import SessionLocal
import models
from ui.barcode_renderer import draw_shelf_label, render_barcode_pixmap


class ShelfLabelsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏷️ Impresión de Etiquetas de Góndola y Códigos de Barras")
        self.resize(1150, 720)
        self.print_queue = []  # List of dicts: product, copies
        self.usd_rate = Decimal("7500")
        self.cargar_cotizacion_usd()
        self.setup_ui()
        self.cargar_catalogo()

    def cargar_cotizacion_usd(self):
        """Obtiene la tasa de cambio USD activa desde la base de datos."""
        db = SessionLocal()
        try:
            rate_row = db.query(models.CurrencyRate).filter(
                models.CurrencyRate.currency_code == "USD"
            ).order_by(models.CurrencyRate.id.desc()).first()
            if rate_row and rate_row.rate_to_base:
                self.usd_rate = Decimal(str(rate_row.rate_to_base))
        except Exception as e:
            print(f"Aviso: Usando cotización USD por defecto: {e}")
            self.usd_rate = Decimal("7500")
        finally:
            db.close()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ── Barra Superior: Título y Configuración ─────────────────────────
        top_bar = QHBoxLayout()
        lbl_title = QLabel("🏷️ Impresión Masiva de Etiquetas de Góndola")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        top_bar.addWidget(lbl_title)
        top_bar.addStretch()

        self.lbl_usd_info = QLabel(f"💵 Cotización USD: ₲ {int(self.usd_rate):,}".replace(",", "."))
        self.lbl_usd_info.setStyleSheet("font-weight: bold; color: #0369a1; background: #e0f2fe; padding: 4px 8px; border-radius: 4px;")
        top_bar.addWidget(self.lbl_usd_info)
        main_layout.addLayout(top_bar)

        # ── Splitter Principal: Catálogo (Izq) vs Cola + Preview (Der) ─────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # PANEL IZQUIERDO: Catálogo de Productos
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)

        grp_search = QGroupBox("📦 Catálogo de Productos Disponibles")
        search_box = QVBoxLayout(grp_search)

        filter_row = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Filtrar por código o descripción...")
        self.txt_buscar.textChanged.connect(self.filtrar_catalogo)
        filter_row.addWidget(self.txt_buscar)

        btn_refrescar = QPushButton("🔄")
        btn_refrescar.setToolTip("Recargar catálogo")
        btn_refrescar.clicked.connect(self.cargar_catalogo)
        filter_row.addWidget(btn_refrescar)
        search_box.addLayout(filter_row)

        self.table_catalogo = QTableWidget(0, 5)
        self.table_catalogo.setHorizontalHeaderLabels(["Cód.", "Descripción", "Cód. Barras", "Precio (₲)", "Stock"])
        self.table_catalogo.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_catalogo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_catalogo.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_catalogo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_catalogo.itemDoubleClicked.connect(lambda *args: self.agregar_seleccionados())
        search_box.addWidget(self.table_catalogo)

        cat_btn_row = QHBoxLayout()
        btn_add_sel = QPushButton("➕ Agregar Seleccionados")
        btn_add_sel.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 6px;")
        btn_add_sel.clicked.connect(self.agregar_seleccionados)

        btn_add_all = QPushButton("📦 Agregar Todos")
        btn_add_all.setStyleSheet("background-color: #475569; color: white; font-weight: bold; padding: 6px;")
        btn_add_all.clicked.connect(self.agregar_todos)

        cat_btn_row.addWidget(btn_add_sel)
        cat_btn_row.addWidget(btn_add_all)
        search_box.addLayout(cat_btn_row)

        left_layout.addWidget(grp_search)
        splitter.addWidget(left_panel)

        # PANEL DERECHO: Cola de Impresión + Configuración + Previsualizador
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 0, 0, 0)

        # 1. Configuración de Formato
        grp_cfg = QGroupBox("⚙️ Configuración del Formato de Etiquetas")
        cfg_layout = QGridLayout(grp_cfg)

        cfg_layout.addWidget(QLabel("Formato / Soporte:"), 0, 0)
        self.cmb_formato = QComboBox()
        self.cmb_formato.addItems([
            "📄 Hoja A4 Adhesiva (3 columnas x 8 filas = 24 etiquetas)",
            "📄 Hoja A4 Adhesiva (2 columnas x 7 filas = 14 etiquetas grandes)",
            "🏷️ Rollo Térmico 60x30 mm (Zebra/Xprinter 1 col)",
            "🏷️ Rollo Térmico 50x25 mm (Zebra/Xprinter 1 col)"
        ])
        self.cmb_formato.currentIndexChanged.connect(self.actualizar_vista_previa)
        cfg_layout.addWidget(self.cmb_formato, 0, 1, 1, 3)

        self.chk_show_usd = QCheckBox("Mostrar Precio en USD")
        self.chk_show_usd.setChecked(True)
        self.chk_show_usd.toggled.connect(self.actualizar_vista_previa)
        cfg_layout.addWidget(self.chk_show_usd, 1, 0)

        self.chk_show_date = QCheckBox("Mostrar Fecha de Emisión")
        self.chk_show_date.setChecked(True)
        self.chk_show_date.toggled.connect(self.actualizar_vista_previa)
        cfg_layout.addWidget(self.chk_show_date, 1, 1)

        self.txt_store_name = QLineEdit("SUPERMERCADO CENTRAL")
        self.txt_store_name.setPlaceholderText("Nombre del comercio...")
        self.txt_store_name.textChanged.connect(self.actualizar_vista_previa)
        cfg_layout.addWidget(QLabel("Encabezado:"), 1, 2)
        cfg_layout.addWidget(self.txt_store_name, 1, 3)

        right_layout.addWidget(grp_cfg)

        # 2. Cola de Impresión
        grp_queue = QGroupBox("📋 Cola de Impresión de Etiquetas")
        queue_layout = QVBoxLayout(grp_queue)

        self.table_queue = QTableWidget(0, 5)
        self.table_queue.setHorizontalHeaderLabels(["Cód.", "Descripción", "Precio (₲)", "Copias", "Eliminar"])
        self.table_queue.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_queue.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_queue.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        queue_layout.addWidget(self.table_queue)

        queue_btn_row = QHBoxLayout()
        self.lbl_total_labels = QLabel("Total etiquetas: 0")
        self.lbl_total_labels.setStyleSheet("font-weight: bold; color: #047857; font-size: 13px;")
        queue_btn_row.addWidget(self.lbl_total_labels)
        queue_btn_row.addStretch()

        btn_clear_queue = QPushButton("🗑️ Limpiar Cola")
        btn_clear_queue.setStyleSheet("background-color: #fee2e2; color: #b91c1c; font-weight: bold; padding: 4px 8px;")
        btn_clear_queue.clicked.connect(self.limpiar_cola)
        queue_btn_row.addWidget(btn_clear_queue)
        queue_layout.addLayout(queue_btn_row)

        right_layout.addWidget(grp_queue, stretch=2)

        # 3. Vista Previa en Vivo de una Etiqueta
        grp_preview = QGroupBox("👁️ Vista Previa en Vivo (Etiqueta Individual)")
        preview_layout = QVBoxLayout(grp_preview)
        
        self.lbl_preview = QLabel("Agregue productos a la cola para ver la vista previa")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setMinimumHeight(120)
        self.lbl_preview.setStyleSheet("background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px;")
        preview_layout.addWidget(self.lbl_preview)

        right_layout.addWidget(grp_preview, stretch=1)
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 700])
        main_layout.addWidget(splitter, stretch=1)

        # ── Barra Inferior: Acciones de Impresión ──────────────────────────
        bottom_bar = QHBoxLayout()
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet("padding: 8px 16px;")
        btn_cerrar.clicked.connect(self.reject)
        bottom_bar.addWidget(btn_cerrar)
        
        bottom_bar.addStretch()

        btn_preview_full = QPushButton("🔍 Vista Previa Impresión")
        btn_preview_full.setStyleSheet("background-color: #0ea5e9; color: white; font-weight: bold; padding: 10px 16px;")
        btn_preview_full.clicked.connect(self.abrir_vista_previa_completa)
        bottom_bar.addWidget(btn_preview_full)

        btn_export_pdf = QPushButton("📄 Guardar en PDF")
        btn_export_pdf.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px 16px;")
        btn_export_pdf.clicked.connect(self.exportar_pdf)
        bottom_bar.addWidget(btn_export_pdf)

        btn_imprimir = QPushButton("🖨️ Imprimir Etiquetas")
        btn_imprimir.setStyleSheet("background-color: #059669; color: white; font-weight: bold; font-size: 13px; padding: 10px 20px;")
        btn_imprimir.clicked.connect(self.imprimir_etiquetas)
        bottom_bar.addWidget(btn_imprimir)

        main_layout.addLayout(bottom_bar)

    def cargar_catalogo(self):
        """Carga todos los productos activos de la base de datos."""
        db = SessionLocal()
        self.todos_los_productos = []
        try:
            prods = db.query(models.Product).filter(
                models.Product.is_active == True
            ).order_by(models.Product.art_descri).all()
            for p in prods:
                self.todos_los_productos.append({
                    "art_codigo": str(p.art_codigo),
                    "art_descri": str(p.art_descri or ""),
                    "art_codbar": str(p.art_codbar or p.art_codigo or ""),
                    "art_preven": Decimal(str(p.art_preven or "0")),
                    "art_stkact": Decimal(str(p.art_stkact or "0")),
                })
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando catálogo: {e}")
        finally:
            db.close()

        self.poblar_tabla_catalogo(self.todos_los_productos)

    def poblar_tabla_catalogo(self, items):
        self.table_catalogo.setRowCount(0)
        for i, item in enumerate(items):
            self.table_catalogo.insertRow(i)
            self.table_catalogo.setItem(i, 0, QTableWidgetItem(item["art_codigo"]))
            self.table_catalogo.setItem(i, 1, QTableWidgetItem(item["art_descri"]))
            self.table_catalogo.setItem(i, 2, QTableWidgetItem(item["art_codbar"]))
            
            p_val = f"₲ {int(item['art_preven']):,}".replace(",", ".")
            it_p = QTableWidgetItem(p_val)
            it_p.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_catalogo.setItem(i, 3, it_p)

            stk_val = f"{item['art_stkact']:.2f}"
            it_stk = QTableWidgetItem(stk_val)
            it_stk.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_catalogo.setItem(i, 4, it_stk)

    def filtrar_catalogo(self, text):
        t = text.strip().lower()
        if not t:
            self.poblar_tabla_catalogo(self.todos_los_productos)
            return

        filtrados = [
            p for p in self.todos_los_productos
            if t in p["art_codigo"].lower() or t in p["art_descri"].lower() or t in p["art_codbar"].lower()
        ]
        self.poblar_tabla_catalogo(filtrados)

    def agregar_seleccionados(self):
        selected_rows = sorted(set(idx.row() for idx in self.table_catalogo.selectedIndexes()))
        if not selected_rows:
            return

        for r in selected_rows:
            cod = self.table_catalogo.item(r, 0).text()
            item = next((p for p in self.todos_los_productos if p["art_codigo"] == cod), None)
            if item:
                self._add_to_queue(item)

        self.actualizar_tabla_cola()

    def agregar_todos(self):
        for item in self.todos_los_productos:
            self._add_to_queue(item)
        self.actualizar_tabla_cola()

    def _add_to_queue(self, item, copies=1):
        # Si ya está en la cola, incrementa las copias
        for q in self.print_queue:
            if q["item"]["art_codigo"] == item["art_codigo"]:
                q["copies"] += copies
                return
        self.print_queue.append({"item": item, "copies": copies})

    def actualizar_tabla_cola(self):
        self.table_queue.setRowCount(0)
        total_copias = 0
        for i, entry in enumerate(self.print_queue):
            self.table_queue.insertRow(i)
            item = entry["item"]
            copies = entry["copies"]
            total_copias += copies

            self.table_queue.setItem(i, 0, QTableWidgetItem(item["art_codigo"]))
            self.table_queue.setItem(i, 1, QTableWidgetItem(item["art_descri"]))
            
            p_val = f"₲ {int(item['art_preven']):,}".replace(",", ".")
            it_p = QTableWidgetItem(p_val)
            it_p.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_queue.setItem(i, 2, it_p)

            # SpinBox para editar copias directamente
            spn = QSpinBox()
            spn.setRange(1, 999)
            spn.setValue(copies)
            spn.valueChanged.connect(lambda val, idx=i: self._on_copies_changed(idx, val))
            self.table_queue.setCellWidget(i, 3, spn)

            # Botón eliminar
            btn_del = QPushButton("❌")
            btn_del.setStyleSheet("color: red; font-weight: bold;")
            btn_del.clicked.connect(lambda _, idx=i: self._remove_from_queue(idx))
            self.table_queue.setCellWidget(i, 4, btn_del)

        self.lbl_total_labels.setText(f"Total etiquetas a imprimir: {total_copias}")
        self.actualizar_vista_previa()

    def _on_copies_changed(self, idx, val):
        if 0 <= idx < len(self.print_queue):
            self.print_queue[idx]["copies"] = val
            total = sum(q["copies"] for q in self.print_queue)
            self.lbl_total_labels.setText(f"Total etiquetas a imprimir: {total}")

    def _remove_from_queue(self, idx):
        if 0 <= idx < len(self.print_queue):
            del self.print_queue[idx]
            self.actualizar_tabla_cola()

    def limpiar_cola(self):
        self.print_queue.clear()
        self.actualizar_tabla_cola()

    def actualizar_vista_previa(self):
        """Genera un QPixmap con la previsualización de la primera etiqueta."""
        if not self.print_queue:
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.setText("Agregue productos a la cola para ver la vista previa")
            return

        primer_item = self.print_queue[0]["item"]
        w = 340
        h = 160
        pm = QPixmap(w, h)
        pm.fill(QColor("white"))
        
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        draw_shelf_label(
            painter,
            QRectF(0, 0, w, h),
            primer_item,
            store_name=self.txt_store_name.text().strip() or "SUPERMERCADO CENTRAL",
            show_usd=self.chk_show_usd.isChecked(),
            show_date=self.chk_show_date.isChecked(),
            rate_usd=self.usd_rate
        )
        painter.end()

        self.lbl_preview.setText("")
        self.lbl_preview.setPixmap(pm)

    def _render_all_labels_to_printer(self, printer: QPrinter):
        """
        Dibuja todas las etiquetas de la cola sobre el QPrinter según el formato seleccionado.
        Maneja paginado automático para pliegos A4 y rollos continuos.
        """
        fmt_idx = self.cmb_formato.currentIndex()
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
        pw = page_rect.width()
        ph = page_rect.height()

        store_name = self.txt_store_name.text().strip() or "SUPERMERCADO CENTRAL"
        show_usd = self.chk_show_usd.isChecked()
        show_date = self.chk_show_date.isChecked()

        # Lista aplanada de todas las etiquetas a imprimir (duplicadas según 'copies')
        labels_to_print = []
        for q in self.print_queue:
            for _ in range(q["copies"]):
                labels_to_print.append(q["item"])

        if not labels_to_print:
            painter.end()
            return

        if fmt_idx == 0:
            # ── A4: 3 Columnas x 8 Filas (24 por hoja) ──
            cols = 3
            rows = 8
            margin_x = pw * 0.03
            margin_y = ph * 0.03
            label_w = (pw - (margin_x * 2)) / cols
            label_h = (ph - (margin_y * 2)) / rows

            curr_idx = 0
            while curr_idx < len(labels_to_print):
                if curr_idx > 0:
                    printer.newPage()

                for r in range(rows):
                    for c in range(cols):
                        if curr_idx >= len(labels_to_print):
                            break
                        item = labels_to_print[curr_idx]
                        lx = margin_x + (c * label_w)
                        ly = margin_y + (r * label_h)
                        rect = QRectF(lx + 2, ly + 2, label_w - 4, label_h - 4)
                        draw_shelf_label(painter, rect, item, store_name, show_usd, show_date, self.usd_rate)
                        curr_idx += 1

        elif fmt_idx == 1:
            # ── A4: 2 Columnas x 7 Filas (14 por hoja, más grandes) ──
            cols = 2
            rows = 7
            margin_x = pw * 0.04
            margin_y = ph * 0.04
            label_w = (pw - (margin_x * 2)) / cols
            label_h = (ph - (margin_y * 2)) / rows

            curr_idx = 0
            while curr_idx < len(labels_to_print):
                if curr_idx > 0:
                    printer.newPage()

                for r in range(rows):
                    for c in range(cols):
                        if curr_idx >= len(labels_to_print):
                            break
                        item = labels_to_print[curr_idx]
                        lx = margin_x + (c * label_w)
                        ly = margin_y + (r * label_h)
                        rect = QRectF(lx + 2, ly + 2, label_w - 4, label_h - 4)
                        draw_shelf_label(painter, rect, item, store_name, show_usd, show_date, self.usd_rate)
                        curr_idx += 1

        else:
            # ── Rollo Térmico (1 etiqueta por página continua) ──
            for i, item in enumerate(labels_to_print):
                if i > 0:
                    printer.newPage()
                rect = QRectF(4, 4, pw - 8, ph - 8)
                draw_shelf_label(painter, rect, item, store_name, show_usd, show_date, self.usd_rate)

        painter.end()

    def abrir_vista_previa_completa(self):
        if not self.print_queue:
            QMessageBox.warning(self, "Cola Vacía", "Debe agregar al menos un producto a la cola de impresión.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        fmt_idx = self.cmb_formato.currentIndex()
        if fmt_idx in (0, 1):
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        else:
            # Térmica 60x30 o 50x25
            sz = QSizeF(60, 30) if fmt_idx == 2 else QSizeF(50, 25)
            printer.setPageSize(QPageSize(sz, QPageSize.Unit.Millimeter))

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Previsualización de Impresión de Etiquetas")
        preview.paintRequested.connect(self._render_all_labels_to_printer)
        preview.exec()

    def exportar_pdf(self):
        if not self.print_queue:
            QMessageBox.warning(self, "Cola Vacía", "Debe agregar al menos un producto a la cola de impresión.")
            return

        fecha_str = datetime.date.today().strftime("%Y%m%d")
        default_name = f"etiquetas_gondola_{fecha_str}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Etiquetas en PDF", default_name, "Archivos PDF (*.pdf)")
        if not file_path:
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)

        fmt_idx = self.cmb_formato.currentIndex()
        if fmt_idx in (0, 1):
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        else:
            sz = QSizeF(60, 30) if fmt_idx == 2 else QSizeF(50, 25)
            printer.setPageSize(QPageSize(sz, QPageSize.Unit.Millimeter))

        self._render_all_labels_to_printer(printer)
        QMessageBox.information(self, "PDF Generado", f"El archivo PDF ha sido generado exitosamente en:\n{file_path}")

    def imprimir_etiquetas(self):
        if not self.print_queue:
            QMessageBox.warning(self, "Cola Vacía", "Debe agregar al menos un producto a la cola de impresión.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        fmt_idx = self.cmb_formato.currentIndex()
        if fmt_idx in (0, 1):
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        else:
            sz = QSizeF(60, 30) if fmt_idx == 2 else QSizeF(50, 25)
            printer.setPageSize(QPageSize(sz, QPageSize.Unit.Millimeter))

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Imprimir Etiquetas")
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self._render_all_labels_to_printer(printer)
            QMessageBox.information(self, "Éxito", "Trabajo de impresión enviado correctamente.")
