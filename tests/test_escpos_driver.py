import pytest
import os
import sys
from decimal import Decimal
import datetime

# Asegurar path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))

from PyQt6.QtWidgets import QApplication
from utils.escpos_driver import (
    ESCPOSCommandBuilder, ESCPOSPrinterDriver, ESCPOSPrintWorker
)
from database import SessionLocal, Base, engine
import models
from ui.ticket_dialog import TicketDialog

# Fixture de aplicación Qt headless
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestESCPOSDriver:
    """Suite de Pruebas Unitarias para el Driver de Impresión Térmica ESC/POS"""

    def test_01_command_builder_basic_sequences(self):
        """Verifica que los comandos básicos ESC/POS generen los códigos de escape binarios estándar."""
        builder = ESCPOSCommandBuilder(width=40)
        builder.init_printer()
        builder.align_center()
        builder.bold(True)
        builder.text_line("SUPERMERCADO CENTRAL")
        builder.bold(False)
        builder.align_left()
        builder.text_line("Articulo 1")
        builder.align_right()
        builder.text_line("Gs. 50.000")
        builder.open_cash_drawer(pin=0)
        builder.feed(3)
        builder.cut_paper(partial=True)
        
        raw = builder.get_bytes()
        
        # Comprobación de bytes clave
        assert b'\x1b@' in raw, "Debe contener ESC @ para inicializar"
        assert b'\x1ba\x01' in raw, "Debe contener ESC a 1 para centrado"
        assert b'\x1bE\x01' in raw, "Debe contener ESC E 1 para activar negrita"
        assert b'\x1bE\x00' in raw, "Debe contener ESC E 0 para desactivar negrita"
        assert b'\x1ba\x00' in raw, "Debe contener ESC a 0 para alinear a la izquierda"
        assert b'\x1ba\x02' in raw, "Debe contener ESC a 2 para alinear a la derecha"
        assert b'\x1bp\x00\x19\xfa' in raw, "Debe contener el pulso de apertura de cajón ESC p 0 25 250"
        assert b'\x1bd\x03' in raw, "Debe contener el avance de 3 líneas ESC d 3"
        assert b'\x1dV\x42\x00' in raw, "Debe contener el comando de corte parcial GS V 66 0"

    def test_02_native_qr_code_structure(self):
        """Verifica la secuencia nativa ESC/POS para generación de códigos QR (GS ( k)."""
        builder = ESCPOSCommandBuilder()
        qr_data = "https://ekuatia.set.gov.py/consultas-sifen/qr?nVersion=150&Id=01800123456001001000000112026100111000000015"
        builder.qr_code(qr_data, size=4)
        raw = builder.get_bytes()
        
        # Modelo 2: GS ( k \x04\x00 1 A 2 0
        assert b'\x1d(k\x04\x001A2\x00' in raw
        # Tamaño 4: GS ( k \x03\x00 1 C \x04
        assert b'\x1d(k\x03\x001C\x04' in raw
        # Nivel de corrección M: GS ( k \x03\x00 1 E 1
        assert b'\x1d(k\x03\x001E1' in raw
        # Comando imprimir QR: GS ( k \x03\x00 1 Q 0
        assert b'\x1d(k\x03\x001Q0' in raw
        # Contenido de la URL codificado
        assert qr_data.encode('utf-8') in raw

    def test_03_column_and_separator_formatting(self):
        """Verifica el cálculo de ancho para columnas y separadores."""
        builder = ESCPOSCommandBuilder(width=40)
        builder.separator("=")
        builder.two_columns("TOTAL Gs.:", "1.250.000")
        
        raw_lines = builder.get_bytes().decode('cp850', errors='ignore').split('\n')
        clean_lines = [l.replace('\x1b@', '').strip('\r') for l in raw_lines]
        
        # Debe haber una línea de 40 signos '='
        assert "=" * 40 in clean_lines
        
        # La línea de dos columnas debe tener longitud 40
        found = False
        for l in clean_lines:
            if "TOTAL Gs.:" in l:
                assert len(l) == 40
                assert l.startswith("TOTAL Gs.:")
                assert l.endswith("1.250.000")
                found = True
        assert found

    def test_04_simulator_driver_execution(self):
        """Verifica que el driver en modo SIMULATOR capture correctamente los bytes sin hardware físico."""
        driver = ESCPOSPrinterDriver(connection_type=ESCPOSPrinterDriver.CONN_SIMULATOR)
        
        builder = ESCPOSCommandBuilder()
        builder.text_line("TEST SIMULADOR 123")
        
        success, msg = driver.send_raw(builder.get_bytes())
        assert success is True
        assert "Simulador" in msg
        assert b"TEST SIMULADOR 123" in driver.simulated_output

        # Probar apertura de gaveta
        success_drawer, _ = driver.open_drawer()
        assert success_drawer is True
        assert b'\x1bp\x00\x19\xfa' in driver.simulated_output

    def test_05_network_failure_resilience(self):
        """Verifica que ante un fallo de conexión a IP inalcanzable, el driver maneje el error limpiamente sin lanzar excepciones no controladas."""
        # IP inválida y timeout ultracorto (0.2s)
        driver = ESCPOSPrinterDriver(
            connection_type=ESCPOSPrinterDriver.CONN_NETWORK,
            ip="192.0.2.1", # Dirección de prueba no enrutable (RFC 5737)
            port=9100,
            timeout=0.2
        )
        success, msg = driver.send_raw(b"TEST BYTES")
        assert success is False
        assert len(msg) > 0

    def test_06_ticket_dialog_escpos_integration(self, qapp):
        """Verifica la generación completa del flujo binario ESC/POS dentro de TicketDialog."""
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        
        # Crear o buscar factura de prueba
        inv = db.query(models.Invoice).first()
        if not inv:
            inv = models.Invoice(
                ven_numero=999991,
                ven_fecha=datetime.datetime.now(),
                ven_total=Decimal("150000"),
                ven_estado=1
            )
            db.add(inv)
            db.commit()
            db.refresh(inv)
        
        dlg = TicketDialog(invoice_id=inv.id)
        assert len(dlg.escpos_bytes) > 0, "Debe generar bytes ESC/POS"
        
        # Verificar que contiene los comandos binarios clave
        assert b'\x1b@' in dlg.escpos_bytes
        assert b'\x1dV\x42\x00' in dlg.escpos_bytes # Corte
        assert dlg.cdc_code.encode('ascii') in dlg.escpos_bytes or len(dlg.cdc_code) == 44
        assert b'https://ekuatia.set.gov.py' in dlg.escpos_bytes
        
        db.close()
