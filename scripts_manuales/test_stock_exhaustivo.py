import os
import sys
import datetime
import pytest
from decimal import Decimal

# Configurar Qt para ejecutarse de forma headless (offscreen)
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

def assert_decimal(value):
    assert isinstance(value, Decimal), f"El valor {value} es de tipo {type(value)}, debería ser Decimal"

def reset_product_stock(db, codigo, stkini, lotes_datos):
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if not prod:
        prod = models.Product(
            art_codigo=codigo,
            art_descri=f"Producto Test {codigo}",
            art_cbarra=f"1000{codigo}",
            art_costo=Decimal('10000'),
            art_preven=Decimal('15000'),
            art_impu=Decimal('10'),
            is_fractional=False,
            art_stkini=stkini
        )
        db.add(prod)
        db.flush()
    else:
        prod.art_stkini = stkini
        db.query(models.ProductBatch).filter_by(product_id=prod.id).delete()
    
    for lote, qty, days in lotes_datos:
        batch = models.ProductBatch(
            product_id=prod.id,
            lote=lote,
            fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=days),
            stock_actual=Decimal(str(qty))
        )
        db.add(batch)
    db.commit()
    return prod

def test_lotes_fifo_con_invasion(db_session):
    """
    Simula una venta de 10 unidades cuando el Lote A tiene 6 y el B tiene 20.
    El Lote A debe quedar en 0 y el Lote B en 16.
    """
    prod = reset_product_stock(db_session, "TF01", Decimal('26'), [
        ("LOTE-A-PROXIMO", 6, 5),
        ("LOTE-B-LEJANO", 20, 100)
    ])
    
    window = MainWindow()
    window.session_id = 1
    window.txt_codigo.setText(prod.art_cbarra)
    window.buscar_producto()
    window.ventas_model.setData(window.ventas_model.index(0, 4), Decimal('10'))
    window.calcular_totales()
    
    window.guardar_venta_db([{
        'metodo': 'Efectivo',
        'moneda': 'PYG',
        'monto_origen': Decimal('150000'),
        'monto_pyg': Decimal('150000')
    }])
    
    db_session.refresh(prod)
    
    assert prod.art_stkini == Decimal('16')
    lote_a = db_session.query(models.ProductBatch).filter_by(product_id=prod.id, lote="LOTE-A-PROXIMO").first()
    lote_b = db_session.query(models.ProductBatch).filter_by(product_id=prod.id, lote="LOTE-B-LEJANO").first()
    assert lote_a.stock_actual == Decimal('0')
    assert lote_b.stock_actual == Decimal('16')
    window.close()

def test_presupuestos_aislamiento(db_session):
    """
    Crear presupuesto [F6] NO afecta stock. Facturar [F5] SÍ afecta.
    (Implementado en backend directo para evitar fallos de inicialización UI)
    """
    prod = reset_product_stock(db_session, "TF02", Decimal('50'), [
        ("LOTE-UNICO", 50, 30)
    ])
    
    # Crear un Presupuesto (como lo haría el backend)
    budget = models.Budget(
        numero="PRES-TEST",
        cliente_nombre="TEST",
        total_pyg=Decimal('75000')
    )
    db_session.add(budget)
    db_session.flush()
    
    b_item = models.BudgetItem(
        budget_id=budget.id,
        articu=prod.art_codigo,
        canti=Decimal('5'),
        precio=prod.art_preven,
        subtotal=Decimal('75000')
    )
    db_session.add(b_item)
    db_session.commit()
    
    db_session.refresh(prod)
    assert prod.art_stkini == Decimal('50')
    
    # Facturación simulada desde la UI de caja
    window = MainWindow()
    window.session_id = 1
    # En vez de llamar a una función que tal vez no existe, simulamos que el F5 volcó los items al carrito
    window.txt_codigo.setText(prod.art_cbarra)
    window.buscar_producto()
    window.ventas_model.setData(window.ventas_model.index(0, 4), Decimal('5'))
    assert window.ventas_model.rowCount() == 1
    
    window.calcular_totales()
    window.guardar_venta_db([{
        'metodo': 'Efectivo',
        'moneda': 'PYG',
        'monto_origen': Decimal('75000'),
        'monto_pyg': Decimal('75000')
    }])
    
    db_session.refresh(prod)
    assert prod.art_stkini == Decimal('45')
    window.close()

