"""
ui/backoffice_fiscal_dialog.py - Panel de Back-Office, Liquidación Fiscal y Exportador SIFEN v150
Permite a gerencia y contabilidad auditar la liquidación de IVA, verificar comprobantes KuDE
y generar los lotes JSON oficiales y Libros de Ventas.
"""

import os
import tempfile
import webbrowser
import datetime
from decimal import Decimal

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QFileDialog, QMessageBox, QFrame, QWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from database import SessionLocal
import models
from utils.fiscal_engine import FiscalEngine


class BackofficeFiscalDialog(QDialog):
    """Diálogo de auditoría fiscal, comprobantes KuDE y exportación SIFEN."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏢 Panel de Auditoría Fiscal y Liquidación KuDE / SIFEN")
        self.resize(1150, 750)
        self.setMinimumSize(950, 600)

        self._init_ui()
        self._set_default_dates()
        self.consultar_datos()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1117;
                color: #a9b1d6;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #e0e6ed;
            }
            QPushButton {
                background-color: #1c2333;
                border: 1px solid #2a3550;
                border-radius: 6px;
                padding: 6px 14px;
                color: #e0e6ed;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2a3550;
                color: #ffffff;
            }
            QDateEdit, QLineEdit {
                background-color: #131929;
                border: 1px solid #2a3550;
                border-radius: 6px;
                padding: 6px 10px;
                color: #9ece6a;
                font-weight: bold;
                font-size: 13px;
            }
            QDateEdit:focus, QLineEdit:focus {
                border-color: #7aa2f7;
            }
            QTableWidget {
                background-color: #131929;
                alternate-background-color: #182033;
                gridline-color: #2a3550;
                border: 1px solid #2a3550;
                border-radius: 6px;
                color: #e0e6ed;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1c2333;
                color: #7aa2f7;
                padding: 6px;
                font-weight: bold;
                border: 1px solid #2a3550;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # --- ENCABEZADO Y FILTRO DE FECHAS ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #161b26; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(10)

        lbl_title = QLabel("📊 Liquidación Fiscal KuDE / SIFEN")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #7aa2f7;")
        h_layout.addWidget(lbl_title)

        h_layout.addStretch()

        # Botones rápidos
        btn_hoy = QPushButton("Hoy")
        btn_hoy.clicked.connect(self._set_today)
        btn_semana = QPushButton("Esta Semana")
        btn_semana.clicked.connect(self._set_this_week)
        btn_mes = QPushButton("Este Mes")
        btn_mes.clicked.connect(self._set_this_month)

        h_layout.addWidget(btn_hoy)
        h_layout.addWidget(btn_semana)
        h_layout.addWidget(btn_mes)

        h_layout.addWidget(QLabel("Desde:"))
        self.dt_desde = QDateEdit()
        self.dt_desde.setCalendarPopup(True)
        self.dt_desde.setDisplayFormat("dd/MM/yyyy")
        h_layout.addWidget(self.dt_desde)

        h_layout.addWidget(QLabel("Hasta:"))
        self.dt_hasta = QDateEdit()
        self.dt_hasta.setCalendarPopup(True)
        self.dt_hasta.setDisplayFormat("dd/MM/yyyy")
        h_layout.addWidget(self.dt_hasta)

        btn_consultar = QPushButton("🔍 Consultar")
        btn_consultar.setStyleSheet("background-color: #1a3b5c; color: #7aa2f7; border-color: #2b5b8c;")
        btn_consultar.clicked.connect(self.consultar_datos)
        h_layout.addWidget(btn_consultar)

        layout.addWidget(header_frame)

        # --- TARJETAS KPI DE RESUMEN ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        def make_kpi(title, color="#9ece6a"):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #161b26;
                    border: 1px solid #2a3550;
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(10, 6, 10, 6)
            c_layout.setSpacing(4)
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-size: 11px; font-weight: bold; color: #7aa2f7; text-transform: uppercase;")
            lbl_v = QLabel("₲ 0")
            lbl_v.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color}; font-family: 'Consolas', monospace;")
            c_layout.addWidget(lbl_t)
            c_layout.addWidget(lbl_v)
            return card, lbl_v

        self.card_total, self.lbl_kpi_total = make_kpi("Total Facturado (PYG)", "#9ece6a")
        self.card_iva10, self.lbl_kpi_iva10 = make_kpi("IVA 10% Liquidado", "#7aa2f7")
        self.card_iva5, self.lbl_kpi_iva5 = make_kpi("IVA 5% Liquidado", "#ffd166")
        self.card_exenta, self.lbl_kpi_exenta = make_kpi("Ventas Exentas", "#a9b1d6")
        self.card_docs, self.lbl_kpi_docs = make_kpi("Total Facturas", "#06d6a0")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_iva10)
        kpi_layout.addWidget(self.card_iva5)
        kpi_layout.addWidget(self.card_exenta)
        kpi_layout.addWidget(self.card_docs)
        layout.addLayout(kpi_layout)

        # --- FILTRO Y TABLA DE COMPROBANTES ---
        table_header_layout = QHBoxLayout()
        lbl_subtitle = QLabel("Comprobantes Electrónicos Emitidos (KuDE)")
        lbl_subtitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #7aa2f7;")
        table_header_layout.addWidget(lbl_subtitle)

        table_header_layout.addStretch()

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filtrar por RUC, Cliente o Factura...")
        self.txt_filter.setFixedWidth(280)
        self.txt_filter.textChanged.connect(self.consultar_datos)
        table_header_layout.addWidget(self.txt_filter)

        layout.addLayout(table_header_layout)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Nro Factura", "Fecha", "RUC Cliente", "Razón Social",
            "Grav. 10%", "IVA 10%", "Grav. 5%", "IVA 5%", "Exenta", "Total PYG"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, stretch=1)

        # --- BOTONES DE ACCIÓN INFERIORES ---
        bot_layout = QHBoxLayout()
        bot_layout.setSpacing(10)

        self.btn_export_sifen = QPushButton("📄 Exportar JSON SIFEN v150")
        self.btn_export_sifen.setStyleSheet("background-color: #1b382b; color: #06d6a0; border-color: #23654b; padding: 8px 16px;")
        self.btn_export_sifen.clicked.connect(self.exportar_json_sifen)
        bot_layout.addWidget(self.btn_export_sifen)

        self.btn_html_chart = QPushButton("📊 Ver Reporte Gráfico (ApexCharts)")
        self.btn_html_chart.setStyleSheet("background-color: #2e3a59; color: #7aa2f7; border-color: #41527d; padding: 8px 16px;")
        self.btn_html_chart.clicked.connect(self.abrir_reporte_grafico)
        bot_layout.addWidget(self.btn_html_chart)

        self.btn_export_csv = QPushButton("📑 Exportar Libro de Ventas (CSV)")
        self.btn_export_csv.setStyleSheet("background-color: #3b2c1f; color: #ffd166; border-color: #6b4d32; padding: 8px 16px;")
        self.btn_export_csv.clicked.connect(self.exportar_libro_csv)
        bot_layout.addWidget(self.btn_export_csv)

        bot_layout.addStretch()

        btn_close = QPushButton("🚪 Cerrar")
        btn_close.clicked.connect(self.close)
        bot_layout.addWidget(btn_close)

        layout.addLayout(bot_layout)

    def _set_default_dates(self):
        today = QDate.currentDate()
        self.dt_desde.setDate(today)
        self.dt_hasta.setDate(today)

    def _set_today(self):
        today = QDate.currentDate()
        self.dt_desde.setDate(today)
        self.dt_hasta.setDate(today)
        self.consultar_datos()

    def _set_this_week(self):
        today = QDate.currentDate()
        # Lunes de esta semana
        day_of_week = today.dayOfWeek()
        monday = today.addDays(-(day_of_week - 1))
        self.dt_desde.setDate(monday)
        self.dt_hasta.setDate(today)
        self.consultar_datos()

    def _set_this_month(self):
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        self.dt_desde.setDate(first_day)
        self.dt_hasta.setDate(today)
        self.consultar_datos()

    def _get_datetime_range(self):
        d_from = self.dt_desde.date()
        d_to = self.dt_hasta.date()
        dt_start = datetime.datetime(d_from.year(), d_from.month(), d_from.day(), 0, 0, 0)
        dt_end = datetime.datetime(d_to.year(), d_to.month(), d_to.day(), 23, 59, 59)
        return dt_start, dt_end

    def consultar_datos(self):
        dt_start, dt_end = self._get_datetime_range()
        q_filter = self.txt_filter.text()

        db = SessionLocal()
        try:
            summary = FiscalEngine.get_period_summary(db, dt_start, dt_end)
            details = FiscalEngine.get_invoices_detail(db, dt_start, dt_end, query_filter=q_filter)
        finally:
            db.close()

        # Actualizar KPIs
        self.lbl_kpi_total.setText(f"₲ {summary['total_general']:,.0f}".replace(",", "."))
        self.lbl_kpi_iva10.setText(f"₲ {summary['total_iva_10']:,.0f}".replace(",", "."))
        self.lbl_kpi_iva5.setText(f"₲ {summary['total_iva_5']:,.0f}".replace(",", "."))
        self.lbl_kpi_exenta.setText(f"₲ {summary['total_exentas']:,.0f}".replace(",", "."))
        self.lbl_kpi_docs.setText(f"{summary['invoices_count']} docs")

        # Cargar Tabla
        self.table.setRowCount(0)
        for row_idx, d in enumerate(details):
            self.table.insertRow(row_idx)

            items_data = [
                (f"001-001-{d['ven_numero']:07d}", Qt.AlignmentFlag.AlignLeft),
                (d["ven_fecha"], Qt.AlignmentFlag.AlignCenter),
                (d["ruc_cliente"], Qt.AlignmentFlag.AlignCenter),
                (d["nombre_cliente"], Qt.AlignmentFlag.AlignLeft),
                (f"₲ {d['gravada_10']:,.0f}".replace(",", "."), Qt.AlignmentFlag.AlignRight),
                (f"₲ {d['iva_10']:,.0f}".replace(",", "."), Qt.AlignmentFlag.AlignRight),
                (f"₲ {d['gravada_5']:,.0f}".replace(",", "."), Qt.AlignmentFlag.AlignRight),
                (f"₲ {d['iva_5']:,.0f}".replace(",", "."), Qt.AlignmentFlag.AlignRight),
                (f"₲ {d['exenta']:,.0f}".replace(",", "."), Qt.AlignmentFlag.AlignRight),
                (f"₲ {d['total']:,.0f}".replace(",", "."), Qt.AlignmentFlag.AlignRight),
            ]

            for col_idx, (text, align) in enumerate(items_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_idx, col_idx, item)

    def exportar_json_sifen(self):
        dt_start, dt_end = self._get_datetime_range()
        db = SessionLocal()
        try:
            payload = FiscalEngine.generate_sifen_json(db, dt_start, dt_end)
        finally:
            db.close()

        default_filename = f"SIFEN_LOTE_{dt_start.strftime('%Y%m%d')}_{dt_end.strftime('%Y%m%d')}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Lote JSON SIFEN v150", default_filename, "JSON Files (*.json)")
        if path:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self,
                "Exportación SIFEN Exitosa",
                f"Lote JSON SIFEN v150 generado correctamente con {payload['resumen_fiscal']['total_comprobantes']} comprobantes.\n\nRuta: {path}"
            )

    def exportar_libro_csv(self):
        dt_start, dt_end = self._get_datetime_range()
        db = SessionLocal()
        try:
            csv_content = FiscalEngine.generate_sales_book_csv(db, dt_start, dt_end)
        finally:
            db.close()

        default_filename = f"Libro_Ventas_{dt_start.strftime('%Y%m%d')}_{dt_end.strftime('%Y%m%d')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Libro de Ventas CSV", default_filename, "CSV Files (*.csv)")
        if path:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(csv_content)
            QMessageBox.information(
                self,
                "Libro de Ventas Guardado",
                f"El archivo CSV fue generado exitosamente.\n\nRuta: {path}"
            )

    def abrir_reporte_grafico(self):
        dt_start, dt_end = self._get_datetime_range()
        db = SessionLocal()
        try:
            html_content = FiscalEngine.generate_html_report(db, dt_start, dt_end)
        finally:
            db.close()

        temp_path = os.path.join(tempfile.gettempdir(), f"reporte_fiscal_{datetime.datetime.now().strftime('%H%M%S')}.html")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        webbrowser.open(f"file:///{temp_path}")
