import os
import sys
import tracemalloc
import gc
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

def setup_product_memory(db, codigo):
    prod = db.query(models.Product).filter_by(art_codigo=codigo).first()
    if prod:
        return prod
    prod = models.Product(
        art_codigo=codigo,
        art_descri=f"Memory Leak Test {codigo}",
        art_costo=Decimal('1000'),
        art_preven=Decimal('2000'),
        art_stkini=Decimal('100')
    )
    db.add(prod)
    db.commit()
    return prod


def test_no_memory_leaks(db_session):
    """
    Simular 500 ciclos de facturacin continuos sin cerrar la ventana.
    Garantizar que tras el Garbage Collection, la RAM no asciende exponencialmente.
    """
    prod = setup_product_memory(db_session, "MEM01")
    
    # 1. Abrimos la UI que estar abierta durante 12 horas.
    window = MainWindow()
    window.session_id = 99
    
    # Limpiamos basura residual de inicializaciones iniciales
    gc.collect()
    
    # Iniciamos rastreo de memoria Heap
    tracemalloc.start()
    snapshot_inicio = tracemalloc.take_snapshot()
    
    # Simulamos 500 ciclos de ventas
    for i in range(500):
        # Escanea 5 items
        for j in range(5):
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
        window.ventas_model.layoutChanged.emit()
        
        # Simular que factura y limpia grilla
        window.ventas_model.items.clear()
        window.ventas_model.layoutChanged.emit()
        window.calcular_totales()
        
    # Forzamos recoleccin de memoria en python
    gc.collect()
    
    snapshot_fin = tracemalloc.take_snapshot()
    
    # Comparamos
    top_stats = snapshot_fin.compare_to(snapshot_inicio, 'lineno')
    
    # Obtenemos el total de RAM adicional que qued varada y no se liber
    # (En KiB)
    diff_memory_bytes = sum(stat.size_diff for stat in top_stats)
    diff_memory_mb = diff_memory_bytes / (1024 * 1024)
    
    tracemalloc.stop()
    window.close()
    
    print(f"\n[INFO] Fuga de memoria total tras 500 transacciones: {diff_memory_mb:.4f} MB")
    
    # Si tras 500 facturas completas se acumularon ms de 3 MB residuales (lo cual es muchsimo para solo variables Python en loop)
    # significa que hay un leak de referencias.
    assert diff_memory_mb < 3.0, f"Memory Leak crtico detectado: La app acumul {diff_memory_mb:.2f} MB de basura sin liberar."
