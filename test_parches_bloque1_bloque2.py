import os
import sys
import pytest
from decimal import Decimal

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database import SessionLocal
import models
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.ventas_table_model import VentasTableModel
from ui.shelf_labels_dialog import ShelfLabelsDialog
from ui.payment_dialog import PaymentDialog
from PyQt6.QtCore import Qt

app = QApplication.instance() or QApplication([])

@pytest.fixture(autouse=True)
def auto_mock_messagebox(monkeypatch):
    """Evita modales bloqueantes durante pruebas automatizadas."""
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_ventas_table_model_rechaza_cantidad_no_positiva():
    """Verifica que setData en columna Cantidad rechace 0, negativos y basura."""
    prod = models.Product(
        art_codigo="PARCHE01", art_descri="Producto Test",
        art_costo=Decimal('1000'), art_preven=Decimal('2000'), art_impu=Decimal('10')
    )
    model = VentasTableModel()
    model.add_item(prod, cantidad=Decimal('5'))
    idx_cant = model.index(0, 4)

    assert not model.setData(idx_cant, "0"), "Debe rechazar cantidad 0"
    assert not model.setData(idx_cant, "-5"), "Debe rechazar cantidades negativas"
    assert not model.setData(idx_cant, "invalido"), "Debe rechazar strings no numéricos"
    assert model.items[0]['cantidad'] == Decimal('5')

    assert model.setData(idx_cant, "8"), "Debe aceptar cantidad positiva válida"
    assert model.items[0]['cantidad'] == Decimal('8')

def test_shelf_labels_dialog_sin_attribute_errors(db_session):
    """Verifica que ShelfLabelsDialog cargue cotización y productos sin fallar por atributos obsoletos."""
    dlg = ShelfLabelsDialog()
    assert dlg.usd_rate > Decimal('0')
    assert isinstance(dlg.usd_rate, Decimal)
    for item in dlg.todos_los_productos:
        assert "art_codigo" in item
        assert "art_codbar" in item
        assert "art_stkact" in item
    dlg.close()

def test_cuenta_corriente_protecciones(db_session):
    """Verifica que PaymentDialog bloquee Cuenta Corriente a Consumidor Final."""
    dlg = PaymentDialog(totals={'PYG': '100000'})
    dlg.set_consumidor_final()
    dlg.combo_metodo.setCurrentText("Cuenta Corriente")
    dlg.txt_monto.setText("100000")
    dlg.agregar_pago()
    assert dlg.table_pagos.rowCount() == 0, "No debe permitir Cuenta Corriente a Consumidor Final"
    dlg.close()

def test_vuelto_descontado_de_efectivo():
    """Verifica que procesar_cobro reste el vuelto del pago en efectivo neto."""
    dlg = PaymentDialog(totals={'PYG': '50000'})
    dlg.set_consumidor_final()
    dlg.combo_moneda.setCurrentText("PYG")
    dlg.combo_metodo.setCurrentText("Efectivo")
    dlg.txt_monto.setText("100000")
    dlg.agregar_pago()
    assert dlg.table_pagos.rowCount() == 1

    dlg.procesar_cobro()
    assert dlg.payment_successful is True
    # Pago registrado debe ser neto Gs. 50.000 (100.000 entregado - 50.000 vuelto)
    assert len(dlg.payments_list) == 1
    assert dlg.payments_list[0]['monto_pyg'] == Decimal('50000')
    assert dlg.payments_list[0]['monto_origen'] == Decimal('50000')
    dlg.close()

def test_models_salted_hash_seguro():
    """Verifica que hash_password use salt y que verify_password valide tanto con salt como legacy."""
    h1 = models.hash_password("admin")
    h2 = models.hash_password("admin")
    assert h1 == h2, "El hash debe ser determinista para consistencia interna"
    assert models.verify_password("admin", h1)
    assert not models.verify_password("wrong", h1)

    import hashlib
    legacy_hash = hashlib.sha256("admin".encode('utf-8')).hexdigest()
    assert models.verify_password("admin", legacy_hash), "Debe soportar hashes legacy de la BD anterior"