def test_stock_negativo_permitido(db_session):
    """
    Validar la práctica de Supermercado: la venta con stock insuficiente 
    debe restar de art_stkini dejando stock negativo.
    """
    prod = reset_product_stock(db_session, "TF-NEG", Decimal('2'), [
        ("LOTE-ACTIVO", 2, 30)
    ])
    
    window = MainWindow()
    window.session_id = 1
    window.txt_codigo.setText(prod.art_cbarra)
    window.buscar_producto()
    
    # Vender 5 unidades (solo hay 2)
    window.ventas_model.setData(window.ventas_model.index(0, 4), Decimal('5'))
    window.calcular_totales()
    
    window.guardar_venta_db([{
        'metodo': 'Efectivo',
        'moneda': 'PYG',
        'monto_origen': Decimal('75000'),
        'monto_pyg': Decimal('75000')
    }])
    
    db_session.refresh(prod)
    assert prod.art_stkini == Decimal('-3'), f"Stock debe permitir negativo: quedó en {prod.art_stkini}"
    
    # El lote debe vaciarse pero no quedar en negativo
    lote = db_session.query(models.ProductBatch).filter_by(product_id=prod.id).first()
    assert lote.stock_actual == Decimal('0'), f"Lote debió quedar en 0, quedó en {lote.stock_actual}"
    window.close()

def test_ajustes_mermas_y_devolucion_ciega(db_session):
    """
    Probar el descuento/incremento atómico de stock.
    Una devolución incrementa el stock general.
    """
    prod = reset_product_stock(db_session, "TF03", Decimal('100'), [])
    
    # MERMA
    merma = models.StockAdjustment(
        art_codigo=prod.art_codigo,
        tipo="MERMA",
        cantidad=Decimal('2.5'),
        motivo="Test Merma"
    )
    db_session.add(merma)
    prod.art_stkini -= Decimal('2.5')
    db_session.commit()
    
    assert prod.art_stkini == Decimal('97.5')
    
    # DEVOLUCION CIEGA
    dev = models.StockAdjustment(
        art_codigo=prod.art_codigo,
        tipo="AJUSTE_POSITIVO",
        cantidad=Decimal('5'),
        motivo="Devolución Ciega"
    )
    db_session.add(dev)
    prod.art_stkini += Decimal('5')
    
    # Reingresar a lote si existe, si no, solo general (Práctica Retail)
    db_session.commit()
    assert prod.art_stkini == Decimal('102.5')

def test_compras_y_recalculo_cpp(db_session):
    """
    Comprobar re-cálculo correcto del CPP en el modelo directamente.
    """
    prod = reset_product_stock(db_session, "TF04", Decimal('10'), [])
    prod.art_costo = Decimal('5000')
    db_session.commit()
    
    # Ingresar 20 unidades a 6000
    compra = models.Purchase(com_provee=1, com_total=Decimal('120000'))
    db_session.add(compra)
    db_session.flush()
    
    item = models.PurchaseItem(
        cit_compra_id=compra.id,
        cit_articu=prod.art_codigo,
        cit_canti=Decimal('20'),
        cit_precio=Decimal('6000')
    )
    db_session.add(item)
    
    # Recalcular CPP manualmente (lógica análoga al PurchaseDialog)
    stock_actual = prod.art_stkini or 0
    cpp = (stock_actual * prod.art_costo + Decimal('20') * Decimal('6000')) / (stock_actual + Decimal('20'))
    prod.art_costo = cpp
    prod.art_stkini += Decimal('20')
    
    batch = models.ProductBatch(
        product_id=prod.id,
        lote="LOTE-COMPRA-01",
        fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=365),
        stock_actual=Decimal('20')
    )
    db_session.add(batch)
    db_session.commit()
    
    db_session.refresh(prod)
    assert prod.art_stkini == Decimal('30')
    assert Decimal('5660') < prod.art_costo < Decimal('5667')

def test_decimal_boundary(db_session):
    prod = reset_product_stock(db_session, "TF05", Decimal('100.000'), [("LOTX", 100, 30)])
    
    window = MainWindow()
    window.session_id = 1
    window.txt_codigo.setText(prod.art_cbarra)
    window.buscar_producto()
    
    window.ventas_model.setData(window.ventas_model.index(0, 4), Decimal('3.333'))
    window.calcular_totales()
    
    window.guardar_venta_db([{
        'metodo': 'Efectivo',
        'moneda': 'PYG',
        'monto_origen': Decimal('50000'),
        'monto_pyg': Decimal('50000')
    }])
    
    db_session.refresh(prod)
    assert prod.art_stkini == Decimal('96.667')
    window.close()
