import os
import sys
import pytest
from decimal import Decimal

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database import SessionLocal
import models
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from PyQt6.QtCore import Qt

app = QApplication.instance() or QApplication([])

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def setup_product_overflow(db, codigo):
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if prod:
        return prod
    # Producto con costo y precio inmenso: 99 mil millones
    prod = models.Product(
        art_codigo=codigo,
        art_descri=f"Cargamento Oro {codigo}",
        art_costo=Decimal('99999999999'), 
        art_preven=Decimal('99999999999'),
        art_stkini=Decimal('10000000'),
        art_impu=Decimal('10')
    )
    db.add(prod)
    db.commit()
    return prod

def test_overflow_financiero(db_session):
    """
    Simulacin de una transaccin astronmica de ms de 99 Cuatrillones.
    """
    prod = setup_product_overflow(db_session, "OVRF01")
    
    window = MainWindow()
    
    # 1 milln de unidades de 99,999,999,999 c/u
    cantidad_demencial = Decimal('1000000')
    precio_inmenso = Decimal('99999999999')
    subtotal_esperado = cantidad_demencial * precio_inmenso
    # 99,999,999,999,000,000
    
    window.ventas_model.add_item(prod, cantidad=cantidad_demencial)
    window.calcular_totales()
    
    # 1. Validar la interfaz grfica (PyQt6)
    # Columna 8 es 'Total'
    index = window.ventas_model.index(0, 8)
    texto_visible = window.ventas_model.data(index, Qt.ItemDataRole.DisplayRole)
    
    # El framework Python convierte nmeros grandes a 'e' si no se les aplica un f-string correcto.
    assert "e" not in str(texto_visible).lower(), f"ERROR VISUAL: El nmero se trunc a notacin cientfica: {texto_visible}"
    
    # Debe ser el string exacto con separador de miles si es que as lo configuramos, 
    # pero ante todo debe contener la precisin de 99,999,999,999,000,000
    # Quitamos las comas para comparar
    numero_limpio = str(texto_visible).replace(',', '')
    assert Decimal(numero_limpio) == subtotal_esperado, f"La UI trunc o redonde mal: {numero_limpio} != {subtotal_esperado}"
    
    # 2. Guardar en SQLite
    pagos = [{
        'metodo': 'Transferencia', 'moneda': 'PYG', 
        'monto_origen': subtotal_esperado, 'monto_pyg': subtotal_esperado
    }]
    
    window.guardar_venta_db(pagos)
    
    # 3. Validar integridad de la base de datos (Recuperar y asertar)
    # Buscamos la ltima factura
    db_session.expire_all() # Forzar lectura limpia
    factura_guardada = db_session.query(models.Invoice).order_by(models.Invoice.id.desc()).first()
    
    # Comprobar que SQLAlchemy y SQLite no corrompieron el Float/Decimal
    assert factura_guardada.ven_total == subtotal_esperado, f"CORRUPCIN DB: {factura_guardada.ven_total} != {subtotal_esperado}"
    
    item_guardado = db_session.query(models.InvoiceItem).filter_by(vit_numero=factura_guardada.ven_numero).first()
    assert (item_guardado.vit_canti * item_guardado.vit_precio) == subtotal_esperado, "Corrupcin en detalle de factura"
    
    window.close()
