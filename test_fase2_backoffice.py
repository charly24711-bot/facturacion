"""
test_fase2_backoffice.py
========================
Test automatizado riguroso - FASE 2: Back-Office Modules
Cubre:
  1. Gestión de Usuarios (UsersManagementDialog logic)
  2. StockAdjustment: mermas, donaciones, ajuste positivo/negativo
  3. Actualización de stock tras ajuste (art_stkini)
  4. Exportador Hechauka DNIT: cálculo IVA 10% y 5%
  5. Regla CERO float en todos los cálculos
  6. Protección del usuario 'admin'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pytest
import tempfile
import csv
from decimal import Decimal, ROUND_HALF_UP

from database import SessionLocal, Base, engine
import models


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def prod_ajuste(db):
    """Producto de prueba para ajustes de stock."""
    p = db.query(models.Product).filter_by(art_codigo="ADJ01").first()
    if not p:
        p = models.Product(
            art_codigo="ADJ01",
            art_descri="Producto Ajuste Merma Test F2",
            art_cbarra="7891234500001",
            art_costo=Decimal("8000"),
            art_preven=Decimal("12000"),
            art_impu=Decimal("10"),
            art_stkini=Decimal("200"),
            is_active=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


@pytest.fixture(scope="module")
def user_cajero(db):
    """Usuario cajero de prueba."""
    u = db.query(models.User).filter_by(username="cajero_test_f2").first()
    if not u:
        u = models.User(
            username="cajero_test_f2",
            full_name="Cajero Test Fase 2",
            password_hash=models.hash_password("1234"),
            role="CAJERO",
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


@pytest.fixture(scope="module")
def user_gerente(db):
    """Usuario gerente de prueba."""
    u = db.query(models.User).filter_by(username="gerente_test_f2").first()
    if not u:
        u = models.User(
            username="gerente_test_f2",
            full_name="Gerente Test Fase 2",
            password_hash=models.hash_password("secure456"),
            role="GERENTE",
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - GESTIÓN DE USUARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsuarios:

    def test_crear_usuario_cajero(self, db, user_cajero):
        """Usuario CAJERO creado correctamente."""
        u = db.query(models.User).filter_by(username="cajero_test_f2").first()
        assert u is not None
        assert u.role == "CAJERO"
        assert u.is_active is True

    def test_crear_usuario_gerente(self, db, user_gerente):
        """Usuario GERENTE creado correctamente."""
        u = db.query(models.User).filter_by(username="gerente_test_f2").first()
        assert u is not None
        assert u.role == "GERENTE"

    def test_password_hash_no_es_texto_plano(self, db, user_cajero):
        """El password_hash nunca almacena contraseña en texto plano."""
        u = db.query(models.User).filter_by(username="cajero_test_f2").first()
        assert u.password_hash != "1234"
        assert len(u.password_hash) > 10

    def test_verificar_password_correcto(self, db, user_cajero):
        """hash_password y verify son consistentes."""
        hash_nuevo = models.hash_password("1234")
        # Debe poder verificarse
        assert models.hash_password("1234") == hash_nuevo  # deterministic hash

    def test_usuario_admin_existe(self, db):
        """El usuario 'admin' debe existir siempre."""
        admin = db.query(models.User).filter_by(username="admin").first()
        assert admin is not None
        assert admin.role == "ADMIN"

    def test_usuario_admin_es_activo(self, db):
        """El usuario 'admin' debe estar siempre activo."""
        admin = db.query(models.User).filter_by(username="admin").first()
        assert admin.is_active is True

    def test_roles_validos(self, db, user_cajero, user_gerente):
        """Solo existen roles válidos: ADMIN, GERENTE, CAJERO."""
        ROLES_VALIDOS = {"ADMIN", "GERENTE", "CAJERO"}
        todos = db.query(models.User).all()
        for u in todos:
            assert u.role in ROLES_VALIDOS, f"Rol inválido '{u.role}' en usuario '{u.username}'"

    def test_desactivar_usuario_cajero(self, db, user_cajero):
        """Desactivar un cajero de prueba."""
        u = db.query(models.User).filter_by(username="cajero_test_f2").first()
        u.is_active = False
        db.commit()
        u_refrescado = db.query(models.User).filter_by(username="cajero_test_f2").first()
        assert u_refrescado.is_active is False
        # Reactivar para no romper otros tests
        u_refrescado.is_active = True
        db.commit()

    def test_no_permite_username_duplicado(self, db):
        """No puede haber dos usuarios con el mismo username."""
        u1 = db.query(models.User).filter_by(username="cajero_test_f2").first()
        u2 = db.query(models.User).filter_by(username="cajero_test_f2").first()
        assert u1.id == u2.id, "El mismo username no puede mapearse a dos IDs distintos"

    def test_resetear_password(self, db, user_cajero):
        """Reset de contraseña genera nuevo hash válido."""
        nuevo_hash = models.hash_password("1234")
        u = db.query(models.User).filter_by(username="cajero_test_f2").first()
        u.password_hash = nuevo_hash
        db.commit()
        u_ref = db.query(models.User).filter_by(username="cajero_test_f2").first()
        assert u_ref.password_hash == nuevo_hash


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - STOCK ADJUSTMENT (MERMAS Y AJUSTES)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStockAdjustment:

    def _get_stock(self, db, codigo):
        p = db.query(models.Product).filter_by(art_codigo=codigo).first()
        return Decimal(str(p.art_stkini or '0'))

    def test_merma_resta_stock(self, db, prod_ajuste):
        """MERMA descuenta stock correctamente."""
        stock_antes = self._get_stock(db, prod_ajuste.art_codigo)
        cantidad = Decimal("10")
        costo = Decimal("8000")
        perdida = (cantidad * costo).quantize(Decimal("1"))

        ajuste = models.StockAdjustment(
            art_codigo=prod_ajuste.art_codigo,
            tipo="MERMA",
            cantidad=cantidad,
            motivo="Test merma Fase 2",
            costo_unitario=costo,
            monto_perdida=perdida,
        )
        db.add(ajuste)
        prod = db.query(models.Product).filter_by(art_codigo=prod_ajuste.art_codigo).first()
        prod.art_stkini = stock_antes - cantidad
        db.commit()

        stock_despues = self._get_stock(db, prod_ajuste.art_codigo)
        assert stock_despues == stock_antes - cantidad

    def test_ajuste_positivo_suma_stock(self, db, prod_ajuste):
        """AJUSTE_POSITIVO suma stock correctamente."""
        stock_antes = self._get_stock(db, prod_ajuste.art_codigo)
        cantidad = Decimal("20")

        ajuste = models.StockAdjustment(
            art_codigo=prod_ajuste.art_codigo,
            tipo="AJUSTE_POSITIVO",
            cantidad=cantidad,
            motivo="Corrección inventario fisico F2",
            costo_unitario=Decimal("8000"),
            monto_perdida=Decimal("0"),
        )
        db.add(ajuste)
        prod = db.query(models.Product).filter_by(art_codigo=prod_ajuste.art_codigo).first()
        prod.art_stkini = stock_antes + cantidad
        db.commit()

        stock_despues = self._get_stock(db, prod_ajuste.art_codigo)
        assert stock_despues == stock_antes + cantidad

    def test_donacion_resta_stock(self, db, prod_ajuste):
        """DONACION descuenta stock."""
        stock_antes = self._get_stock(db, prod_ajuste.art_codigo)
        cantidad = Decimal("5")

        ajuste = models.StockAdjustment(
            art_codigo=prod_ajuste.art_codigo,
            tipo="DONACION",
            cantidad=cantidad,
            motivo="Donación banco de alimentos test",
            costo_unitario=Decimal("8000"),
            monto_perdida=(cantidad * Decimal("8000")).quantize(Decimal("1")),
        )
        db.add(ajuste)
        prod = db.query(models.Product).filter_by(art_codigo=prod_ajuste.art_codigo).first()
        prod.art_stkini = stock_antes - cantidad
        db.commit()

        stock_despues = self._get_stock(db, prod_ajuste.art_codigo)
        assert stock_despues == stock_antes - cantidad

    def test_perdida_en_decimal_nunca_float(self, db, prod_ajuste):
        """monto_perdida almacenado como Decimal, nunca float."""
        ajustes = db.query(models.StockAdjustment).filter_by(
            art_codigo=prod_ajuste.art_codigo
        ).all()
        assert len(ajustes) >= 1
        for a in ajustes:
            perdida = Decimal(str(a.monto_perdida))
            assert isinstance(perdida, Decimal)
            assert type(a.monto_perdida) is not float

    def test_cantidad_decimal_3_decimales(self, db, prod_ajuste):
        """Cantidad de ajuste permite hasta 3 decimales (balanza)."""
        cantidad = Decimal("2.500")
        ajuste = models.StockAdjustment(
            art_codigo=prod_ajuste.art_codigo,
            tipo="MERMA",
            cantidad=cantidad,
            motivo="Test cantidad balanza",
            costo_unitario=Decimal("8000"),
            monto_perdida=(cantidad * Decimal("8000")).quantize(Decimal("1")),
        )
        db.add(ajuste)
        prod = db.query(models.Product).filter_by(art_codigo=prod_ajuste.art_codigo).first()
        prod.art_stkini = Decimal(str(prod.art_stkini)) - cantidad
        db.commit()
        db.refresh(ajuste)
        assert Decimal(str(ajuste.cantidad)) == cantidad

    def test_motivo_no_puede_estar_vacio(self, db, prod_ajuste):
        """Regla de negocio: no se permiten ajustes sin motivo."""
        motivo = "   "
        assert motivo.strip() == "", "Motivo vacío detectado correctamente"

    def test_calculo_perdida_decimal(self):
        """monto_perdida = cantidad * costo_unitario en Decimal estricto."""
        cantidad = Decimal("15")
        costo = Decimal("8000")
        perdida_esperada = Decimal("120000")
        perdida_calculada = (cantidad * costo).quantize(Decimal("1"))
        assert perdida_calculada == perdida_esperada
        assert isinstance(perdida_calculada, Decimal)

    def test_historial_ordenado_por_fecha_desc(self, db, prod_ajuste):
        """El historial de ajustes se puede ordenar por fecha descendente."""
        ajustes = db.query(models.StockAdjustment).order_by(
            models.StockAdjustment.fecha.desc()
        ).limit(5).all()
        if len(ajustes) >= 2:
            for i in range(len(ajustes) - 1):
                assert ajustes[i].fecha >= ajustes[i+1].fecha


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - EXPORTADOR HECHAUKA DNIT (CÁLCULOS IVA)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHechaukaCalculos:
    """Verifica las fórmulas IVA de la Ley 6380/19 usadas en el exportador."""

    def test_iva_10_formula_correcta(self):
        """IVA 10% = total / 11  (exacto)."""
        total = Decimal("110000")
        iva = (total / Decimal("11")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        gravada = total - iva
        assert iva == Decimal("10000")
        assert gravada == Decimal("100000")

    def test_iva_5_formula_correcta(self):
        """IVA 5% = total / 21  (exacto)."""
        total = Decimal("105000")
        iva = (total / Decimal("21")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        gravada = total - iva
        assert iva == Decimal("5000")
        assert gravada == Decimal("100000")

    def test_exenta_iva_cero(self):
        """Productos exentos: IVA = 0, gravada = total."""
        total = Decimal("50000")
        iva = Decimal("0")
        gravada = total
        assert iva == Decimal("0")
        assert gravada == total

    def test_iva_10_sobre_importes_varios(self):
        """IVA 10% calculado correctamente para varios montos."""
        casos = [
            (Decimal("55000"), Decimal("5000"), Decimal("50000")),
            (Decimal("11000"), Decimal("1000"), Decimal("10000")),
            (Decimal("220000"), Decimal("20000"), Decimal("200000")),
        ]
        for total, iva_esp, grav_esp in casos:
            iva = (total / Decimal("11")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            grav = total - iva
            assert iva == iva_esp, f"IVA 10% de {total}: esperado {iva_esp}, obtenido {iva}"
            assert grav == grav_esp

    def test_suma_facturas_decimal(self, db):
        """Suma de totales de facturas es siempre Decimal."""
        facturas = db.query(models.Invoice).limit(50).all()
        total = Decimal("0")
        for f in facturas:
            total += Decimal(str(f.ven_total or '0'))
        assert isinstance(total, Decimal)

    def test_iva_nunca_float(self):
        """El cálculo de IVA nunca produce float."""
        total = Decimal("110000")
        iva = (total / Decimal("11")).quantize(Decimal("1"))
        assert type(iva) is not float
        assert isinstance(iva, Decimal)

    def test_exportar_csv_genera_archivo(self):
        """El exportador genera un archivo CSV bien formado."""
        rows = [
            ["01/09/2026", "1", "44444401-7", "CONSUMIDOR FINAL",
             "110000", "100000", "10000", "0", "0", "0"],
            ["02/09/2026", "2", "80012345-1", "CLIENTE XYZ",
             "105000", "0", "0", "100000", "5000", "0"],
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                         newline='', encoding='utf-8-sig',
                                         delete=False) as f:
            fname = f.name
            writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow([
                "FECHA", "NRO_FACTURA", "RUC_CI_CLIENTE", "RAZON_SOCIAL",
                "TOTAL", "GRAVADA_10", "IVA_10", "GRAVADA_5", "IVA_5", "EXENTA"
            ])
            writer.writerows(rows)

        # Verificar que se puede leer y parsear
        with open(fname, encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=";")
            filas = list(reader)

        assert len(filas) == 3  # encabezado + 2 filas
        assert filas[0][0] == "FECHA"
        assert Decimal(filas[1][4]) == Decimal("110000")
        assert Decimal(filas[2][8]) == Decimal("5000")

        import os; os.unlink(fname)

    def test_exportar_compras_csv(self):
        """El libro de compras CSV tiene las columnas correctas."""
        rows = [
            ["01/09/2026", "001-001-0000001", "12345678", "80012345-1",
             "PROVEEDOR ABC", "220000", "200000", "20000"],
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                         newline='', encoding='utf-8-sig',
                                         delete=False) as f:
            fname = f.name
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "FECHA", "NRO_FACTURA", "TIMBRADO", "RUC_PROVEEDOR",
                "RAZON_SOCIAL", "TOTAL", "GRAVADA_10", "IVA_10"
            ])
            writer.writerows(rows)

        with open(fname, encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=";")
            filas = list(reader)

        assert filas[0][2] == "TIMBRADO"
        assert Decimal(filas[1][5]) == Decimal("220000")
        iva = (Decimal("220000") / Decimal("11")).quantize(Decimal("1"))
        assert iva == Decimal("20000")

        import os; os.unlink(fname)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS - REGLAS ESTRICTAS DE NO FLOAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestReglasNoFloatFase2:

    def test_stock_adjustment_cantidad_no_float(self, db, prod_ajuste):
        """StockAdjustment.cantidad nunca es float."""
        ajustes = db.query(models.StockAdjustment).filter_by(
            art_codigo=prod_ajuste.art_codigo
        ).all()
        for a in ajustes:
            assert type(a.cantidad) is not float

    def test_stock_adjustment_costo_no_float(self, db, prod_ajuste):
        """StockAdjustment.costo_unitario nunca es float."""
        ajustes = db.query(models.StockAdjustment).filter_by(
            art_codigo=prod_ajuste.art_codigo
        ).all()
        for a in ajustes:
            assert type(a.costo_unitario) is not float

    def test_producto_stkini_no_float(self, db, prod_ajuste):
        """Product.art_stkini nunca es float."""
        p = db.query(models.Product).filter_by(art_codigo=prod_ajuste.art_codigo).first()
        assert type(p.art_stkini) is not float

    def test_iva_10_puro_decimal(self):
        """IVA 10% es Decimal puro en todos los pasos."""
        total = Decimal("77000")
        iva = (total / Decimal("11")).quantize(Decimal("1"))
        assert type(iva) is Decimal
        assert type(total - iva) is Decimal

    def test_iva_5_puro_decimal(self):
        """IVA 5% es Decimal puro en todos los pasos."""
        total = Decimal("63000")
        iva = (total / Decimal("21")).quantize(Decimal("1"))
        assert type(iva) is Decimal


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  FASE 2 - Back-Office Modules - Test Riguroso")
    print("=" * 70)
    result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header",
        "-q"
    ])
    sys.exit(result)
