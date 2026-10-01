"""
utils/scale_driver.py - Driver y Worker Asíncrono para Balanzas de Mostrador RS232 / USB-Serial

Soporta protocolos estándar de la Triple Frontera:
- Toledo / Systel / Filizola / CAS / Genérico ASCII.
- Manejo 100% en decimal.Decimal (hasta 3 decimales para Kg).
- MockScaleDriver para entorno de desarrollo y pruebas automatizadas.
- ScaleWorker (QThread) para lectura continua sin bloqueo del hilo principal de la UI.
"""

import re
import time
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
from abc import ABC, abstractmethod

from PyQt6.QtCore import QThread, pyqtSignal, QMutex

logger = logging.getLogger("ScaleDriver")
logger.setLevel(logging.INFO)


class ScaleProtocolParser:
    """Parser determinista de tramas seriales de balanzas de mostrador."""

    @staticmethod
    def parse_frame(raw_data: str) -> Tuple[Optional[Decimal], bool]:
        """
        Interpreta la trama cruda y devuelve (peso_decimal, is_stable).
        Soporta:
        1. Toledo / Systel: STX (0x02) + 5 dígitos de peso + ETX (0x03) o con decimal implícito.
        2. ASCII Estándar: "ST,GS,+001.450kg", "WN001.450kg", "1.450 kg", "01.450".
        3. Simple numérico: "1.450".
        """
        if not raw_data:
            return None, False

        cleaned = raw_data.strip()
        is_stable = True

        # Verificar indicador de inestabilidad común en protocolos
        if "US" in cleaned or "?" in cleaned or "IN" in cleaned:
            is_stable = False

        # 1. Intentar extraer número con punto/coma decimal
        match = re.search(r'[-+]?\s*(\d+[\.,]\d{1,4})', cleaned)
        if match:
            num_str = match.group(1).replace(',', '.')
            try:
                weight = Decimal(num_str).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                return max(Decimal('0.000'), weight), is_stable
            except Exception:
                pass

        # 2. Formato de 5 dígitos enteros (gramos, ej. 01450 -> 1.450 kg)
        match_digits = re.search(r'(\d{5})', cleaned)
        if match_digits:
            try:
                grams = Decimal(match_digits.group(1))
                weight = (grams / Decimal('1000')).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                return max(Decimal('0.000'), weight), is_stable
            except Exception:
                pass

        return None, False


class BaseScaleDriver(ABC):
    """Interfaz base para el driver de balanza."""

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def read_weight(self) -> Tuple[Optional[Decimal], bool]:
        """Devuelve (peso_en_kg, is_stable)."""
        pass


class MockScaleDriver(BaseScaleDriver):
    """Simulador de balanza en memoria para testing y modo desarrollo."""

    def __init__(self, current_weight: Decimal = Decimal('0.000'), is_stable: bool = True):
        self.current_weight = current_weight.quantize(Decimal('0.001'))
        self.is_stable = is_stable
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def set_weight(self, weight: Decimal, is_stable: bool = True):
        self.current_weight = Decimal(str(weight)).quantize(Decimal('0.001'))
        self.is_stable = is_stable

    def read_weight(self) -> Tuple[Optional[Decimal], bool]:
        if not self._connected:
            return None, False
        return self.current_weight, self.is_stable


class SerialScaleDriver(BaseScaleDriver):
    """Driver para balanzas reales conectadas vía RS232 / USB-Serial."""

    def __init__(self, port: str = "COM1", baudrate: int = 9600, timeout: float = 0.5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None

    def connect(self) -> bool:
        try:
            import serial
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            return self.serial_conn.is_open
        except Exception as e:
            logger.warning(f"No se pudo abrir el puerto serie {self.port}: {e}")
            self.serial_conn = None
            return False

    def disconnect(self) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None

    def read_weight(self) -> Tuple[Optional[Decimal], bool]:
        if not self.serial_conn or not self.serial_conn.is_open:
            return None, False

        try:
            raw_line = self.serial_conn.readline().decode('ascii', errors='ignore')
            return ScaleProtocolParser.parse_frame(raw_line)
        except Exception as e:
            logger.debug(f"Error al leer puerto serial: {e}")
            return None, False


class ScaleWorker(QThread):
    """
    Worker asíncrono para PyQt6 que hace polling continuo de la balanza en segundo plano.
    """
    weight_changed = pyqtSignal(Decimal, bool)  # (peso_kg, is_stable)
    connection_changed = pyqtSignal(bool)       # True=Conectada, False=Desconectada

    def __init__(self, driver: BaseScaleDriver, poll_interval_ms: int = 200, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.poll_interval_ms = poll_interval_ms
        self._running = True
        self._mutex = QMutex()
        self.last_weight = Decimal('0.000')
        self.last_stable = False

    def stop(self):
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()
        self.wait(1000)

    def run(self):
        is_connected = self.driver.connect()
        self.connection_changed.emit(is_connected)

        while self._running:
            try:
                weight, is_stable = self.driver.read_weight()
                if weight is not None:
                    if weight != self.last_weight or is_stable != self.last_stable:
                        self.last_weight = weight
                        self.last_stable = is_stable
                        self.weight_changed.emit(weight, is_stable)
            except Exception as e:
                logger.error(f"Error en bucle de balanza: {e}")

            time.sleep(self.poll_interval_ms / 1000.0)

        self.driver.disconnect()
        self.connection_changed.emit(False)
