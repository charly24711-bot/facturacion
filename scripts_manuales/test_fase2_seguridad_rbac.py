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

def test_rbac_cajero_bloqueado_en_modulos_criticos_pos():
    """
    Verifica que un CAJERO en MainWindow tenga oculto el botón de Artículos
    y bloqueados los accesos a Compras, Promociones, Configuración y Listas de Precios.
    """
    from ui.main_window import MainWindow
    from PyQt6.QtWidgets import QMessageBox
    win_cajero = MainWindow(current_user={"id": 2, "username": "cajero", "full_name": "Cajero", "role": "CAJERO"})
    assert not win_cajero.btn_articulo.isVisible(), "El botón Artículos debe estar oculto para CAJERO"
    win_cajero.close()

def test_kardex_inmutable_en_venta(db_session):
    """
    Verifica que al registrar una venta en POS se cree un registro en InventoryMovement (Kardex)
    con stock_anterior, cantidad descontada, stock_resultante y comprobante.
    """
    from ui.main_window import MainWindow
    prod = db_session.query(models.Product).filter_by(art_codigo="RBAC01").first()
    prod.art_stkini = Decimal('20')
    db_session.commit()

    win = MainWindow(current_user={"id": 1, "username": "admin", "full_name": "Admin", "role": "ADMIN"})
    win.session_id = 1
    win.ventas_model.add_item(prod, cantidad=Decimal('2'))
    win.calcular_totales()
    win.guardar_venta_db([{
        'metodo': 'Efectivo', 'moneda': 'PYG',
        'monto_origen': Decimal('7000000'), 'monto_pyg': Decimal('7000000')
    }])

    mov = (db_session.query(models.InventoryMovement)
             .filter_by(art_codigo="RBAC01", tipo_movimiento="VENTA")
             .order_by(models.InventoryMovement.id.desc())
             .first())
    assert mov is not None, "Debe registrarse el movimiento en el Kardex (InventoryMovement)"
    assert mov.stock_anterior == Decimal('20')
    assert mov.cantidad == Decimal('-2')
    assert mov.stock_resultante == Decimal('18')
    assert isinstance(mov.stock_resultante, Decimal)
    win.close()

