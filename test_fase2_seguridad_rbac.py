import os
import sys
import pytest
from decimal import Decimal

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database import SessionLocal
import models
from PyQt6.QtWidgets import QApplication
from ui.ventas_table_model import VentasTableModel
from PyQt6.QtCore import Qt

app = QApplication.instance() or QApplication([])

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_rbac_cajero_no_puede_editar_precio(db_session):
    """
    Simula un Cajero intentando vulnerar la grilla para bajarle el precio a un artculo (fraude).
    El Role Based Access Control (RBAC) debe rechazar el `setData` en la columna 7 (Precio).
    """
    # 1. Crear producto de prueba
    prod = db_session.query(models.Product).filter_by(art_codigo="RBAC01").first()
    if not prod:
        prod = models.Product(
            art_codigo="RBAC01", art_descri="TV 50 Pulgadas",
            art_costo=Decimal('2000000'), art_preven=Decimal('3500000'), art_impu=Decimal('10')
        )
        db_session.add(prod)
        db_session.commit()
        
    # 2. Instanciar la tabla con rol CAJERO (Usuario raso)
    modelo_cajero = VentasTableModel(current_role="CAJERO")
    modelo_cajero.add_item(prod, cantidad=Decimal('1'))
    
    # Intentar sobrescribir el precio de 3.500.000 a 1 (Fraude)
    index = modelo_cajero.index(0, 7) # Fila 0, Columna 7 (Precio)
    
    # Comprobar los flags
    flags = modelo_cajero.flags(index)
    assert not (flags & Qt.ItemFlag.ItemIsEditable), "La celda de precio debera estar BLOQUEADA para cajeros"
    
    # Intentar forzar el setteo
    exito = modelo_cajero.setData(index, "1", Qt.ItemDataRole.EditRole)
    assert exito is False, "El modelo permiti la inyeccin de precio fraudulento al Cajero"
    
    # Verificar que el precio sigui en 3.500.000
    assert modelo_cajero.items[0]['precio'] == Decimal('3500000')

def test_rbac_gerente_puede_editar_precio(db_session):
    """
    Simula a un Gerente modificando el precio en caja para aplicar una rebaja especial.
    """
    prod = db_session.query(models.Product).filter_by(art_codigo="RBAC01").first()
    
    # Instanciar con rol GERENTE
    modelo_gerente = VentasTableModel(current_role="GERENTE")
    modelo_gerente.add_item(prod, cantidad=Decimal('1'))
    
    index = modelo_gerente.index(0, 7)
    
    # Comprobar los flags
    flags = modelo_gerente.flags(index)
    assert bool(flags & Qt.ItemFlag.ItemIsEditable), "La celda debera estar LIBERADA para gerentes"
    
    # Aplicar la rebaja a 3.000.000
    exito = modelo_gerente.setData(index, "3000000", Qt.ItemDataRole.EditRole)
    assert exito is True, "El sistema bloque errneamente a un Gerente legtimamente autenticado"
    
    # Verificar impacto
    assert modelo_gerente.items[0]['precio'] == Decimal('3000000')
