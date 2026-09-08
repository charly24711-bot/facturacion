import os
import sys
import time
import pytest
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

def setup_product_hardware(db, codigo, cbarra=None):
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if prod:
        return prod
    prod = models.Product(
        art_codigo=codigo,
        art_descri=f"Hardware Prod {codigo}",
        art_cbarra=cbarra or codigo,
        art_costo=Decimal('1000'),
        art_preven=Decimal('2000'),
        art_stkini=Decimal('100')
    )
    db.add(prod)
    db.commit()
    return prod

def test_hardware_ean13_metralleta(db_session):
    """
    Simular un escner de caja que lee rapidsimo (metralleta EAN-13).
    Asegurarse de que el QTimer/Event Loop procese cada input y el modelo crezca correctamente.
    """
    prod1 = setup_product_hardware(db_session, "HW0001", "7891234567890")
    prod2 = setup_product_hardware(db_session, "HW0002", "7890987654321")
    
    window = MainWindow()
    
    start_time = time.time()
    
    # Simular 100 "bips" del escner intercalados muy rpido
    for i in range(50):
        # Escanear el primer producto
        window.txt_codigo.setText("7891234567890")
        window.txt_codigo.returnPressed.emit()
        
        # Escanear el segundo
        window.txt_codigo.setText("7890987654321")
        window.txt_codigo.returnPressed.emit()
        
    # Pyqt podra diferir el layout emit o hacer merges si el escner es muy veloz.
    # El test valida que el modelo de la grilla contabilice los 100 tems a la perfeccin (sean 100 filas, o si consolida, sean 50 qty de c/u)
    
    end_time = time.time()
    
    # En nuestro main_window.py no sabemos si "buscar_producto" consolida o aade nueva linea.
    # En cualquier caso, sumamos las cantidades. Deberan ser exactamente 100 artculos en total.
    total_qty = sum(Decimal(str(item['cantidad'])) for item in window.ventas_model.items)
    
    assert total_qty == Decimal('100'), f"El escner perdi datos. Cantidad total: {total_qty}"
    assert (end_time - start_time) < 3.0, "La lectura de hardware es demasiado lenta."
    
    window.close()


def test_hardware_balanza_prefijo_20(db_session):
    """
    Verificar decodificacin de ticket de balanza In-Store.
    Ej: 20 00035 01250 3
    Significa: Prefijo 20 (peso), PLU 00035, Peso 1.250kg
    """
    prod_balanza = setup_product_hardware(db_session, "000035") # El PLU que leer
    # Forzar art_preven a algo conocido para el test, ej: 100,000 por Kilo.
    prod_balanza.art_preven = Decimal('100000')
    db_session.commit()
    
    window = MainWindow()
    
    # Escaneamos la etiqueta de carnicera
    barcode = "2000035012503"
    window.txt_codigo.setText(barcode)
    window.txt_codigo.returnPressed.emit()
    
    # Asegurarnos de que el input entr a la grilla y fue convertido en fraccin matemticamente
    # 1.250 kg * 100,000 = 125,000
    
    assert len(window.ventas_model.items) == 1, "La balanza no ingres a la grilla"
    
    item_ingresado = window.ventas_model.items[0]
    
    assert item_ingresado['codigo'] == "000035", f"El decodificador err el PLU: {item_ingresado['codigo']}"
    assert Decimal(str(item_ingresado['cantidad'])) == Decimal('1.250'), f"Error al extraer peso en KG"
    
    # El subtotal (1.250 kg x 100,000) debe ser 125,000
    expected_total = Decimal('125000')
    assert Decimal(str(item_ingresado['total'])) == expected_total, f"Clculo monetario errneo desde peso: {item_ingresado['total']}"
    
    window.close()
