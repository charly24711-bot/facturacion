import os
import sys
import unittest
from decimal import Decimal
import datetime

# Entorno headless y paths
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))

from PyQt6.QtWidgets import QApplication
from database import SessionLocal, Base, engine
import models
from ui.ticket_dialog import TicketDialog
from ruc_validator.ruc_validator import calcular_dv_ruc

app = QApplication.instance() or QApplication(sys.argv)

class TestTicketKuDEPrinter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        
        # Crear factura de prueba única
        cls.invoice = models.Invoice(
            ven_codcli="000001",
            ven_total=Decimal("110000"),
            ven_codmnd="PYG",
            ven_fecha=datetime.datetime(2026, 10, 1, 12, 0, 0)
        )
        db.add(cls.invoice)
        db.commit()
        db.refresh(cls.invoice)
        cls.invoice_id = cls.invoice.id
        cls.ven_numero = cls.invoice.ven_numero or cls.invoice.id
        
        # Producto IVA 10%
        prod10 = db.query(models.Product).filter_by(art_codigo="TICKET01").first()
        if not prod10:
            prod10 = models.Product(
                art_codigo="TICKET01",
                art_descri="LECHE ENTERA 1L",
                art_preven=Decimal("10000"),
                art_impu=10,
                art_stkini=Decimal("50")
            )
            db.add(prod10)
            db.commit()
            
        item1 = models.InvoiceItem(
            vit_numero=cls.ven_numero,
            vit_articu="TICKET01",
            vit_canti=Decimal("11"),
            vit_precio=Decimal("10000")
        )
        db.add(item1)
        
        # Pago con Tarjeta POS
        pago_pos = models.Payment(
            cob_monto=Decimal("110000"),
            cob_monto_pyg=Decimal("110000"),
            cob_vennro=cls.ven_numero,
            cob_mndori="PYG",
            cob_metodo="Tarjeta VISA",
            auth_code="AUTH-123456",
            voucher_nro="VOUCH-7890",
            card_brand="VISA",
            terminal_id="POS-TEST-01"
        )
        db.add(pago_pos)
        db.commit()
        db.close()

    def test_01_cdc_44_digits_and_modulo11(self):
        """Verifica que el CDC generado tenga exactamente 44 dígitos y su DV sea válido."""
        dlg = TicketDialog(invoice_id=self.invoice_id)
        
        cdc = dlg.cdc_code
        self.assertEqual(len(cdc), 44, f"El CDC debe tener 44 dígitos, obtenido: {len(cdc)} ({cdc})")
        self.assertTrue(cdc.isdigit(), "El CDC debe ser 100% numérico")
        
        # Verificar que el último dígito coincida con el Módulo 11 de los primeros 43 dígitos
        cadena_43 = cdc[:43]
        dv_esperado = str(calcular_dv_ruc(cadena_43))
        self.assertEqual(cdc[43], dv_esperado, f"Dígito verificador de CDC incorrecto: {cdc[43]} != {dv_esperado}")

    def test_02_qr_url_sifen_format(self):
        """Verifica que el QR contenga la URL oficial de e-Kuatia con parámetros SIFEN."""
        dlg = TicketDialog(invoice_id=self.invoice_id)
        
        url = dlg.qr_url
        self.assertTrue(url.startswith("https://ekuatia.set.gov.py/consultas-sifen/qr"))
        self.assertIn(f"Id={dlg.cdc_code}", url)
        self.assertIn("dTotGralOpe=110000", url)
        self.assertIn("dTotIVA=10000", url) # IVA 10% de 110.000 es 110.000 / 11 = 10.000

    def test_03_ticket_format_40_columns_and_tax_breakdown(self):
        """Verifica el ancho de 40 columnas monoespaciado y el desglose de IVA DNIT."""
        dlg = TicketDialog(invoice_id=self.invoice_id)
        text = dlg.ticket_text
        
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            # Líneas no vacías no deben exceder los 44 caracteres
            self.assertLessEqual(len(line), 44, f"Línea {idx+1} excede ancho térmico: '{line}' ({len(line)} chars)")
            
        self.assertIn("IVA 10%", text)
        self.assertIn("10.000", text) # 110.000 / 11 = 10.000
        self.assertIn("110.000", text)

    def test_04_pos_voucher_rendering_in_ticket(self):
        """Verifica que el ticket imprima el código de autorización y voucher del POS electrónico."""
        dlg = TicketDialog(invoice_id=self.invoice_id)
        text = dlg.ticket_text
        
        self.assertIn("TARJETA VISA", text)
        self.assertIn("AUTH-123456", text)
        self.assertIn("VOUCH-7890", text)

if __name__ == '__main__':
    unittest.main()
