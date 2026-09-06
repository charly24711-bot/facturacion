import sys
from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, 
    QGroupBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from database import SessionLocal, format_stock_qty, format_iva_rate
import models

class InvoiceDetailDialog(QDialog):
    """
    Ventana emergente moderna con el detalle completo de la venta:
    - Cabecera: Cliente, RUC, Factura Nº, Fecha, Vendedor, Condición
    - Grilla de Productos: Código, Descripción, Cantidad, Precio Unitario, Tasa IVA, Subtotal
    - Desglose de Liquidación de IVA (10%, 5%, Exentas)
    - Formas de pago registradas
    - Botón para ver / imprimir el comprobante KuDE oficial con código QR SIFEN
    """
    def __init__(self, invoice_id, parent=None):
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.ven_numero = invoice_id
        
        self.setWindowTitle(f"Detalle de Comprobante / Venta #{self.invoice_id}")
        self.resize(750, 560)
        self.setMinimumSize(680, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.setup_ui()
        self.cargar_datos()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ── 1. CABECERA DE LA VENTA ───────────────────────────────────────────
        grp_cabecera = QGroupBox("Datos del Comprobante Fiscal")
        grp_cabecera.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
                background-color: #f8fafc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #1e293b;
            }
        """)
        cab_grid = QGridLayout(grp_cabecera)
        cab_grid.setContentsMargins(12, 10, 12, 10)
        cab_grid.setHorizontalSpacing(16)
        cab_grid.setVerticalSpacing(6)

        # Labels
        self.lbl_nro_fac = QLabel("-")
        self.lbl_nro_fac.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.lbl_nro_fac.setStyleSheet("color: #1a237e;")

        self.lbl_fecha = QLabel("-")
        self.lbl_cliente = QLabel("-")
        self.lbl_ruc = QLabel("-")
        self.lbl_condicion = QLabel("CONTADO")
        self.lbl_vendedor = QLabel("001 - Principal")

        self.lbl_total = QLabel("Gs. 0")
        self.lbl_total.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #2e7d32;")

        # Fila 0
        cab_grid.addWidget(QLabel("Nº Factura / Ticket:"), 0, 0)
        cab_grid.addWidget(self.lbl_nro_fac, 0, 1)
        cab_grid.addWidget(QLabel("Total Operación:"), 0, 2)
        cab_grid.addWidget(self.lbl_total, 0, 3)

        # Fila 1
        cab_grid.addWidget(QLabel("Fecha / Hora:"), 1, 0)
        cab_grid.addWidget(self.lbl_fecha, 1, 1)
        cab_grid.addWidget(QLabel("Condición:"), 1, 2)
        cab_grid.addWidget(self.lbl_condicion, 1, 3)

        # Fila 2
        cab_grid.addWidget(QLabel("Cliente:"), 2, 0)
        cab_grid.addWidget(self.lbl_cliente, 2, 1)
        cab_grid.addWidget(QLabel("RUC / CI:"), 2, 2)
        cab_grid.addWidget(self.lbl_ruc, 2, 3)

        main_layout.addWidget(grp_cabecera)

        # ── 2. GRILLA DE ARTÍCULOS VENDIDOS ───────────────────────────────────
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción del Artículo", "Cantidad", "Precio Unit.", "IVA", "Subtotal (Gs.)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                gridline-color: #f1f5f9;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #334155;
                font-weight: bold;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #cbd5e1;
            }
        """)
        main_layout.addWidget(self.table, stretch=1)

        # ── 3. RESUMEN FISCAL & FORMAS DE PAGO ────────────────────────────────
        bottom_box = QFrame()
        bottom_box.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;")
        bottom_layout = QHBoxLayout(bottom_box)
        bottom_layout.setContentsMargins(12, 8, 12, 8)

        # Formas de Pago
        pago_layout = QVBoxLayout()
        lbl_pago_title = QLabel("💳 Forma de Pago:")
        lbl_pago_title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        lbl_pago_title.setStyleSheet("color: #475569;")
        self.lbl_pago_desc = QLabel("Efectivo (PYG)")
        self.lbl_pago_desc.setFont(QFont("Arial", 10))
        self.lbl_pago_desc.setStyleSheet("color: #0f172a;")
        pago_layout.addWidget(lbl_pago_title)
        pago_layout.addWidget(self.lbl_pago_desc)
        bottom_layout.addLayout(pago_layout, stretch=1)

        # Desglose IVA
        iva_layout = QVBoxLayout()
        lbl_iva_title = QLabel("⚖️ Liquidación DNIT:")
        lbl_iva_title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        lbl_iva_title.setStyleSheet("color: #475569;")
        self.lbl_iva_desc = QLabel("Grav. 10%: Gs. 0 | IVA 10%: Gs. 0 | Grav. 5%: Gs. 0 | IVA 5%: Gs. 0")
        self.lbl_iva_desc.setFont(QFont("Arial", 9))
        self.lbl_iva_desc.setStyleSheet("color: #334155;")
        iva_layout.addWidget(lbl_iva_title)
        iva_layout.addWidget(self.lbl_iva_desc)
        bottom_layout.addLayout(iva_layout, stretch=2)

        main_layout.addWidget(bottom_box)

        # ── 4. BOTONERA DE ACCIÓN ─────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        
        self.btn_ticket = QPushButton("🖨️ Ver / Imprimir Ticket KuDE (QR SIFEN)")
        self.btn_ticket.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_ticket.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                padding: 9px 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_ticket.clicked.connect(self.abrir_ticket)

        self.btn_cerrar = QPushButton("Cerrar [Esc]")
        self.btn_cerrar.setFont(QFont("Arial", 10))
        self.btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: white;
                padding: 9px 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_cerrar.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_ticket)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cerrar)
        main_layout.addLayout(btn_layout)

    def abrir_ticket(self):
        from ui.ticket_dialog import TicketDialog
        dlg = TicketDialog(self.ven_numero, self)
        dlg.exec()

    def cargar_datos(self):
        db = SessionLocal()
        try:
            # Buscar por ven_numero o por id
            factura = db.query(models.Invoice).filter(
                (models.Invoice.ven_numero == self.invoice_id) | (models.Invoice.id == self.invoice_id)
            ).first()

            if not factura:
                self.lbl_cliente.setText("Comprobante no encontrado")
                return

            self.ven_numero = factura.ven_numero or factura.id
            self.lbl_nro_fac.setText(f"#{self.ven_numero:06d}")
            self.lbl_fecha.setText(factura.ven_fecha.strftime("%d/%m/%Y %H:%M:%S") if factura.ven_fecha else "-")

            cli_nom = factura.client.cli_nombre if factura.client else "CONSUMIDOR FINAL"
            cli_cod = factura.client.cli_codigo if factura.client else "000000"
            cli_ruc = factura.client.cli_ruc if (factura.client and factura.client.cli_ruc) else "X"
            
            self.lbl_cliente.setText(f"{cli_cod} - {cli_nom}")
            self.lbl_ruc.setText(cli_ruc)

            tot_pyg = Decimal(str(factura.ven_total or 0))
            self.lbl_total.setText(f"Gs. {tot_pyg:,.0f}")

            # ── Formas de Pago ──
            pagos = db.query(models.Payment).filter(
                (models.Payment.cob_vennro == self.ven_numero) | (models.Payment.cob_vennro == factura.id)
            ).all()

            if pagos:
                desc_pagos = []
                for p in pagos:
                    monto = Decimal(str(p.cob_monto or 0))
                    mnd = p.cob_mndori or "PYG"
                    met = p.cob_metodo or "Efectivo"
                    if mnd == "PYG":
                        desc_pagos.append(f"{met} (PYG): Gs. {monto:,.0f}")
                    else:
                        desc_pagos.append(f"{met} ({mnd}): {monto:,.2f}")
                self.lbl_pago_desc.setText(" | ".join(desc_pagos))
            else:
                self.lbl_pago_desc.setText("Efectivo (PYG)")

            # ── Ítems de la Venta ──
            items = db.query(models.InvoiceItem).filter(
                (models.InvoiceItem.vit_numero == self.ven_numero) | (models.InvoiceItem.vit_numero == factura.id)
            ).all()

            self.table.setRowCount(len(items))

            tot_grav10 = Decimal('0')
            tot_iva10 = Decimal('0')
            tot_grav5 = Decimal('0')
            tot_iva5 = Decimal('0')
            tot_exenta = Decimal('0')

            for row, item in enumerate(items):
                # Código
                item_cod = QTableWidgetItem(str(item.vit_articu or ""))
                item_cod.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Descripción
                desc = item.product.art_descri if item.product else "Artículo"
                item_desc = QTableWidgetItem(desc)

                # Cantidad
                canti = Decimal(str(item.vit_canti or 0))
                canti_str = format_stock_qty(canti)
                item_canti = QTableWidgetItem(canti_str)
                item_canti.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                # Precio
                precio = Decimal(str(item.vit_precio or 0))
                item_precio = QTableWidgetItem(f"{precio:,.0f}")
                item_precio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                # IVA
                iva_pct = Decimal(str(item.product.art_impu if item.product and item.product.art_impu is not None else 10))
                item_iva = QTableWidgetItem(format_iva_rate(iva_pct))
                item_iva.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Subtotal
                subtotal = canti * precio
                item_sub = QTableWidgetItem(f"{subtotal:,.0f}")
                item_sub.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                # Acumuladores de IVA
                if iva_pct == 10:
                    iva_calc = subtotal / Decimal('11')
                    tot_iva10 += iva_calc
                    tot_grav10 += (subtotal - iva_calc)
                elif iva_pct == 5:
                    iva_calc = subtotal / Decimal('21')
                    tot_iva5 += iva_calc
                    tot_grav5 += (subtotal - iva_calc)
                else:
                    tot_exenta += subtotal

                self.table.setItem(row, 0, item_cod)
                self.table.setItem(row, 1, item_desc)
                self.table.setItem(row, 2, item_canti)
                self.table.setItem(row, 3, item_precio)
                self.table.setItem(row, 4, item_iva)
                self.table.setItem(row, 5, item_sub)

            # Actualizar label de IVA
            self.lbl_iva_desc.setText(
                f"Grav. 10%: Gs. {tot_grav10:,.0f} | IVA 10%: Gs. {tot_iva10:,.0f} | "
                f"Grav. 5%: Gs. {tot_grav5:,.0f} | IVA 5%: Gs. {tot_iva5:,.0f} | Total IVA: Gs. {(tot_iva10 + tot_iva5):,.0f}"
            )

        except Exception as e:
            print(f"Error cargando detalle de factura: {e}")
        finally:
            db.close()
