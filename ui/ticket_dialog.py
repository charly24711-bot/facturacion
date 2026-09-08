from decimal import Decimal
import sys
import os
import io
import base64
import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QMessageBox, QApplication, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument, QPixmap
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

import qrcode
from database import SessionLocal
import models

# Importar Skill de Impuestos y Validador de RUC
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills/tax_calculator/scripts')))
import tax_calculator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))
try:
    from ruc_validator.ruc_validator import calcular_dv_ruc
except ImportError:
    from ruc_validator import calcular_dv_ruc

class TicketDialog(QDialog):
    """
    Diálogo de visualización e impresión de Ticket / Factura Legal (KuDE SIFEN)
    con desglose completo de IVA (DNIT Paraguay), CDC oficial de 44 dígitos
    y Código QR oficial para consulta en e-Kuatia.
    """
    def __init__(self, invoice_id: int, parent=None):
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.setWindowTitle(f"Factura Legal KuDE #{invoice_id:06d} - DNIT Paraguay")
        self.resize(520, 740)
        
        self.ticket_text = ""
        self.cdc_code = ""
        self.qr_base64 = ""
        self.qr_url = ""
        
        self.setup_ui()
        self.cargar_y_generar_ticket()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        
        # Título superior
        lbl_titulo = QLabel(f"📄 Comprobante de Venta Electrónico #{self.invoice_id:06d}")
        lbl_titulo.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)
        
        # Visor de Ticket estilo papel térmico 80mm
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
                border-radius: 4px;
                padding: 10px;
                line-height: 1.2;
            }
        """)
        layout.addWidget(self.txt_ticket, stretch=1)
        
        # Card inferior con Código QR oficial DNIT y CDC
        self.qr_box = QGroupBox("Validación Oficial DNIT / SIFEN (KuDE)")
        self.qr_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #1a237e;
                border-radius: 5px;
                margin-top: 6px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #1a237e;
            }
        """)
        qr_layout = QHBoxLayout(self.qr_box)
        qr_layout.setContentsMargins(10, 8, 10, 8)
        qr_layout.setSpacing(12)
        
        self.lbl_qr_img = QLabel()
        self.lbl_qr_img.setFixedSize(110, 110)
        self.lbl_qr_img.setStyleSheet("background-color: white; border: 1px solid #cccccc; border-radius: 4px;")
        self.lbl_qr_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        qr_text_layout = QVBoxLayout()
        lbl_qr_title = QLabel("Comprobante Electrónico Homologado")
        lbl_qr_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl_qr_title.setStyleSheet("color: #1a237e;")
        
        lbl_qr_desc = QLabel("Escanee este código QR con la cámara de su teléfono móvil para verificar la validez tributaria e inalterabilidad de esta factura en el portal e-Kuatia.")
        lbl_qr_desc.setFont(QFont("Arial", 9))
        lbl_qr_desc.setWordWrap(True)
        lbl_qr_desc.setStyleSheet("color: #444444;")
        
        self.lbl_cdc_display = QLabel("CDC: Generando...")
        self.lbl_cdc_display.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.lbl_cdc_display.setStyleSheet("color: #111111; background-color: #e8eaf6; padding: 3px 6px; border-radius: 3px;")
        self.lbl_cdc_display.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        qr_text_layout.addWidget(lbl_qr_title)
        qr_text_layout.addWidget(lbl_qr_desc)
        qr_text_layout.addWidget(self.lbl_cdc_display)
        
        qr_layout.addWidget(self.lbl_qr_img)
        qr_layout.addLayout(qr_text_layout, stretch=1)
        layout.addWidget(self.qr_box)
        
        # Barra de botones
        btn_layout = QHBoxLayout()
        
        self.btn_imprimir = QPushButton("🖨️ Imprimir Ticket KuDE")
        self.btn_imprimir.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 10px 18px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.btn_imprimir.clicked.connect(self.imprimir_ticket)
        
        self.btn_copiar = QPushButton("📋 Copiar Texto")
        self.btn_copiar.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 10px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0d47a1;
            }
        """)
        self.btn_copiar.clicked.connect(self.copiar_texto)
        
        self.btn_cerrar = QPushButton("Aceptar [Enter]")
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
        
    def cargar_y_generar_ticket(self):
        db = SessionLocal()
        try:
            invoice = db.query(models.Invoice).filter_by(id=self.invoice_id).first()
            if not invoice:
                self.txt_ticket.setText("Factura no encontrada.")
                return
                
            company = db.query(models.CompanySettings).first()
            nombre_empresa = company.nombre if (company and company.nombre) else "SUPERMERCADO CENTRAL"
            ruc_empresa = company.ruc if (company and company.ruc) else "80012345-6"
            dir_empresa = company.direccion if (company and company.direccion) else "Avda. San Blas e/ Curupayty - CDE"
            tel_empresa = company.telefono if (company and company.telefono) else "(061) 500-123"
            
            client = invoice.client
            cod_cli = invoice.ven_codcli or "000001"
            nombre_cli = client.cli_nombre if client else "CONSUMIDOR FINAL"
            ruc_cli = client.cli_ruc if (client and client.cli_ruc) else "44444401-7"
            
            items = db.query(models.InvoiceItem).filter_by(vit_numero=invoice.ven_numero).all()
            payments = db.query(models.Payment).filter_by(cob_vennro=invoice.ven_numero).all()
            
            # Ancho estándar 80mm (~40 caracteres monoespaciados)
            W = 40
            SEP = "-" * W
            
            fmt_pyg = lambda n: f"{n:,.0f}".replace(",", ".")
            fmt_sec = lambda n: f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            def fmt_fila_monto(label: str, amount_str: str, curr: str = "Gs.") -> str:
                lbl_pad = f"{label:<22}"[:22]
                curr_pad = f"{curr:<4}"
                num_pad = f"{amount_str:>12}"
                return f"{lbl_pad} {curr_pad} {num_pad}"
            
            lines = []
            lines.append(nombre_empresa.center(W))
            lines.append(f"RUC: {ruc_empresa}".center(W))
            lines.append(dir_empresa.center(W))
            lines.append(f"Tel: {tel_empresa}".center(W))
            lines.append(f"TIMBRADO: 12345678".center(W))
            lines.append(f"FECHA DE INICIO: 01/01/2026".center(W))
            
            fecha_str = invoice.ven_fecha.strftime("%d/%m/%Y %I:%M:%S %p").lower()
            factura_num = f"001-001-{invoice.id:07d}"
            lines.append(f"FACTURA No.: {factura_num}")
            lines.append(f"FECHA: {fecha_str}")
            lines.append(SEP)
            
            # Encabezado ítems
            lines.append(f"{'ARTICULO':<12} {'DESCRIPCION':<27}")
            lines.append(f"{'IVA':<5} {'CANTIDAD':<9} {'PRECIO':<7} {'DESC.':<6} {'TOTAL':>9}")
            lines.append(SEP)
            
            tot_gravada_10 = Decimal("0")
            tot_iva_10 = Decimal("0")
            tot_gravada_5 = Decimal("0")
            tot_iva_5 = Decimal("0")
            tot_exenta = Decimal("0")
            
            for it in items:
                prod = it.product
                codigo = prod.art_codigo if prod else "0000"
                desc = prod.art_descri if prod else "ARTICULO"
                tasa = int(prod.art_impu) if (prod and prod.art_impu is not None) else 10
                
                canti = it.vit_canti
                precio = it.vit_precio
                subtotal = (canti * precio).quantize(Decimal("1"))
                
                # Descuento
                descuento = Decimal("0") # Asumiendo 0 por ahora hasta implementar descuento en lineas
                
                # Desglose IVA según Ley 6380/19
                if tasa == 10:
                    iva_it = (subtotal / Decimal("11")).quantize(Decimal("1"))
                    tot_iva_10 += iva_it
                    tot_gravada_10 += subtotal
                elif tasa == 5:
                    iva_it = (subtotal / Decimal("21")).quantize(Decimal("1"))
                    tot_iva_5 += iva_it
                    tot_gravada_5 += subtotal
                else:
                    tot_exenta += subtotal
                
                canti_str = f"{canti:.3f}".rstrip('0').rstrip('.') if '.' in str(canti) else str(canti)
                
                # Line 1: Codigo - Descripcion
                desc_line = f"{codigo} - {desc}"
                # Split description if too long
                if len(desc_line) > W:
                    lines.append(desc_line[:W])
                    lines.append(desc_line[W:W*2])
                else:
                    lines.append(desc_line)
                    
                # Line 2: IVA CANT x PRECIO DESC TOTAL
                line_2 = f"{str(tasa)+'%':<5} {canti_str} x {fmt_pyg(precio):<7} {fmt_pyg(descuento):<6} {fmt_pyg(subtotal):>9}"
                lines.append(line_2)
            
            lines.append(SEP)
            
            # TOTAL A PAGAR
            tot_pyg = invoice.ven_total or Decimal("0")
            lines.append(fmt_fila_monto("TOTAL:", fmt_pyg(tot_pyg)))
            
            # Formas de Pago
            total_pagado_pyg = Decimal("0")
            for p in payments:
                if p.cob_mndori == "PYG":
                    lines.append(fmt_fila_monto(f"EFECTIVO PYG:", fmt_pyg(p.cob_monto_pyg)))
                else:
                    lines.append(fmt_fila_monto(f"{p.cob_mndori}:", fmt_sec(p.cob_monto), p.cob_mndori))
                total_pagado_pyg += p.cob_monto_pyg
            
            lines.append(fmt_fila_monto("TOTAL PAGO:", fmt_pyg(total_pagado_pyg)))
            vuelto = max(Decimal("0"), total_pagado_pyg - tot_pyg)
            lines.append(fmt_fila_monto("VUELTO:", fmt_pyg(vuelto)))
            lines.append(fmt_fila_monto("DESCUENTO:", "0"))
            
            # Liquidación del IVA Dinámica
            lines.append("DETALLE DE TOTALES")
            if tot_gravada_10 > 0:
                lines.append(f"Grav. 10%{' ' * (W - 10 - len(fmt_pyg(tot_gravada_10)))}{fmt_pyg(tot_gravada_10)}")
            if tot_gravada_5 > 0:
                lines.append(f"Grav. 5%{' ' * (W - 9 - len(fmt_pyg(tot_gravada_5)))}{fmt_pyg(tot_gravada_5)}")
            if tot_exenta > 0:
                lines.append(f"Exenta{' ' * (W - 7 - len(fmt_pyg(tot_exenta)))}{fmt_pyg(tot_exenta)}")
                
            lines.append("DETALLE DEL IMPUESTO")
            if tot_iva_10 > 0:
                lines.append(f"IVA 10%{' ' * (W - 8 - len(fmt_pyg(tot_iva_10)))}{fmt_pyg(tot_iva_10)}")
            if tot_iva_5 > 0:
                lines.append(f"IVA 5%{' ' * (W - 7 - len(fmt_pyg(tot_iva_5)))}{fmt_pyg(tot_iva_5)}")
                
            total_iva_acum = tot_iva_10 + tot_iva_5
            
            lines.append(SEP)
            
            # Datos del cliente abajo
            lines.append(f"Cliente: {nombre_cli[:30]}")
            lines.append(f"C.I. / RUC: {ruc_cli}")
            lines.append(f"CONDICION VENTA: CONTADO")
            lines.append(f"CAJA: 01")
            
            usuario = "CAJERO PRINCIPAL"
            if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'current_user'):
                user_data = self.parent().current_user
                if user_data:
                    usuario = user_data.get('full_name', 'CAJERO PRINCIPAL')
            lines.append(f"CAJERO/A: {usuario}")
            
            # Generación determinista del CDC oficial SIFEN (44 dígitos)
            ruc_clean = ruc_empresa.replace('-', '').strip()
            if '-' in ruc_empresa:
                partes = ruc_empresa.split('-')
                ruc_base = partes[0].zfill(8)
                dv_ruc = partes[1]
            else:
                ruc_base = ruc_clean[:-1].zfill(8) if len(ruc_clean) > 1 else "80012345"
                dv_ruc = ruc_clean[-1] if len(ruc_clean) > 0 else "6"
                
            tipo_doc = "01" # Factura Electrónica
            estab = "001"
            pto_exp = "001"
            nro_sec = f"{(invoice.ven_numero or invoice.id):07d}"
            tipo_contrib = "1" # Persona Jurídica
            fec_emision = invoice.ven_fecha or datetime.datetime.utcnow()
            fecha_cad = fec_emision.strftime("%Y%m%d")
            tipo_emision = "1" # Normal
            cod_seguridad = "100000001" # 9 dígitos
            
            cadena_43 = f"{tipo_doc}{ruc_base}{dv_ruc}{estab}{pto_exp}{nro_sec}{tipo_contrib}{fecha_cad}{tipo_emision}{cod_seguridad}"
            dv_cdc = calcular_dv_ruc(cadena_43)
            self.cdc_code = f"{cadena_43}{dv_cdc}"
            
            # Formatear CDC con guiones visuales
            c = self.cdc_code
            cdc_vis = f"{c[0:4]}-{c[4:8]}-{c[8:12]}-{c[12:16]}-{c[16:20]}-{c[20:24]}-{c[24:28]}-{c[28:32]}-{c[32:36]}-{c[36:40]}-{c[40:44]}"
            
            lines.append("Consulte validez de la Factura Electronica")
            lines.append("con el numero CDC impreso abajo en:")
            lines.append("https://ekuatia.set.gov.py/consultas")
            lines.append(cdc_vis)
            lines.append("")
            
            self.ticket_text = "\n".join(lines)
            self.txt_ticket.setPlainText(self.ticket_text)
            self.lbl_cdc_display.setText(f"CDC: {cdc_vis}")
            
            # Generar Código QR Oficial para el portal e-Kuatia (DNIT)
            self.qr_url = f"https://ekuatia.set.gov.py/consultas-sifen/qr?nVersion=150&Id={self.cdc_code}&dTotGralOpe={int(tot_pyg)}&dTotIVA={int(total_iva_acum)}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=4,
                border=1,
            )
            qr.add_data(self.qr_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            qr_bytes = buf.getvalue()
            self.qr_base64 = base64.b64encode(qr_bytes).decode('ascii')
            
            pixmap = QPixmap()
            pixmap.loadFromData(qr_bytes)
            self.lbl_qr_img.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            
        except Exception as e:
            self.txt_ticket.setPlainText(f"Error generando ticket: {str(e)}")
        finally:
            db.close()
            
    def imprimir_ticket(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            doc = QTextDocument()
            html_content = f"""
            <div style="font-family: 'Courier New', monospace; font-size: 8pt; line-height: 1.25;">
                <pre style="margin: 0; padding: 0;">{self.ticket_text}</pre>
                <div style="text-align: center; margin-top: 10px;">
                    <img src="data:image/png;base64,{self.qr_base64}" width="130" height="130" /><br>
                    <span style="font-size: 7.5pt; font-family: sans-serif; color: #333;">Consulte validez oficial en ekuatia.set.gov.py</span>
                </div>
            </div>
            """
            doc.setHtml(html_content)
            doc.print(printer)
            QMessageBox.information(self, "Impresión", "Ticket KuDE enviado a la impresora.")
        
    def copiar_texto(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ticket_text)
        QMessageBox.information(self, "Copiado", "Texto del ticket copiado al portapapeles.")
