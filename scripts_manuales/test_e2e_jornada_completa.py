import os
import sys
import random
import pytest
from datetime import datetime
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

def setup_e2e_environment(db):
    # 1. Crear productos estables y con muchsimo stock
    prods = [
        {"cod": "E2E01", "desc": "Gaseosa Cola 2L", "costo": 5000, "precio": 10000},
        {"cod": "E2E02", "desc": "Carne Vacuna 1Kg", "costo": 25000, "precio": 45000},
    ]
    
    db_prods = []
    for p in prods:
        prod = db.query(models.Product).filter_by(art_codigo=p["cod"]).first()
        if not prod:
            prod = models.Product(
                art_codigo=p["cod"],
                art_descri=p["desc"],
                art_costo=Decimal(str(p["costo"])),
                art_preven=Decimal(str(p["precio"])),
                art_stkini=Decimal('1000000') # 1 milln de stock base
            )
            db.add(prod)
        else:
            # Restaurar stock a 1,000,000 para el test
            db.query(models.Product).filter_by(id=prod.id).update({"art_stkini": Decimal('1000000')})
        db_prods.append(prod)
    
    db.commit()
    
    # Refrescar objetos
    for prod in db_prods:
        db.refresh(prod)
        
    return db_prods

def test_jornada_completa_e2e(db_session):
    """
    Day-in-the-Life Test (Soak / E2E).
    """
    db_prods = setup_e2e_environment(db_session)
    
    # 2. Abrir sesin de caja simulada
    session_uid = 999
    caja = models.CashSession(
        user_id=1,
        opened_at=datetime.utcnow(),
        status='OPEN'
    )
    db_session.add(caja)
    db_session.commit()
    db_session.refresh(caja)
    
    window = MainWindow()
    window.session_id = caja.id
    window.current_user = {"id": 1, "username": "e2e_cajero", "role": "CAJERO", "full_name": "Cajero Bot"}
    
    # Contadores para auditora cruzada
    total_efectivo_ventas = Decimal('0')
    total_qty_vendida = {p.art_codigo: Decimal('0') for p in db_prods}
    
    ITERACIONES = 100 # Se puede subir a 10,000 para soak testing
    
    random.seed(42) # Determinismo para el test
    
    print(f"\n[E2E] Iniciando simulacin de {ITERACIONES} transacciones de caja...")
    
    for i in range(ITERACIONES):
        # Limpiar grilla de UI
        window.ventas_model.items.clear()
        
        subtotal_esperado = Decimal('0')
        
        # Seleccionar artculos al azar (1 a 5 lneas)
        for _ in range(random.randint(1, 3)):
            p = random.choice(db_prods)
            qty = Decimal(str(random.randint(1, 10)))
            
            window.ventas_model.add_item(p, cantidad=qty)
            total_qty_vendida[p.art_codigo] += qty
            subtotal_esperado += qty * p.art_preven
            
        window.calcular_totales()
        
        # Pagar en efectivo
        pagos = [{
            'metodo': 'Efectivo', 'moneda': 'PYG',
            'monto_origen': subtotal_esperado, 'monto_pyg': subtotal_esperado
        }]
        
        # Ejecutar transaccin
        window.guardar_venta_db(pagos)
        total_efectivo_ventas += subtotal_esperado
        
    print(f"[E2E] Jornada terminada. Recaudacin Total Simulada: {total_efectivo_ventas:,.0f} Gs")
    
    # 3. Cruzar la contabilidad con SQLite y el Inventory
    # Arqueo de efectivo: Sumar todo pago en 'Efectivo' asociado a la session_id actual
    pagos_db = db_session.query(models.Payment).filter_by(
        session_id=caja.id, cob_metodo='Efectivo'
    ).all()
    
    total_pagos_sqlite = sum([p.cob_monto_pyg for p in pagos_db])
    
    assert total_pagos_sqlite == total_efectivo_ventas, f"ERROR CONTABLE: SQL reporta {total_pagos_sqlite} pero debera ser {total_efectivo_ventas}"
    
    # 4. Cruzar el stock
    db_session.expire_all()
    for p in db_prods:
        prod_en_db = db_session.query(models.Product).filter_by(id=p.id).first()
        stock_esperado = Decimal('1000000') - total_qty_vendida[p.art_codigo]
        
        assert prod_en_db.art_stkini == stock_esperado, f"ERROR DE INVENTARIO ({p.art_codigo}): Stock {prod_en_db.art_stkini} != {stock_esperado}"
    
    print("[E2E] EXITO. La contabilidad cuadra al centavo y el inventario descont perfectamente tras la prueba de estrs.")
    
    window.close()
