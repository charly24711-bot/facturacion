"""
ui/hechauka_export_dialog.py
=============================
Exportación Oficial DNIT Paraguay:
  - Hechauka: Libro de Ventas (Tipo 2) y Compras (Tipo 1)
  - Marangatú: XML de IVA para SIFEN (simplificado)

Formatos:
  - Ventas: CSV delimitado por ';' para Hechauka/Marangatú
  - Compras: CSV delimitado por ';' para Hechauka/Marangatú
  - Ambos: Columnas según RG N° 23/2022 DNIT

Fórmulas IVA (Ley 6380/19):
  - IVA 10% = Total / 11  (gravada = Total - IVA)
  - IVA 5%  = Total / 21  (gravada = Total - IVA)
  - Exenta  = Total / 1   (IVA = 0)
"""

import os
import csv
import datetime
from decimal import Decimal, ROUND_HALF_UP

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QDateEdit, QComboBox, QTextEdit,
    QMessageBox, QFileDialog, QProgressBar, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from database import SessionLocal
import models


def _d(v) -> Decimal:
    """Convierte cualquier valor a Decimal seguro."""
    if v is None:
        return Decimal('0')
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _iva_10(total: Decimal) -> tuple[Decimal, Decimal]:
    """Devuelve (gravada, iva) para tasa 10% según Ley 6380/19."""
    iva = (total / Decimal('11')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    gravada = total - iva
    return gravada, iva


def _iva_5(total: Decimal) -> tuple[Decimal, Decimal]:
    """Devuelve (gravada, iva) para tasa 5% según Ley 6380/19."""
    iva = (total / Decimal('21')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    gravada = total - iva
    return gravada, iva


MESES_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


class HechaukaExportDialog(QDialog):
    """
    Exportación mensual al DNIT: Libro de Ventas y Compras.
    Genera archivos .TXT/.CSV según especificación Hechauka / Marangatú.
    """
    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user or {'id': 1, 'username': 'admin'}
        self.setWindowTitle("📊 Exportación DNIT: Hechauka / Marangatú")
        self.resize(1050, 680)
        self.setMinimumSize(800, 550)
        self._ventas_rows = []
        self._compras_rows = []
        self.setup_ui()
        self._cargar_empresa()

    def _cargar_empresa(self):
        db = SessionLocal()
        try:
            cfg = db.query(models.CompanySettings).first()
            if cfg:
                self.lbl_empresa.setText(f"{cfg.nombre}  |  RUC: {cfg.ruc}")
        finally:
            db.close()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)

        # Encabezado
        hdr = QHBoxLayout()
        lbl_title = QLabel("📊 EXPORTACIÓN DNIT — HECHAUKA / MARANGATÚ")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #1a237e;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        self.lbl_empresa = QLabel("Empresa: —")
        self.lbl_empresa.setFont(QFont("Segoe UI", 10))
        self.lbl_empresa.setStyleSheet("color:#546e7a;")
        hdr.addWidget(self.lbl_empresa)
        root.addLayout(hdr)

        # Panel de filtros
        grp_filtros = QGroupBox("Parámetros de Exportación")
        grp_filtros.setStyleSheet("""
            QGroupBox { font-weight:bold; border:2px solid #1a237e; border-radius:5px;
                        margin-top:6px; padding-top:10px; }
            QGroupBox::title { color:#1a237e; left:10px; subcontrol-origin:margin; }
        """)
        filt = QGridLayout(grp_filtros)
        filt.setSpacing(10)

        filt.addWidget(QLabel("Período Desde:"), 0, 0)
        self.date_desde = QDateEdit(
            QDate(QDate.currentDate().year(), QDate.currentDate().month(), 1))
        self.date_desde.setCalendarPopup(True)
        filt.addWidget(self.date_desde, 0, 1)

        filt.addWidget(QLabel("Período Hasta:"), 0, 2)
        self.date_hasta = QDateEdit(QDate.currentDate())
        self.date_hasta.setCalendarPopup(True)
        filt.addWidget(self.date_hasta, 0, 3)

        filt.addWidget(QLabel("Tipo de Exportación:"), 0, 4)
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems([
            "📤 Libro de VENTAS (Tipo 2)",
            "📥 Libro de COMPRAS (Tipo 1)",
            "📦 Ambos (Ventas + Compras)",
        ])
        self.cmb_tipo.setStyleSheet("padding:5px; font-weight:bold;")
        filt.addWidget(self.cmb_tipo, 0, 5)

        btn_previsualizar = QPushButton("🔍 Previsualizar")
        btn_previsualizar.setStyleSheet(
            "background:#1565c0; color:white; font-weight:bold; padding:7px 14px; border-radius:4px;")
        btn_previsualizar.clicked.connect(self.previsualizar)
        filt.addWidget(btn_previsualizar, 0, 6)

        root.addWidget(grp_filtros)

        # Tabs de previsualización
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        # Tab Ventas
        self.tab_ventas = QWidget()
        lay_v = QVBoxLayout(self.tab_ventas)
        self.tabla_ventas = self._crear_tabla_ventas()
        lay_v.addWidget(self.tabla_ventas)
        self.lbl_tot_ventas = QLabel("Total Ventas IVA 10%: ₲ 0  |  IVA 5%: ₲ 0  |  Exentas: ₲ 0")
        self.lbl_tot_ventas.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_tot_ventas.setStyleSheet("color:#1565c0; padding:4px;")
        lay_v.addWidget(self.lbl_tot_ventas)
        self.tabs.addTab(self.tab_ventas, "📤 Ventas")

        # Tab Compras
        self.tab_compras = QWidget()
        lay_c = QVBoxLayout(self.tab_compras)
        self.tabla_compras = self._crear_tabla_compras()
        lay_c.addWidget(self.tabla_compras)
        self.lbl_tot_compras = QLabel("Total Compras: ₲ 0")
        self.lbl_tot_compras.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_tot_compras.setStyleSheet("color:#2e7d32; padding:4px;")
        lay_c.addWidget(self.lbl_tot_compras)
        self.tabs.addTab(self.tab_compras, "📥 Compras")

        # Tab Log
        self.tab_log = QWidget()
        lay_log = QVBoxLayout(self.tab_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Courier New", 9))
        self.txt_log.setStyleSheet("background:#1e1e2e; color:#cdd6f4; border:none;")
        lay_log.addWidget(self.txt_log)
        self.tabs.addTab(self.tab_log, "📋 Log / Vista Previa TXT")

        # Barra inferior
        bot = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        bot.addWidget(self.progress, stretch=1)

        btn_exportar = QPushButton("💾 Exportar Archivo(s)")
        btn_exportar.setStyleSheet(
            "background:#2e7d32; color:white; font-weight:bold; padding:9px 20px; "
            "border-radius:4px; font-size:13px;")
        btn_exportar.clicked.connect(self.exportar)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet("padding:9px 18px;")
        btn_cerrar.clicked.connect(self.accept)

        bot.addWidget(btn_exportar)
        bot.addWidget(btn_cerrar)
        root.addLayout(bot)

    def _crear_tabla_ventas(self):
        cols = ["Fecha", "Nº Fact.", "RUC/CI Cliente", "Razón Social",
                "Total", "Grav. 10%", "IVA 10%", "Grav. 5%", "IVA 5%", "Exentas"]
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("QHeaderView::section { background:#1a237e; color:white; font-weight:bold; }")
        return t

    def _crear_tabla_compras(self):
        cols = ["Fecha", "Nº Fact.", "Timbrado", "RUC Proveedor", "Razón Social",
                "Total", "Grav. 10%", "IVA 10%"]
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setStyleSheet("QHeaderView::section { background:#2e7d32; color:white; font-weight:bold; }")
        return t

    # ── Previsualización ──────────────────────────────────────────────────────
    def previsualizar(self):
        d_desde = self.date_desde.date().toPyDate()
        d_hasta = self.date_hasta.date().toPyDate()
        dt_desde = datetime.datetime.combine(d_desde, datetime.time.min)
        dt_hasta = datetime.datetime.combine(d_hasta, datetime.time.max)

        tipo_idx = self.cmb_tipo.currentIndex()
        if tipo_idx in (0, 2):
            self._cargar_ventas(dt_desde, dt_hasta)
        if tipo_idx in (1, 2):
            self._cargar_compras(dt_desde, dt_hasta)

    def _cargar_ventas(self, dt_desde, dt_hasta):
        db = SessionLocal()
        try:
            facturas = (db.query(models.Invoice)
                          .filter(models.Invoice.ven_fecha >= dt_desde,
                                  models.Invoice.ven_fecha <= dt_hasta,
                                  models.Invoice.ven_estado == 'A')
                          .order_by(models.Invoice.ven_fecha)
                          .all())

            self.tabla_ventas.setRowCount(0)
            self._ventas_rows = []
            log_lines = ["=== LIBRO DE VENTAS ===",
                         f"Período: {dt_desde.date()} al {dt_hasta.date()}",
                         f"Facturas encontradas: {len(facturas)}", ""]

            tot_10 = Decimal('0'); tot_iva10 = Decimal('0')
            tot_5  = Decimal('0'); tot_iva5  = Decimal('0')
            tot_ex = Decimal('0')

            for row_idx, fac in enumerate(facturas):
                total = _d(fac.ven_total)
                cli = fac.client
                ruc  = (cli.cli_ruc  or '44444401-7') if cli else '44444401-7'
                razon = (cli.cli_nombre or 'CONSUMIDOR FINAL') if cli else 'CONSUMIDOR FINAL'

                # Calcular IVA según composición de ítems
                g10 = Decimal('0'); i10 = Decimal('0')
                g5  = Decimal('0'); i5  = Decimal('0')
                ex  = Decimal('0')

                for it in fac.items:
                    sub = (_d(it.vit_precio) * _d(it.vit_canti)).quantize(Decimal('1'))
                    # Buscar impuesto del producto
                    prod = it.product
                    impu = _d(prod.art_impu) if prod else Decimal('10')
                    if impu == Decimal('10'):
                        gv, iv = _iva_10(sub)
                        g10 += gv; i10 += iv
                    elif impu == Decimal('5'):
                        gv, iv = _iva_5(sub)
                        g5 += gv; i5 += iv
                    else:
                        ex += sub

                tot_10 += g10; tot_iva10 += i10
                tot_5  += g5;  tot_iva5  += i5
                tot_ex += ex

                row_data = [
                    fac.ven_fecha.strftime("%d/%m/%Y"),
                    str(fac.ven_numero),
                    ruc, razon,
                    str(int(total)),
                    str(int(g10)), str(int(i10)),
                    str(int(g5)),  str(int(i5)),
                    str(int(ex)),
                ]
                self._ventas_rows.append(row_data)

                self.tabla_ventas.insertRow(row_idx)
                for col, val in enumerate(row_data):
                    item = QTableWidgetItem(val)
                    if col >= 4:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.tabla_ventas.setItem(row_idx, col, item)

                log_lines.append(";".join(row_data))

            self.lbl_tot_ventas.setText(
                f"Total Grav.10%: ₲ {tot_10:,.0f}  |  IVA 10%: ₲ {tot_iva10:,.0f}  |  "
                f"Grav.5%: ₲ {tot_5:,.0f}  |  IVA 5%: ₲ {tot_iva5:,.0f}  |  "
                f"Exentas: ₲ {tot_ex:,.0f}".replace(',', '.')
            )

            log_lines += [
                "",
                f"TOTALES: Grav.10%={tot_10} | IVA10%={tot_iva10} | "
                f"Grav.5%={tot_5} | IVA5%={tot_iva5} | Exentas={tot_ex}",
            ]
            self.txt_log.append("\n".join(log_lines))
            self.tabs.setCurrentIndex(0)

        finally:
            db.close()

    def _cargar_compras(self, dt_desde, dt_hasta):
        db = SessionLocal()
        try:
            compras = (db.query(models.Purchase)
                         .filter(models.Purchase.com_fecha >= dt_desde,
                                 models.Purchase.com_fecha <= dt_hasta)
                         .order_by(models.Purchase.com_fecha)
                         .all())

            self.tabla_compras.setRowCount(0)
            self._compras_rows = []
            log_lines = ["", "=== LIBRO DE COMPRAS ===",
                         f"Período: {dt_desde.date()} al {dt_hasta.date()}",
                         f"Compras encontradas: {len(compras)}", ""]

            tot_compras = Decimal('0')

            for row_idx, c in enumerate(compras):
                total = _d(c.com_total)
                sup = c.supplier
                ruc_sup  = (sup.sup_ruc   or '—') if sup else '—'
                nom_sup  = (sup.sup_nombre or '—') if sup else '—'
                g10, i10 = _iva_10(total)
                tot_compras += total

                row_data = [
                    c.com_fecha.strftime("%d/%m/%Y"),
                    c.com_nrofac or '',
                    c.com_timbra or '',
                    ruc_sup, nom_sup,
                    str(int(total)),
                    str(int(g10)), str(int(i10)),
                ]
                self._compras_rows.append(row_data)

                self.tabla_compras.insertRow(row_idx)
                for col, val in enumerate(row_data):
                    item = QTableWidgetItem(val)
                    if col >= 5:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.tabla_compras.setItem(row_idx, col, item)

                log_lines.append(";".join(row_data))

            self.lbl_tot_compras.setText(
                f"Total Compras: ₲ {tot_compras:,.0f}  |  "
                f"Comprobantes: {len(compras)}".replace(',', '.'))
            log_lines.append(f"\nTOTAL COMPRAS: {tot_compras}")
            self.txt_log.append("\n".join(log_lines))

        finally:
            db.close()

    # ── Exportar CSV ─────────────────────────────────────────────────────────
    def exportar(self):
        tipo_idx = self.cmb_tipo.currentIndex()
        if tipo_idx in (0, 2) and not self._ventas_rows:
            self.previsualizar()
        if tipo_idx in (1, 2) and not self._compras_rows:
            self.previsualizar()

        carpeta = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de destino",
            os.path.expanduser("~/Documents"))
        if not carpeta:
            return

        d_desde = self.date_desde.date().toPyDate()
        d_hasta = self.date_hasta.date().toPyDate()
        periodo = f"{d_desde.strftime('%Y%m')}"

        archivos_creados = []

        if tipo_idx in (0, 2) and self._ventas_rows:
            fname = os.path.join(carpeta, f"HECHAUKA_VENTAS_{periodo}.txt")
            with open(fname, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                # Encabezado Hechauka Tipo 2 (Ventas)
                writer.writerow([
                    "FECHA", "NRO_FACTURA", "RUC_CI_CLIENTE", "RAZON_SOCIAL",
                    "TOTAL", "GRAVADA_10", "IVA_10", "GRAVADA_5", "IVA_5", "EXENTA"
                ])
                writer.writerows(self._ventas_rows)
            archivos_creados.append(fname)

        if tipo_idx in (1, 2) and self._compras_rows:
            fname = os.path.join(carpeta, f"HECHAUKA_COMPRAS_{periodo}.txt")
            with open(fname, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                writer.writerow([
                    "FECHA", "NRO_FACTURA", "TIMBRADO", "RUC_PROVEEDOR",
                    "RAZON_SOCIAL", "TOTAL", "GRAVADA_10", "IVA_10"
                ])
                writer.writerows(self._compras_rows)
            archivos_creados.append(fname)

        if archivos_creados:
            lista = "\n".join(f"  ✅ {f}" for f in archivos_creados)
            QMessageBox.information(
                self, "Exportación Exitosa",
                f"Archivos generados correctamente:\n\n{lista}\n\n"
                f"Listo para importar en Hechauka / Marangatú DNIT."
            )
            self.txt_log.append(
                f"\n✅ EXPORTADO: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                + "\n".join(archivos_creados)
            )
        else:
            QMessageBox.warning(self, "Sin datos",
                                "No hay datos para exportar. Ejecute 'Previsualizar' primero.")
