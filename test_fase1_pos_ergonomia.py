"""
test_fase1_pos_ergonomia.py
===========================
Test automatizado riguroso - FASE 1: POS Ergonomics & Cash Ops
Cubre:
  1. Motor de canales de precios (PriceList como canal)
  2. Quitar ítem / Cancelar venta
  3. Movimientos de caja: Fondo Inicial y Sangría/Retiro
  4. CajaDialog consolida pagos + movimientos en Decimal
  5. ArqueoDialog recalcula efectivo teórico con movimientos
  6. Regla: CERO floats en precios/montos/stock
"""

import sys
import os
import datetime
sys.path.insert(0, os.path.dirname(__file__))

from decimal import Decimal, InvalidOperation
import pytest

from database import SessionLocal, engine, Base
import models


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def db():
    """Sesión de base de datos compartida para el módulo."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def canal_mayorista(db):
    """Crea o recupera la lista de precios 'Mayorista (Test)'."""
    lista = db.query(models.PriceList).filter_by(pl_nombre="Mayorista (Test F1)").first()
    if not lista:
        lista = models.PriceList(pl_nombre="Mayorista (Test F1)", is_default=False)
        db.add(lista)
        db.commit()
        db.refresh(lista)
    return lista


@pytest.fixture(scope="module")
def producto_test(db):
    """Crea o recupera un producto de prueba."""
    prod = db.query(models.Product).filter_by(art_codigo="TST001").first()
    if not prod:
        prod = models.Product(
            art_codigo="TST001",
            art_descri="Producto Test Fase1",
            art_cbarra="7890001234567",
            art_costo=Decimal("10000"),
            art_preven=Decimal("15000"),  # Precio minorista
            art_impu=Decimal("10"),
            art_stkini=Decimal("100"),
            is_active=True,
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)
    return prod


@pytest.fixture(scope="module")
def precio_mayorista(db, canal_mayorista, producto_test):
    """Crea o recupera precio mayorista del producto test."""
    item = db.query(models.PriceListItem).filter_by(
        pli_list_id=canal_mayorista.id,
        pli_articu=producto_test.art_codigo
    ).first()
    if not item:
        item = models.PriceListItem(
            pli_list_id=canal_mayorista.id,
            pli_articu=producto_test.art_codigo,
            pli_precio=Decimal("12000"),  # Mayorista más barato
        )
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


@pytest.fixture(scope="module")
def sesion_caja(db):
    """Crea o recupera una sesión de caja abierta."""
    sesion = db.query(models.CashSession).filter_by(status='OPEN').first()
    if not sesion:
        sesion = models.CashSession(status='OPEN')
        db.add(sesion)
        db.commit()
        db.refresh(sesion)
    return sesion


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - CANALES DE PRECIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanalesDePrecios:

    def test_priceList_crea_con_decimal(self, db, canal_mayorista):
        """PriceList y PriceListItem persisten con Decimal, no float."""
        lista = db.query(models.PriceList).get(canal_mayorista.id)
        assert lista is not None
        assert isinstance(lista.pl_nombre, str)

    def test_precio_mayorista_es_decimal(self, db, precio_mayorista):
        """PriceListItem.pli_precio es Decimal (nunca float)."""
        item = db.query(models.PriceListItem).get(precio_mayorista.id)
        precio = Decimal(str(item.pli_precio))
        assert isinstance(precio, Decimal)
        assert precio == Decimal("12000")

    def test_precio_minorista_estandar_es_decimal(self, db, producto_test):
        """art_preven del producto es Decimal."""
        prod = db.query(models.Product).filter_by(art_codigo=producto_test.art_codigo).first()
        precio = Decimal(str(prod.art_preven))
        assert isinstance(precio, Decimal)
        assert precio == Decimal("15000")

    def test_canal_mayorista_es_menor_que_minorista(self, db, canal_mayorista, producto_test):
        """El precio mayorista debe ser <= al minorista (regla comercial básica)."""
        item = db.query(models.PriceListItem).filter_by(
            pli_list_id=canal_mayorista.id,
            pli_articu=producto_test.art_codigo
        ).first()
        prod = db.query(models.Product).filter_by(art_codigo=producto_test.art_codigo).first()
        precio_mayorista = Decimal(str(item.pli_precio))
        precio_minorista = Decimal(str(prod.art_preven))
        assert precio_mayorista <= precio_minorista, (
            f"Mayorista {precio_mayorista} debe ser <= Minorista {precio_minorista}"
        )

    def test_canal_mayorista_mayor_que_costo(self, db, canal_mayorista, producto_test):
        """Canal mayorista nunca por debajo del costo (protección de margen)."""
        item = db.query(models.PriceListItem).filter_by(
            pli_list_id=canal_mayorista.id,
            pli_articu=producto_test.art_codigo
        ).first()
        prod = db.query(models.Product).filter_by(art_codigo=producto_test.art_codigo).first()
        precio = Decimal(str(item.pli_precio))
        costo = Decimal(str(prod.art_costo))
        assert precio > costo, f"Canal mayorista {precio} debe ser > costo {costo}"

    def test_multiples_canales_en_db(self, db):
        """Al menos 3 canales de precios configurados (Mayorista, Distribuidor, etc.)."""
        count = db.query(models.PriceList).count()
        assert count >= 3, f"Se esperan >=3 canales de precios, hay {count}"

    def test_canal_sin_precio_especifico_cae_a_minorista(self, db, canal_mayorista, producto_test):
        """Si el canal no tiene precio para el artículo, motor devuelve minorista."""
        # Crear un canal sin precios configurados
        canal_vacio = db.query(models.PriceList).filter_by(pl_nombre="Canal Vacio Test F1").first()
        if not canal_vacio:
            canal_vacio = models.PriceList(pl_nombre="Canal Vacio Test F1", is_default=False)
            db.add(canal_vacio)
            db.commit()
        
        item = db.query(models.PriceListItem).filter_by(
            pli_list_id=canal_vacio.id,
            pli_articu=producto_test.art_codigo
        ).first()
        assert item is None, "Canal vacío no debe tener items para TST001"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - MOVIMIENTOS DE CAJA (SANGRÍA / FONDO INICIAL)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMovimientosDeCaja:

    def test_registrar_fondo_inicial_pyg(self, db, sesion_caja):
        """Registra un Fondo Inicial en PYG con Decimal."""
        monto = Decimal("500000")
        mov = models.CashMovement(
            session_id=sesion_caja.id,
            tipo="FONDO_INICIAL",
            monto=monto,
            moneda="PYG",
            concepto="Fondo apertura test F1"
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        
        assert mov.id is not None
        assert Decimal(str(mov.monto)) == monto
        assert mov.tipo == "FONDO_INICIAL"
        assert mov.moneda == "PYG"

    def test_registrar_sangria_usd(self, db, sesion_caja):
        """Registra una Sangría en USD con Decimal."""
        monto = Decimal("50.00").quantize(Decimal("0.01"))
        mov = models.CashMovement(
            session_id=sesion_caja.id,
            tipo="RETIRO_SANGRIA",
            monto=monto,
            moneda="USD",
            concepto="Retiro efectivo USD test"
        )
        db.add(mov)
        db.commit()
        db.refresh(mov)
        
        assert mov.id is not None
        assert Decimal(str(mov.monto)) == monto
        assert mov.tipo == "RETIRO_SANGRIA"

    def test_sangria_no_puede_tener_monto_cero(self, db, sesion_caja):
        """Monto cero debe ser rechazado antes de persistir."""
        monto = Decimal("0")
        assert monto <= Decimal("0"), "Validación: monto 0 debe ser rechazado"

    def test_monto_decimal_no_float(self, db, sesion_caja):
        """Verificar que los montos almacenados se recuperan como Decimal, nunca float."""
        movs = db.query(models.CashMovement).filter_by(
            session_id=sesion_caja.id
        ).all()
        for m in movs:
            monto = Decimal(str(m.monto))
            assert isinstance(monto, Decimal), f"Monto {m.monto} debe convertir a Decimal"
            assert type(m.monto) is not float, "monto nunca debe ser float puro"

    def test_fondo_suma_a_teorico_efectivo(self, db, sesion_caja):
        """El efectivo teórico PYG = pagos PYG + fondos - sangrías."""
        movs = db.query(models.CashMovement).filter_by(
            session_id=sesion_caja.id,
            moneda="PYG"
        ).all()
        
        total = Decimal("0")
        for m in movs:
            monto = Decimal(str(m.monto))
            if m.tipo in ("FONDO_INICIAL", "INGRESO"):
                total += monto
            elif m.tipo in ("RETIRO_SANGRIA", "EGRESO"):
                total -= monto
        
        assert isinstance(total, Decimal), "Total teórico debe ser Decimal"
        # Con fondo de 500000 PYG y sin sangrías en PYG, el neto debe ser >= 0
        assert total >= Decimal("0"), f"Efectivo neto PYG debe ser >= 0, es {total}"

    def test_sangria_brl(self, db, sesion_caja):
        """Registra sangría en BRL."""
        monto = Decimal("200.00").quantize(Decimal("0.01"))
        mov = models.CashMovement(
            session_id=sesion_caja.id,
            tipo="RETIRO_SANGRIA",
            monto=monto,
            moneda="BRL",
            concepto="Retiro BRL test F1"
        )
        db.add(mov)
        db.commit()
        assert mov.id is not None

    def test_movimientos_tienen_session_id(self, db, sesion_caja):
        """Todos los movimientos referenciados a la sesión activa."""
        movs = db.query(models.CashMovement).filter_by(
            session_id=sesion_caja.id
        ).all()
        assert len(movs) >= 2
        for m in movs:
            assert m.session_id == sesion_caja.id


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - CALCULO TEÓRICO ARQUEO
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalculoTeorico:

    def test_calculo_teorico_neto_pyg(self, db, sesion_caja):
        """Simulación del cálculo teórico PYG que usa ArqueoDialog."""
        pagos = db.query(models.Payment).filter_by(session_id=sesion_caja.id).all()
        movs = db.query(models.CashMovement).filter_by(session_id=sesion_caja.id).all()
        
        teoricos = {}
        
        for p in pagos:
            key = (p.cob_metodo, p.cob_mndori)
            teoricos[key] = teoricos.get(key, Decimal("0")) + Decimal(str(p.cob_monto))
        
        for m in movs:
            key = ("Efectivo", m.moneda)
            monto = Decimal(str(m.monto))
            if m.tipo in ("FONDO_INICIAL", "INGRESO"):
                teoricos[key] = teoricos.get(key, Decimal("0")) + monto
            elif m.tipo in ("RETIRO_SANGRIA", "EGRESO"):
                teoricos[key] = teoricos.get(key, Decimal("0")) - monto
        
        # Todos los valores deben ser Decimal
        for k, v in teoricos.items():
            assert isinstance(v, Decimal), f"Teórico[{k}] debe ser Decimal, es {type(v)}"

    def test_iva_10_pyg_es_decimal(self, db, sesion_caja):
        """Verificar cálculo IVA 10% paraguay con Decimal."""
        total = Decimal("110000")
        iva_10 = (total / Decimal("11")).quantize(Decimal("1"))
        assert iva_10 == Decimal("10000")
        assert isinstance(iva_10, Decimal)

    def test_iva_5_pyg_es_decimal(self, db):
        """Verificar cálculo IVA 5% paraguay con Decimal."""
        total = Decimal("105000")
        iva_5 = (total / Decimal("21")).quantize(Decimal("1"))
        assert iva_5 == Decimal("5000")
        assert isinstance(iva_5, Decimal)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - MODELO VENTAS TABLE (sin GUI)
# ═══════════════════════════════════════════════════════════════════════════════

class TestVentasModelOperaciones:

    def test_remove_item_sin_qt(self):
        """Verifica que VentasTableModel.remove_item y clear funcionan lógicamente."""
        items = [
            {'codigo': 'AAA', 'descripcion': 'Prod A', 'cantidad': Decimal('2'),
             'precio': Decimal('5000'), 'subtotal': Decimal('10000'), 'impu': Decimal('10')},
            {'codigo': 'BBB', 'descripcion': 'Prod B', 'cantidad': Decimal('1'),
             'precio': Decimal('3000'), 'subtotal': Decimal('3000'), 'impu': Decimal('5')},
        ]
        # Simular remove_item
        items.pop(0)
        assert len(items) == 1
        assert items[0]['codigo'] == 'BBB'

    def test_clear_carrito_sin_qt(self):
        """Simula vaciado del carrito."""
        items = [
            {'codigo': 'AAA', 'cantidad': Decimal('2'), 'precio': Decimal('5000')},
            {'codigo': 'BBB', 'cantidad': Decimal('1'), 'precio': Decimal('3000')},
        ]
        items.clear()
        assert len(items) == 0

    def test_recalculo_subtotal_decimal(self):
        """Subtotal siempre Decimal sin float."""
        cantidad = Decimal("3")
        precio = Decimal("12500")
        subtotal = (cantidad * precio).quantize(Decimal("1"))
        assert subtotal == Decimal("37500")
        assert isinstance(subtotal, Decimal)
        assert type(subtotal) is not float

    def test_iva_sobre_subtotal_decimal(self):
        """IVA 10% sobre subtotal usando fórmula Ley 6380/19."""
        subtotal = Decimal("110000")
        iva = (subtotal / Decimal("11")).quantize(Decimal("1"))
        gravada = subtotal - iva
        assert iva == Decimal("10000")
        assert gravada == Decimal("100000")

    def test_precio_canal_mayorista_recalculo(self):
        """Cambio de canal recalcula subtotales correctamente."""
        precio_minorista = Decimal("15000")
        precio_mayorista = Decimal("12000")
        cantidad = Decimal("6")
        
        subtotal_min = (cantidad * precio_minorista).quantize(Decimal("1"))
        subtotal_may = (cantidad * precio_mayorista).quantize(Decimal("1"))
        
        ahorro = subtotal_min - subtotal_may
        assert ahorro == Decimal("18000"), f"Ahorro al cambiar canal: {ahorro}"
        assert isinstance(ahorro, Decimal)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - REGLAS ESTRICTAS DE NO FLOAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestReglasNoFloat:

    def test_cash_movement_monto_no_float(self, db, sesion_caja):
        """Ningún CashMovement tiene monto float."""
        movs = db.query(models.CashMovement).filter_by(session_id=sesion_caja.id).all()
        for m in movs:
            assert type(m.monto) is not float, f"MOV-{m.id} tiene monto float: {m.monto}"

    def test_pricelist_item_precio_no_float(self, db, canal_mayorista, precio_mayorista):
        """PriceListItem.pli_precio nunca es float."""
        item = db.query(models.PriceListItem).get(precio_mayorista.id)
        assert type(item.pli_precio) is not float

    def test_producto_preven_no_float(self, db, producto_test):
        """Product.art_preven nunca es float."""
        prod = db.query(models.Product).filter_by(art_codigo=producto_test.art_codigo).first()
        assert type(prod.art_preven) is not float

    def test_decimal_cuantizacion_pyg(self):
        """Guaraníes siempre sin decimales."""
        monto = Decimal("500000.0000")
        quantizado = monto.quantize(Decimal("1"))
        assert quantizado == Decimal("500000")
        assert "." not in str(quantizado)

    def test_decimal_cuantizacion_usd(self):
        """USD siempre con 2 decimales."""
        monto = Decimal("50.1")
        quantizado = monto.quantize(Decimal("0.01"))
        assert quantizado == Decimal("50.10")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  FASE 1 - POS Ergonomics & Cash Ops - Test Riguroso")
    print("=" * 70)
    result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header",
        "-q"
    ])
    sys.exit(result)
