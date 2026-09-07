import os
import sys
import pytest
import json
from decimal import Decimal

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database import SessionLocal
import models
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def setup_product_offline(db, codigo):
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if prod:
        return prod
    prod = models.Product(
        art_codigo=codigo,
        art_descri=f"Offline Prod {codigo}",
        art_costo=Decimal('1000'),
        art_preven=Decimal('5000'),
        art_stkini=Decimal('100')
    )
    db.add(prod)
    db.commit()
    return prod

def test_offline_first_sync_outbox(db_session):
    """
    Simulacin de 'Apagn de Red'. 
    Realizar 10 transacciones en el POS.
    Validar que la tabla SyncOutbox capture todas las Invoices e InvoiceItems 
    con `synced=False` y el JSON correspondiente.
    """
    prod = setup_product_offline(db_session, "OFFL01")
    
    # Limpiamos outbox para el test
    db_session.query(models.SyncOutbox).delete()
    db_session.commit()
    
    window = MainWindow()
    window.session_id = 4
    
    # Simular que hacemos 10 ventas durante un apagn
    for i in range(10):
        window.ventas_model.items.clear()
        window.ventas_model.items.append({
            'codigo': prod.art_codigo,
            'descripcion': prod.art_descri,
            'cantidad': Decimal('1'),
            'precio': prod.art_preven,
            'total': prod.art_preven,
            'plu_code': prod.art_codigo,
            'impuesto_porc': Decimal('10')
        })
        window.calcular_totales()
        
        pagos = [{
            'metodo': 'Efectivo', 'moneda': 'PYG', 
            'monto_origen': Decimal('5000'), 'monto_pyg': Decimal('5000')
        }]
        window.guardar_venta_db(pagos)
        
    # Las transacciones han terminado localmente sin problemas
    
    # Evaluamos la bandeja de salida
    outbox_invoices = db_session.query(models.SyncOutbox).filter_by(entity_name='Invoice').all()
    outbox_items = db_session.query(models.SyncOutbox).filter_by(entity_name='InvoiceItem').all()
    outbox_payments = db_session.query(models.SyncOutbox).filter_by(entity_name='Payment').all()
    
    assert len(outbox_invoices) == 10, f"Error en Outbox (Invoices): Esperados 10, hay {len(outbox_invoices)}"
    assert len(outbox_items) == 10, f"Error en Outbox (InvoiceItems): Esperados 10, hay {len(outbox_items)}"
    assert len(outbox_payments) == 10, f"Error en Outbox (Payments): Esperados 10, hay {len(outbox_payments)}"
    
    # Validar el payload de una factura
    sample = outbox_invoices[0]
    assert sample.synced is False, "El flag synced debera ser False para esperar la resincronizacin"
    assert sample.action == 'INSERT'
    
    payload = json.loads(sample.payload_json)
    assert payload['ven_codmnd'] == 'PYG'
    assert payload['ven_total'] == '5000'
    assert 'uuid' in payload, "Falta el UUID universal para sincronizacin segura"
    
    window.close()
