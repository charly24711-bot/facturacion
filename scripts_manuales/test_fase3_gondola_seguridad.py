"""
test_fase3_gondola_seguridad.py
===============================
Batería de pruebas automatizadas rigurosas - FASE 3:
  1. Generador Vectorial de Códigos de Barras (EAN-13, Code-128)
  2. Cálculo de Dígitos Verificadores EAN-13 (Balanza 20/21 y Estándar)
  3. Impresor y Renderizador de Etiquetas de Góndola (Multidivisa Decimal)
  4. Seguridad y Bloqueo de Terminal POS (LockScreenDialog con PIN)
  5. Desbloqueo por Supervisor de Emergencia
  6. Respeto estricto a CERO FLOAT en precios y cotizaciones
"""

import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from decimal import Decimal
import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor

from database import SessionLocal
import models
from ui.barcode_renderer import (
    calculate_ean13_checksum, encode_ean13, encode_code128,
    get_barcode_bits, render_barcode_pixmap, draw_shelf_label
)
from ui.lock_screen_dialog import LockScreenDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def test_user_cajero(db):
    user = db.query(models.User).filter_by(username="cajero_fase3").first()
    if not user:
        user = models.User(
            username="cajero_fase3",
            password_hash=models.hash_password("9876"),
            full_name="Cajero Test Fase 3",
            role="CAJERO",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture(scope="module")
def test_user_supervisor(db):
    user = db.query(models.User).filter_by(username="super_fase3").first()
    if not user:
        user = models.User(
            username="super_fase3",
            password_hash=models.hash_password("superpin"),
            full_name="Supervisor Test Fase 3",
            role="GERENTE",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PRUEBAS DEL MOTOR DE CÓDIGO DE BARRAS (EAN-13 Y CODE-128)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBarcodeEngine:
    def test_checksum_ean13_conocidos(self):
        """Verifica el cálculo exacto del dígito verificador módulo 10."""
        # Código con checksum conocido
        chk1 = calculate_ean13_checksum("779123456789")
        assert chk1 == "8", f"Esperado 8, obtenido {chk1}"

        chk2 = calculate_ean13_checksum("784000100105")
        assert chk2 == "6", f"Esperado 6, obtenido {chk2}"

        # Prefijo balanza 20
        chk_balanza = calculate_ean13_checksum("200010501250")
        assert chk_balanza.isdigit() and len(chk_balanza) == 1

    def test_encode_ean13_longitud_y_guardas(self):
        """EAN-13 debe tener exactamente 95 módulos con guardas 101 y 01010."""
        bits, full_code = encode_ean13("7791234567898")
        assert len(bits) == 95, f"EAN-13 debe tener 95 módulos, tiene {len(bits)}"
        assert bits.startswith("101"), "Guarda izquierda debe ser 101"
        assert bits.endswith("101"), "Guarda derecha debe ser 101"
        assert "01010" in bits, "Guarda central debe ser 01010"
        assert len(full_code) == 13

    def test_encode_ean13_relleno_12_digitos(self):
        """Si recibe 12 dígitos, debe calcular automáticamente el checksum y generar 13 dígitos."""
        bits, full_code = encode_ean13("784000100105")
        assert len(full_code) == 13
        assert full_code[-1] == "6"
        assert len(bits) == 95

    def test_encode_code128_alfanumerico(self):
        """Code-128 debe codificar textos con letras, guiones y números."""
        bits, clean = encode_code128("ART-00123")
        assert len(bits) > 0
        assert set(bits).issubset({"0", "1"})
        assert clean == "ART-00123"

    def test_get_barcode_bits_autodeteccion(self):
        """Detecta automáticamente EAN-13 para números de 12/13 dígitos y Code-128 para otros."""
        t1, bits1, _ = get_barcode_bits("7791234567898")
        assert t1 == "EAN13"
        assert len(bits1) == 95

        t2, bits2, _ = get_barcode_bits("INTERNAL-99")
        assert t2 == "CODE128"

        t3, bits3, _ = get_barcode_bits("1234")
        assert t3 == "CODE128"

    def test_render_barcode_pixmap(self, qapp):
        """Genera un QPixmap renderizado válido sin errores."""
        pm = render_barcode_pixmap("7791234567898", width=250, height=80)
        assert not pm.isNull()
        assert pm.width() == 250
        assert pm.height() == 80


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PRUEBAS DE ETIQUETAS DE GÓNDOLA Y MULTIDIVISA DECIMAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestShelfLabels:
    def test_draw_shelf_label_sin_errores(self, qapp):
        """Verifica que el dibujado de la etiqueta en QPainter complete sin excepciones."""
        pm = QPixmap(300, 150)
        pm.fill(QColor("white"))
        painter = QPainter(pm)

        item = {
            "art_codigo": "000105",
            "art_descri": "ARROZ EXTRA PULIDO 1KG",
            "art_codbar": "7840001001056",
            "art_preven": Decimal("6500")
        }

        draw_shelf_label(
            painter,
            QRectF(0, 0, 300, 150),
            item,
            store_name="SUPERMERCADO CENTRAL",
            show_usd=True,
            show_date=True,
            rate_usd=Decimal("7500")
        )
        painter.end()
        assert not pm.isNull()

    def test_calculo_precio_usd_estricto_decimal(self):
        """El precio en USD debe ser cuantizado a 2 decimales sin usar float."""
        precio_pyg = Decimal("15000")
        rate_usd = Decimal("7500")
        precio_usd = (precio_pyg / rate_usd).quantize(Decimal("0.01"))
        assert precio_usd == Decimal("2.00")
        assert isinstance(precio_usd, Decimal)

        # Precio con decimales no exactos
        precio_pyg2 = Decimal("10000")
        precio_usd2 = (precio_pyg2 / rate_usd).quantize(Decimal("0.01"))
        assert precio_usd2 == Decimal("1.33")
        assert isinstance(precio_usd2, Decimal)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PRUEBAS DE SEGURIDAD Y BLOQUEO DE TERMINAL POS (LockScreenDialog)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPOSLockScreen:
    def test_creacion_lock_screen_dialog(self, qapp, test_user_cajero):
        """El diálogo de bloqueo debe instanciarse con el usuario actual."""
        user_dict = {
            "id": test_user_cajero.id,
            "username": test_user_cajero.username,
            "full_name": test_user_cajero.full_name,
            "role": test_user_cajero.role
        }
        dlg = LockScreenDialog(current_user=user_dict)
        assert dlg.current_user["username"] == "cajero_fase3"
        assert dlg.txt_pin is not None
        assert dlg.timer.isActive()
        dlg.timer.stop()

    def test_desbloqueo_clave_correcta_cajero(self, qapp, test_user_cajero):
        """Al ingresar el PIN exacto del cajero, el diálogo debe desbloquear exitosamente."""
        user_dict = {
            "id": test_user_cajero.id,
            "username": test_user_cajero.username,
            "full_name": test_user_cajero.full_name,
            "role": test_user_cajero.role
        }
        dlg = LockScreenDialog(current_user=user_dict)
        dlg.txt_pin.setText("9876")
        dlg.intentar_desbloqueo()
        assert not dlg.timer.isActive()

    def test_rechazo_clave_incorrecta(self, qapp, test_user_cajero):
        """Un PIN erróneo debe incrementar los intentos fallidos y advertir en pantalla."""
        user_dict = {
            "id": test_user_cajero.id,
            "username": test_user_cajero.username,
            "full_name": test_user_cajero.full_name,
            "role": test_user_cajero.role
        }
        dlg = LockScreenDialog(current_user=user_dict)
        dlg.txt_pin.setText("0000")  # Clave incorrecta
        dlg.intentar_desbloqueo()
        assert dlg.failed_attempts == 1
        assert "incorrecta" in dlg.lbl_error.text().lower()

        # Segundo intento fallido
        dlg.txt_pin.setText("1111")
        dlg.intentar_desbloqueo()
        assert dlg.failed_attempts == 2
        dlg.timer.stop()

    def test_desbloqueo_supervisor_override(self, qapp, test_user_cajero, test_user_supervisor):
        """Un supervisor/gerente puede desbloquear la terminal de un cajero ausente con su clave maestra."""
        user_dict = {
            "id": test_user_cajero.id,
            "username": test_user_cajero.username,
            "full_name": test_user_cajero.full_name,
            "role": test_user_cajero.role
        }
        dlg = LockScreenDialog(current_user=user_dict)
        # Ingresar la clave del supervisor
        dlg.txt_pin.setText("superpin")
        dlg.intentar_desbloqueo()
        assert not dlg.timer.isActive()

    def test_solicitar_cierre_sesion_flag(self, qapp, test_user_cajero, monkeypatch):
        """Si el cajero confirma salida, debe marcarse logout_requested."""
        from PyQt6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

        user_dict = {
            "id": test_user_cajero.id,
            "username": test_user_cajero.username,
            "full_name": test_user_cajero.full_name,
            "role": test_user_cajero.role
        }
        dlg = LockScreenDialog(current_user=user_dict)
        dlg.solicitar_cierre_sesion()
        assert dlg.logout_requested is True


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PRUEBAS DE REGLA ESTRICTA CERO FLOAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestReglasFase3:
    def test_cero_float_en_precios_etiquetas(self, db):
        """Ningún producto activo en la base de datos debe almacenar o procesar precios como float."""
        prods = db.query(models.Product).filter(models.Product.is_active == True).limit(20).all()
        for p in prods:
            assert isinstance(p.art_preven, Decimal), f"El precio de {p.art_codigo} debe ser Decimal, no {type(p.art_preven)}"
            if p.art_costo is not None:
                assert isinstance(p.art_costo, Decimal)
