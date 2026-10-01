"""
tests/test_touch_catalog.py - Suite de Pruebas para Catálogo Táctil y Balanza RS232 (SPEC-007)
Valida:
1. Parser de tramas de balanza con cuantización estricta Decimal('0.001').
2. MockScaleDriver y ScaleWorker.
3. Cálculo de cantidades, pesos y subtotales en TouchQuantityDialog.
4. Filtrado y selección en TouchCatalogDialog.
5. Validación pre-transaccional mediante POSGuardrail.
"""

import pytest
from decimal import Decimal
from PyQt6.QtWidgets import QApplication

from utils.scale_driver import ScaleProtocolParser, MockScaleDriver, ScaleWorker
from ui.touch_numpad_dialog import TouchQuantityDialog
from ui.touch_catalog_dialog import TouchProductCard, TouchCatalogDialog
from validator.validator import POSGuardrail
import models

# Asegurar QApplication para widgets PyQt6
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestScaleAndTouchCatalog:

    def test_01_scale_protocol_parser(self):
        """Verifica el parsing de tramas de diversos fabricantes de balanzas."""
        # 1. ASCII Estándar
        w1, s1 = ScaleProtocolParser.parse_frame("ST,GS,+001.450kg\r\n")
        assert w1 == Decimal('1.450')
        assert s1 is True

        # 2. Inestable
        w2, s2 = ScaleProtocolParser.parse_frame("US,GS,+002.300kg\r\n")
        assert w2 == Decimal('2.300')
        assert s2 is False

        # 3. Formato 5 dígitos en gramos (01250 -> 1.250 kg)
        w3, s3 = ScaleProtocolParser.parse_frame("\x0201250\x03")
        assert w3 == Decimal('1.250')
        assert s3 is True

        # 4. Simple numérico
        w4, s4 = ScaleProtocolParser.parse_frame("0.875")
        assert w4 == Decimal('0.875')

    def test_02_mock_scale_driver(self):
        """Verifica la simulación de lectura de peso con MockScaleDriver."""
        driver = MockScaleDriver(current_weight=Decimal('0.500'), is_stable=True)
        assert driver.connect() is True

        w, s = driver.read_weight()
        assert w == Decimal('0.500')
        assert s is True

        # Modificar peso dinámicamente
        driver.set_weight(Decimal('2.150'), is_stable=True)
        w2, s2 = driver.read_weight()
        assert w2 == Decimal('2.150')

    def test_03_touch_quantity_dialog_presets(self, qapp):
        """Valida que TouchQuantityDialog maneje correctamente los presets y el subtotal con Decimal."""
        dialog = TouchQuantityDialog(
            product_name="TOMATE SANTA CRUZ",
            unit_price=Decimal('12000'),
            uom="Kg",
            initial_qty=Decimal('0.500'),
            live_scale_weight=Decimal('1.250')
        )

        assert dialog.get_quantity() == Decimal('0.500')

        # Aplicar preset +250g
        dialog._add_preset(Decimal('0.250'))
        assert dialog.get_quantity() == Decimal('0.750')

        # Subtotal esperado: 0.750 * 12000 = 9000
        subtotal = (dialog.get_quantity() * dialog.unit_price).quantize(Decimal('1'))
        assert subtotal == Decimal('9000')

        # Capturar balanza en vivo
        dialog._capture_live_scale()
        assert dialog.get_quantity() == Decimal('1.250')
        subtotal_scale = (dialog.get_quantity() * dialog.unit_price).quantize(Decimal('1'))
        assert subtotal_scale == Decimal('15000')

    def test_04_touch_catalog_filtering(self, qapp):
        """Verifica el filtrado por texto y categoría en TouchCatalogDialog."""
        scale = MockScaleDriver(current_weight=Decimal('1.800'))
        dialog = TouchCatalogDialog(scale_driver=scale)

        # Crear productos simulados
        p1 = models.Product(art_codigo="FRUT01", art_descri="BANANA DE ORO", art_preven=Decimal('6000'), uom="Kg", is_fractional=True)
        p2 = models.Product(art_codigo="PANA01", art_descri="PAN FRANCES", art_preven=Decimal('9000'), uom="Kg", is_fractional=True)
        p3 = models.Product(art_codigo="BEB01", art_descri="GASEOSA COCA COLA 500ML", art_preven=Decimal('7000'), uom="Un", is_fractional=False)

        dialog.all_products = [p1, p2, p3]

        # Filtrar por "banana"
        dialog._filter_products("banana")
        assert len(dialog.cards_container.findChildren(TouchProductCard)) == 1

        # Limpiar búsqueda y filtrar por categoría "Panaderia"
        dialog.txt_search.clear()
        dialog._set_category_filter("Panaderia")
        assert len(dialog.cards_container.findChildren(TouchProductCard)) == 1

    def test_05_guardrail_validation_for_weighed_item(self):
        """Valida que un producto pesado del catálogo táctil pase el guardrail de ventas."""
        product = models.Product(
            art_codigo="FRUT02",
            art_descri="MANZANA ROJA",
            art_preven=Decimal('15000'),
            art_impu=Decimal('10'),
            uom="Kg",
            is_fractional=True
        )
        peso_capturado = Decimal('1.450')

        # Validación con POSGuardrail pasando diccionario payload
        status = POSGuardrail.validate_sale_item({
            "plu_code": product.art_codigo,
            "description": product.art_descri,
            "quantity": str(peso_capturado),
            "unit_price": str(product.art_preven),
            "tax_rate": 10
        })

        assert status.is_valid is True
        assert status.clean_data["quantity"] == Decimal('1.450')
        # Subtotal: 1.450 * 15000 = 21750
        assert status.clean_data["subtotal"] == Decimal('21750')
