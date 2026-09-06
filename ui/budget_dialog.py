from decimal import Decimal
import sys
import os
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from database import SessionLocal
import models

class BudgetDialog(QDialog):
    """
    Diálogo de visualización e impresión de Presupuesto / Cotización para Clientes.
    No deduce stock ni genera obligaciones fiscales (validez 15 días).
    """
    def __init__(self, budget_id: int, parent=None):
        super().__init__(parent)
        self.budget_id = budget_id
        self.setWindowTitle(f"Presupuesto / Cotización #{budget_id}")
        self.resize(500, 700)
        
        self.ticket_text = ""
        self.setup_ui()
        self.cargar_y_generar_presupuesto()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header banner
        lbl_titulo = QLabel(f"📋 Presupuesto de Venta #{self.budget_id:06d}")
        lbl_titulo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)
        
        lbl_sub = QLabel("Validez comercial: 15 días corridos • Sin reserva de stock")
        lbl_sub.setFont(QFont("Arial", 9))
        lbl_sub.setStyleSheet("color: #555555;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_sub)
        
        # Visor de Presupuesto formato térmico 80mm
        self.txt_ticket = QTextEdit()
        self.txt_ticket.setReadOnly(True)
        font_thermal = QFont("Courier New", 10)
        font_thermal.setStyleHint(QFont.StyleHint.Monospace)
        self.txt_ticket.setFont(font_thermal)
        self.txt_ticket.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #111111;
                border: 1px solid #cccccc;
                padding: 12px;
                line-height: 1.25;
            }
        """)
        layout.addWidget(self.txt_ticket, stretch=1)
        
        # Barra de botones
        btn_layout = QHBoxLayout()
        
        self.btn_imprimir = QPushButton("🖨️ Imprimir Presupuesto")
        self.btn_imprimir.setStyleSheet("""
            QPushButton {
                background-color: #0288d1;
                color: white;
                font-weight: bold;
                padding: 10px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0277bd;
            }
        """)
        self.btn_imprimir.clicked.connect(self.imprimir_presupuesto)
        
        self.btn_copiar = QPushButton("📋 Copiar")
        self.btn_copiar.setStyleSheet("""
            QPushButton {
                background-color: #546e7a;
                color: white;
                font-weight: bold;
                padding: 10px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #455a64;
            }
        """)
        self.btn_copiar.clicked.connect(self.copiar_texto)
        
        self.btn_cerrar = QPushButton("Cerrar [Esc]")
        self.btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                font-weight: bold;
                padding: 10px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #212121;
            }
        """)
        self.btn_cerrar.clicked.connect(self.accept)
        self.btn_cerrar.setDefault(True)
        
        btn_layout.addWidget(self.btn_imprimir)
        btn_layout.addWidget(self.btn_copiar)
        btn_layout.addWidget(self.btn_cerrar)
        layout.addLayout(btn_layout)
        
    def cargar_y_generar_presupuesto(self):
        db = SessionLocal()
        try:
            budget = db.query(models.Budget).filter_by(id=self.budget_id).first()
            if not budget:
                self.txt_ticket.setText("Presupuesto no encontrado.")
                return
                
            company = db.query(models.CompanySettings).first()
            nombre_empresa = company.nombre if (company and company.nombre) else "SUPERMERCADO CENTRAL"
            ruc_empresa = company.ruc if (company and company.ruc) else "80012345-6"
            dir_empresa = company.direccion if (company and company.direccion) else "Avda. San Blas e/ Curupayty - CDE"
            tel_empresa = company.telefono if (company and company.telefono) else "(061) 500-123"
            
            client = budget.client
            cod_cli = budget.codcli or "000001"
            nombre_cli = budget.cliente_nombre or (client.cli_nombre if client else "CONSUMIDOR FINAL")
            ruc_cli = budget.cliente_ruc or (client.cli_ruc if (client and client.cli_ruc) else "44444401-7")
            
            items = db.query(models.BudgetItem).filter_by(budget_id=budget.id).all()
            
            # Ancho estándar 80mm (~42 caracteres)
            W = 42
            SEP = "=" * W
            MINI_SEP = "-" * W
            
            fmt_pyg = lambda n: f"{n:,.0f}".replace(",", ".")
            fmt_sec = lambda n: f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            def fmt_fila_monto(label: str, amount_str: str, curr: str = "Gs.") -> str:
                lbl_pad = f"{label:<24}"[:24]
                curr_pad = f"{curr:<4}"
                num_pad = f"{amount_str:>14}"
                return f"{lbl_pad}{curr_pad}{num_pad}"
            
            lines = []
            lines.append(nombre_empresa.center(W))
            lines.append(f"RUC: {ruc_empresa}".center(W))
            lines.append(dir_empresa.center(W))
            lines.append(f"Tel: {tel_empresa}".center(W))
            lines.append("IVA INCLUIDO".center(W))
            lines.append(SEP)
            
            lines.append("*** PRESUPUESTO / COTIZACIÓN ***".center(W))
            lines.append(SEP)
            
            fecha_str = budget.fecha.strftime("%d/%m/%Y %H:%M")
            fecha_venc = budget.fecha + datetime.timedelta(days=budget.validez_dias or 15)
            venc_str = fecha_venc.strftime("%d/%m/%Y")
            
            num_str = budget.numero if budget.numero else f"PRES-{budget.id:06d}"
            lines.append(f"PRESUPUESTO Nº : {num_str}")
            lines.append(f"FECHA EMISIÓN  : {fecha_str}")
            lines.append(f"VÁLIDO HASTA   : {venc_str} (15 días)")
            lines.append(f"ESTADO         : {budget.estado}")
            lines.append(MINI_SEP)
            
            # Datos del cliente
            lines.append(f"CLIENTE : {nombre_cli[:30]}")
            lines.append(f"RUC/CI  : {ruc_cli}")
            lines.append(f"CÓDIGO  : {cod_cli}")
            lines.append(SEP)
            
            # Encabezado ítems
            lines.append(f"{'CANT':<5} {'DESCRIPCIÓN':<16} {'PRECIO':>8} {'TOTAL':>10}")
            lines.append(MINI_SEP)
            
            tot_gravada_10 = Decimal("0")
            tot_iva_10 = Decimal("0")
            tot_gravada_5 = Decimal("0")
            tot_iva_5 = Decimal("0")
            tot_exenta = Decimal("0")
            
            for it in items:
                prod = it.product
                desc = it.descripcion or (prod.art_descri if prod else "ARTICULO")
                tasa = it.impuesto_porc if it.impuesto_porc is not None else (int(prod.art_impu) if (prod and prod.art_impu is not None) else 10)
                
                canti = it.canti
                precio = it.precio
                subtotal = it.subtotal if it.subtotal is not None else (canti * precio).quantize(Decimal("1"))
                
                # Desglose IVA según Ley 6380/19
                if tasa == 10:
                    tot_gravada_10 += subtotal
                    tot_iva_10 += (subtotal / Decimal("11")).quantize(Decimal("1"))
                elif tasa == 5:
                    tot_gravada_5 += subtotal
                    tot_iva_5 += (subtotal / Decimal("21")).quantize(Decimal("1"))
                else:
                    tot_exenta += subtotal
                
                canti_str = f"{canti:.3f}".rstrip('0').rstrip('.') if '.' in str(canti) else str(canti)
                lines.append(f"{canti_str:<5} {desc[:16]:<16} {fmt_pyg(precio):>8} {fmt_pyg(subtotal):>10}")
            
            lines.append(SEP)
            
            # TOTAL GENERAL
            tot_pyg = budget.total_pyg or Decimal("0")
            lines.append(fmt_fila_monto("TOTAL PRESUPUESTO", fmt_pyg(tot_pyg), "Gs."))
            lines.append(SEP)
            
            # Equivalencias Multi-Moneda
            lines.append("EQUIVALENCIAS MULTI-MONEDA:".center(W))
            lines.append(fmt_fila_monto("  Dólares Americanos", fmt_sec(budget.total_usd or Decimal("0.00")), "USD"))
            lines.append(fmt_fila_monto("  Reales Brasileños", fmt_sec(budget.total_brl or Decimal("0.00")), "BRL"))
            lines.append(fmt_fila_monto("  Pesos Argentinos", fmt_sec(budget.total_ars or Decimal("0.00")), "ARS"))
            lines.append(MINI_SEP)
            
            # Estimación y Liquidación del IVA (Ley 6380/19)
            lines.append("LIQUIDACIÓN ESTIMADA DEL IVA:".center(W))
            lines.append(fmt_fila_monto("  Gravadas 10%", fmt_pyg(tot_gravada_10), "Gs."))
            lines.append(fmt_fila_monto("  Liquidación IVA 10%", fmt_pyg(tot_iva_10), "Gs."))
            lines.append(fmt_fila_monto("  Gravadas 5%", fmt_pyg(tot_gravada_5), "Gs."))
            lines.append(fmt_fila_monto("  Liquidación IVA 5%", fmt_pyg(tot_iva_5), "Gs."))
            lines.append(fmt_fila_monto("  Exentas", fmt_pyg(tot_exenta), "Gs."))
            total_iva = tot_iva_10 + tot_iva_5
            lines.append(fmt_fila_monto("  TOTAL IVA ESTIMADO", fmt_pyg(total_iva), "Gs."))
            lines.append(SEP)
            
            # Leyenda / Disclaimer Legal y Comercial
            lines.append("CLAUSULAS Y CONDICIONES:".center(W))
            lines.append("- Precios sujetos a variación sin previo aviso.")
            lines.append("- Validez de cotización: 15 días corridos.")
            lines.append("- La emisión NO reserva stock en góndola.")
            lines.append("- Para comprar, presente este comprobante")
            lines.append("  o indique el Nº de Presupuesto en caja.")
            lines.append(MINI_SEP)
            lines.append("NO VÁLIDO COMO COMPROBANTE FISCAL".center(W))
            lines.append("¡Gracias por su preferencia!".center(W))
            lines.append(SEP)
            
            self.ticket_text = "\n".join(lines)
            self.txt_ticket.setText(self.ticket_text)
            
        except Exception as e:
            self.txt_ticket.setText(f"Error generando presupuesto: {str(e)}")
        finally:
            db.close()
            
    def copiar_texto(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ticket_text)
        QMessageBox.information(self, "Copiado", "Texto del presupuesto copiado al portapapeles.")
        
    def imprimir_presupuesto(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        print_dialog = QPrintDialog(printer, self)
        
        if print_dialog.exec() == QDialog.DialogCode.Accepted:
            document = QTextDocument()
            html_content = f"<pre style='font-family: monospace; font-size: 9pt;'>{self.ticket_text}</pre>"
            document.setHtml(html_content)
            document.print(printer)
            QMessageBox.information(self, "Impresión", "Presupuesto enviado a la impresora.")
