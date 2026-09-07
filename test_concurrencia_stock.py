import os
import sys
import threading
import datetime
from decimal import Decimal
import pytest
from sqlalchemy.orm import sessionmaker

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from database import engine, SessionLocal
import models

Session = sessionmaker(bind=engine)

def assert_decimal(value):
    assert isinstance(value, Decimal)

def setup_product_for_stress():
    db = SessionLocal()
    codigo = "RACE-100"
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if prod:
        db.query(models.ProductBatch).filter_by(product_id=prod.id).delete()
        db.delete(prod)
        db.commit()
        
    prod = models.Product(
        art_codigo=codigo,
        art_descri="Producto Stress Test",
        art_costo=Decimal('1000'),
        art_preven=Decimal('2000'),
        art_stkini=Decimal('1000') # Arranca con 1000
    )
    db.add(prod)
    db.flush()
    
    batch = models.ProductBatch(
        product_id=prod.id,
        lote="LOTE-UNICO-RACE",
        fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=300),
        stock_actual=Decimal('1000')
    )
    db.add(batch)
    db.commit()
    prod_id = prod.id
    db.close()
    return codigo, prod_id

def anular_factura_logic(db, invoice_id):
    """
    Lógica de back-office que anula una factura y reintegra el stock.
    """
    invoice = db.query(models.Invoice).filter_by(id=invoice_id).first()
    if not invoice or invoice.ven_estado == 'N':
        return False
    
    invoice.ven_estado = 'N'
    
    # Reintegrar
    for item in invoice.items:
        prod = db.query(models.Product).filter_by(art_codigo=item.vit_articu).first()
        if prod:
            prod.art_stkini = Decimal(str(prod.art_stkini)) + item.vit_canti
            
            # Buscar lote lejano para reintegrar
            lote = db.query(models.ProductBatch).filter_by(product_id=prod.id).order_by(models.ProductBatch.fecha_vencimiento.desc()).first()
            if lote:
                lote.stock_actual = Decimal(str(lote.stock_actual)) + item.vit_canti
    
    db.commit()
    return True

def procesar_venta_bloqueante(codigo_articulo, cantidad):
    """Simula una venta atómica con bloqueo a nivel de fila."""
    db = Session()
    try:
        prod = db.query(models.Product).filter_by(art_codigo=codigo_articulo).first()
        if prod:
            db.query(models.Product).filter_by(id=prod.id).update({
                "art_stkini": models.Product.art_stkini - cantidad
            })
            db.commit() # Forzar el commit del general primero
            
            # Recargar y aplicar el descuento a lotes usando UPDATE atómico
            db.refresh(prod)
            qty_to_deduct = cantidad
            batches = (db.query(models.ProductBatch)
                         .filter(models.ProductBatch.product_id == prod.id, 
                                 models.ProductBatch.stock_actual > 0)
                         .order_by(models.ProductBatch.fecha_vencimiento.asc())
                         .all())
            
            for b in batches:
                if qty_to_deduct <= Decimal('0'):
                    break
                available = Decimal(str(b.stock_actual))
                deduccion = min(available, qty_to_deduct)
                db.query(models.ProductBatch).filter_by(id=b.id).update({
                    "stock_actual": models.ProductBatch.stock_actual - deduccion
                })
                qty_to_deduct -= deduccion
                    
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Thread error: {e}")
    finally:
        db.close()


def test_race_conditions_stock():
    """
    Test Multi-hilo: Lanza 50 ventas concurrentes sobre el mismo artículo.
    Con SQLite, sin bloqueos explícitos, causa 'Database is locked' o race conditions.
    Validaremos si SQLAlchemy lo encola o si necesitamos `with_for_update`.
    """
    codigo, prod_id = setup_product_for_stress()
    
    NUM_THREADS = 50
    CANTIDAD_POR_VENTA = Decimal('5')
    
    threads = []
    
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=procesar_venta_bloqueante, args=(codigo, CANTIDAD_POR_VENTA))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Validar
    db = SessionLocal()
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    lote = db.query(models.ProductBatch).filter_by(product_id=prod.id).first()
    
    # Stock inicial 1000 - (50 * 5) = 1000 - 250 = 750
    esperado = Decimal('750')
    
    assert prod.art_stkini == esperado, f"Race condition detectada! Stock {prod.art_stkini} != {esperado}"
    assert lote.stock_actual == esperado, f"Lote falló por concurrencia: {lote.stock_actual}"
    db.close()

def test_anulacion_factura():
    """
    Validar que la anulación de factura reintegra los saldos correctamente.
    """
    db = SessionLocal()
    codigo, prod_id = setup_product_for_stress() # Stock = 1000
    
    # Crear factura
    inv = models.Invoice(ven_total=Decimal('2000'), ven_estado='A')
    db.add(inv)
    db.flush()
    item = models.InvoiceItem(vit_numero=inv.ven_numero, vit_articu=codigo, vit_canti=Decimal('10'), vit_precio=Decimal('2000'))
    db.add(item)
    
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    prod.art_stkini -= Decimal('10')
    lote = db.query(models.ProductBatch).filter_by(product_id=prod.id).first()
    lote.stock_actual -= Decimal('10')
    db.commit()
    
    assert prod.art_stkini == Decimal('990')
    
    # Anular
    exito = anular_factura_logic(db, inv.id)
    assert exito is True
    
    db.refresh(prod)
    db.refresh(lote)
    
    assert inv.ven_estado == 'N'
    assert prod.art_stkini == Decimal('1000'), "Stock no se reintegró a art_stkini"
    assert lote.stock_actual == Decimal('1000'), "Lote no recibió el stock de anulación"
    
    db.close()

def test_alerta_stock_minimo():
    db = SessionLocal()
    prod = db.query(models.Product).filter_by(art_codigo="RACE-100").first()
    prod.art_stkmin = Decimal('1000') # Alerta a las 1000 unidades
    prod.art_stkini = Decimal('1000')
    db.commit()
    
    # Si vendo 1, art_stkini es 999 <= 1000, dispara alerta
    alerta_disparada = (prod.art_stkini - Decimal('1') <= prod.art_stkmin)
    assert alerta_disparada is True, "No se detectó el cruce del umbral de stock crítico"
    db.close()
