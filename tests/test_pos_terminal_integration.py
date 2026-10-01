import os
import sys
import unittest
from decimal import Decimal

# Asegurar entorno headless y path del proyecto
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from database import SessionLocal, Base, engine
import models
from utils.pos_driver import POSTerminalSimulator, POSTerminalWorker
from ui.payment_dialog import PaymentDialog
from ui.main_window import MainWindow

# Instancia global de QApplication para tests Qt
app = QApplication.instance() or QApplication(sys.argv)

class TestPOSTerminalIntegration(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        
    def tearDown(self):
        self.db.close()

    def test_01_simulator_approved(self):
        """Verifica que el simulador POS responda exitosamente con datos de voucher completos."""
        sim = POSTerminalSimulator(terminal_id="POS-TEST-01", force_result="APPROVED")
        monto = Decimal("150000")
        result = sim.process_payment(monto, "PYG")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["amount"], monto)
        self.assertEqual(result["currency"], "PYG")
        self.assertEqual(result["terminal_id"], "POS-TEST-01")
        self.assertTrue(len(result["auth_code"]) >= 6)
        self.assertTrue(result["voucher_nro"].startswith("T"))
        self.assertTrue(result["card_brand"] in ["VISA", "MASTERCARD", "MAESTRO", "CABAL", "PIX-QR"])

    def test_02_simulator_rejected_and_cancelled(self):
        """Verifica el comportamiento del simulador ante rechazo bancario y cancelación."""
        sim_rej = POSTerminalSimulator(force_result="REJECTED")
        res_rej = sim_rej.process_payment(Decimal("50000"), "PYG")
        self.assertFalse(res_rej["success"])
        self.assertEqual(res_rej["status_code"], "DECLINED")
        
        sim_can = POSTerminalSimulator()
        sim_can.cancel_operation()
        res_can = sim_can.process_payment(Decimal("50000"), "PYG")
        self.assertFalse(res_can["success"])
        self.assertEqual(res_can["status_code"], "CANCELLED")

    def test_03_payment_dialog_pos_approved_deduction(self):
        """Verifica que al recibir cobro aprobado por POS en PaymentDialog se reste el saldo automáticamente."""
        totals = {'PYG': Decimal('200000'), 'USD': Decimal('25.00'), 'BRL': Decimal('130.00'), 'ARS': Decimal('32000.00')}
        dlg = PaymentDialog(totals=totals)
        
        # Simular respuesta exitosa del POS
        mock_result = {
            "success": True,
            "auth_code": "987654",
            "voucher_nro": "T1234",
            "card_brand": "VISA",
            "terminal_id": "POS-TEST-01",
            "amount": Decimal("100000"),
            "currency": "PYG"
        }
        
        dlg.on_pos_approved(mock_result)
        
        # Verificar que el pago se agregó a la grilla y el faltante se redujo a 100.000 Gs
        self.assertEqual(dlg.table_pagos.rowCount(), 1)
        self.assertEqual(dlg.lbl_recibido.text().replace(',', ''), "100000")
        self.assertEqual(dlg.lbl_faltante.text().replace(',', ''), "100000")
        self.assertFalse(dlg.btn_cobrar.isEnabled())
        
        # Completar el resto con otra tarjeta vía POS
        mock_result2 = {
            "success": True,
            "auth_code": "112233",
            "voucher_nro": "T1235",
            "card_brand": "MASTERCARD",
            "terminal_id": "POS-TEST-01",
            "amount": Decimal("100000"),
            "currency": "PYG"
        }
        dlg.on_pos_approved(mock_result2)
        
        self.assertEqual(dlg.table_pagos.rowCount(), 2)
        self.assertEqual(dlg.lbl_recibido.text().replace(',', ''), "200000")
        self.assertEqual(dlg.lbl_faltante.text(), "0")
        self.assertTrue(dlg.btn_cobrar.isEnabled())
        
        # Procesar cobro
        dlg.procesar_cobro()
        self.assertTrue(dlg.payment_successful)
        self.assertEqual(len(dlg.payments_list), 2)
        self.assertEqual(dlg.payments_list[0]['auth_code'], "987654")
        self.assertEqual(dlg.payments_list[1]['auth_code'], "112233")
        self.assertEqual(dlg.payments_list[0]['voucher_nro'], "T1234")
        self.assertEqual(dlg.payments_list[1]['voucher_nro'], "T1235")

    def test_04_full_sale_pos_payment_persistence(self):
        """Verifica la persistencia de los campos de terminal POS en la base de datos (models.Payment)."""
        main_win = MainWindow()
        
        # Agregar un ítem al carrito
        producto = self.db.query(models.Product).first()
        if not producto:
            producto = models.Product(
                art_codigo="999901",
                art_descri="PRODUCTO PRUEBA POS",
                art_prcuni=Decimal("50000"),
                art_stkini=Decimal("100")
            )
            self.db.add(producto)
            self.db.commit()
            
        main_win.ventas_model.add_item(
            product=producto,
            cantidad=Decimal('2'),
            precio_override=Decimal('50000')
        )
        
        # Simular lista de pagos con Voucher de POS
        payments_list = [{
            'moneda': 'PYG',
            'metodo': 'Tarjeta VISA',
            'monto_origen': Decimal('100000'),
            'monto_pyg': Decimal('100000'),
            'auth_code': 'AUTH-778899',
            'voucher_nro': 'TICKET-5544',
            'card_brand': 'VISA',
            'terminal_id': 'POS-LAN-02'
        }]
        
        # Guardar venta
        main_win.guardar_venta_db(payments_list)
        
        # Consultar en DB que el pago se haya guardado con todos sus metadatos
        pago_db = self.db.query(models.Payment).filter_by(auth_code='AUTH-778899').first()
        self.assertIsNotNone(pago_db, "El registro de Payment con auth_code debe persistirse en DB")
        self.assertEqual(pago_db.voucher_nro, 'TICKET-5544')
        self.assertEqual(pago_db.card_brand, 'VISA')
        self.assertEqual(pago_db.terminal_id, 'POS-LAN-02')
        self.assertEqual(pago_db.cob_monto, Decimal('100000'))

if __name__ == '__main__':
    unittest.main()
