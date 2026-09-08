import os
import sys
import time
import pytest
from decimal import Decimal

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills')))

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

def setup_product_impact(db, codigo):
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if prod:
        return prod
    prod = models.Product(
        art_codigo=codigo,
        art_descri=f"Prod Impacto {codigo}",
        art_costo=Decimal('1000'),
        art_preven=Decimal('2000'),
        art_stkini=Decimal('100000')
    )
    db.add(prod)
    db.commit()
    return prod

def setup_currency_rates(db):
    rates = {
        'USD': Decimal('7500'),
        'BRL': Decimal('1400'),
        'ARS': Decimal('6.5')
    }
    for mnd, tasa in rates.items():
        rate_record = models.CurrencyRate(
            currency_code=mnd,
            buy_rate=tasa,
            sell_rate=tasa,
            is_active=True
        )
        db.add(rate_record)
    db.commit()
    return rates

def test_rendimiento_carga_masiva(db_session):
    prod = setup_product_impact(db_session, "IMPACT-01")
    
    window = MainWindow()
    window.session_id = 1
    
    start_time = time.time()
    
    for i in range(5000):
        item = {
            'codigo': prod.art_cbarra or prod.art_codigo,
            'descripcion': prod.art_descri,
            'cantidad': Decimal('1'),
            'precio': prod.art_preven,
            'total': prod.art_preven,
            'plu_code': prod.art_codigo,
            'impuesto_porc': Decimal('10')
        }
        window.ventas_model.items.append(item)
    
    window.ventas_model.layoutChanged.emit()
    window.calcular_totales()
    
    end_time = time.time()
    duracion = end_time - start_time
    
    assert window.ventas_model.rowCount() == 5000
    assert duracion < 2.0, f"Rendimiento de UI deficiente: {duracion:.2f}s"
    window.close()

def test_arqueo_multimoneda(db_session):
    prod = setup_product_impact(db_session, "IMPACT-02")
    rates = setup_currency_rates(db_session)
    
    window = MainWindow()
    window.session_id = 2
    
    db_session.query(models.Payment).filter_by(session_id=2).delete()
    db_session.commit()
    
    for i in range(10):
        window.ventas_model.items.clear()
        window.ventas_model.items.append({
            'codigo': prod.art_codigo, 'descripcion': prod.art_descri, 'cantidad': Decimal('1'),
            'precio': Decimal('2000'), 'total': Decimal('2000'), 'plu_code': prod.art_codigo,
            'impuesto_porc': Decimal('10')
        })
        window.calcular_totales()
        
        pagos = [{
            'metodo': 'Efectivo',
            'moneda': 'USD',
            'monto_origen': Decimal('1'),
            'monto_pyg': Decimal('1') * rates['USD']
        }]
        window.guardar_venta_db(pagos)
        
    for i in range(10):
        window.ventas_model.items.clear()
        window.ventas_model.items.append({
            'codigo': prod.art_codigo, 'descripcion': prod.art_descri, 'cantidad': Decimal('1'),
            'precio': Decimal('2000'), 'total': Decimal('2000'), 'plu_code': prod.art_codigo,
            'impuesto_porc': Decimal('10')
        })
        window.calcular_totales()
        
        pagos = [{
            'metodo': 'Efectivo',
            'moneda': 'BRL',
            'monto_origen': Decimal('5'),
            'monto_pyg': Decimal('5') * rates['BRL']
        }]
        window.guardar_venta_db(pagos)
        
    window.close()
    
    pagos = db_session.query(models.Payment).filter_by(session_id=2).all()
    total_usd_origen = sum([p.cob_monto for p in pagos if p.cob_mndori == 'USD'])
    total_brl_origen = sum([p.cob_monto for p in pagos if p.cob_mndori == 'BRL'])
    total_gral_pyg = sum([p.cob_monto_pyg for p in pagos])
    
    assert total_usd_origen == Decimal('10')
    assert total_brl_origen == Decimal('50')
    assert total_gral_pyg == Decimal('145000')
    

def test_resiliencia_transaccional_rollback(db_session, monkeypatch):
    prod = setup_product_impact(db_session, "IMPACT-03")
    stock_inicial = prod.art_stkini
    
    window = MainWindow()
    window.session_id = 3
    window.ventas_model.items.append({
            'codigo': prod.art_codigo, 'descripcion': prod.art_descri, 'cantidad': Decimal('10'),
            'precio': Decimal('2000'), 'total': Decimal('20000'), 'plu_code': prod.art_codigo,
            'impuesto_porc': Decimal('10')
    })
    window.calcular_totales()
    
    invoices_prev = db_session.query(models.Invoice).count()
    
    def mock_commit(*args, **kwargs):
        raise Exception("Error Falso Inducido de DB")
    
    import sqlalchemy
    monkeypatch.setattr(sqlalchemy.orm.Session, "commit", mock_commit)
    
    # PyQt/app intercepta y traga la excepcion en guardar_venta_db mostrando un alert
    # En nuestro test, validar la excepcion tal vez falle porque window.guardar_venta_db captura except: 
    # db.rollback()
    # Asi que simplemente llamamos y asertamos el stock y la factura que esten limpios.
    window.guardar_venta_db([{
        'metodo': 'Efectivo', 'moneda': 'PYG', 'monto_origen': Decimal('20000'), 'monto_pyg': Decimal('20000')
    }])
        
    # Validacion: el stock NO debio bajar
    db_session.refresh(prod)
    assert prod.art_stkini == stock_inicial
    
    # Validacion: la factura NO debio guardarse
    invoices_post = db_session.query(models.Invoice).count()
    assert invoices_post == invoices_prev
    window.close()
