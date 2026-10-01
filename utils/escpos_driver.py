"""
Driver Directo de Impresión ESC/POS para Puntos de Venta (POS)
Soporta canales: RED (TCP/IP), Windows Spooler RAW (USB), Serial (COM) y Simulador.
Garantiza ejecución no bloqueante con QThread y tolerancia a fallos.
"""

from decimal import Decimal
import socket
import sys
import os
import io
import time
import logging
from typing import Optional, Tuple, List

# PyQt6 para worker asíncrono
try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    # Fallback si se ejecuta en entorno sin GUI
    class QThread:
        def __init__(self, parent=None): pass
    def pyqtSignal(*args):
        class DummySignal:
            def emit(self, *a): pass
            def connect(self, slot): pass
        return DummySignal()

logger = logging.getLogger("ESCPOSDriver")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [ESC/POS] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ESCPOSCommandBuilder:
    """
    Constructor fluido de secuencias de bytes binarias para impresoras térmicas ESC/POS (80mm y 58mm).
    """
    # Constantes ESC/POS
    ESC = b'\x1b'
    FS = b'\x1c'
    GS = b'\x1d'
    
    def __init__(self, encoding: str = 'cp850', width: int = 40):
        self.encoding = encoding
        self.width = width
        self.buffer = bytearray()
        self.init_printer()

    def init_printer(self) -> 'ESCPOSCommandBuilder':
        """Inicializa la impresora a su estado por defecto (ESC @)."""
        self.buffer.extend(self.ESC + b'@')
        return self

    def align_left(self) -> 'ESCPOSCommandBuilder':
        """Alinea texto a la izquierda (ESC a 0)."""
        self.buffer.extend(self.ESC + b'a\x00')
        return self

    def align_center(self) -> 'ESCPOSCommandBuilder':
        """Centra el texto (ESC a 1)."""
        self.buffer.extend(self.ESC + b'a\x01')
        return self

    def align_right(self) -> 'ESCPOSCommandBuilder':
        """Alinea texto a la derecha (ESC a 2)."""
        self.buffer.extend(self.ESC + b'a\x02')
        return self

    def bold(self, enable: bool = True) -> 'ESCPOSCommandBuilder':
        """Activa o desactiva texto en negrita (ESC E n)."""
        self.buffer.extend(self.ESC + (b'E\x01' if enable else b'E\x00'))
        return self

    def underline(self, enable: bool = True) -> 'ESCPOSCommandBuilder':
        """Activa o desactiva subrayado (ESC - n)."""
        self.buffer.extend(self.ESC + (b'-\x01' if enable else b'-\x00'))
        return self

    def font_size(self, double_width: bool = False, double_height: bool = False) -> 'ESCPOSCommandBuilder':
        """Modifica el tamaño de la fuente (GS ! n)."""
        val = 0
        if double_width:
            val |= 0x20
        if double_height:
            val |= 0x01
        self.buffer.extend(self.GS + b'!' + bytes([val]))
        return self

    def invert(self, enable: bool = True) -> 'ESCPOSCommandBuilder':
        """Modo inverso blanco sobre negro (GS B n)."""
        self.buffer.extend(self.GS + (b'B\x01' if enable else b'B\x00'))
        return self

    def text(self, string: str) -> 'ESCPOSCommandBuilder':
        """Agrega texto codificado sin salto de línea."""
        try:
            encoded = string.encode(self.encoding, errors='replace')
        except Exception:
            encoded = string.encode('ascii', errors='replace')
        self.buffer.extend(encoded)
        return self

    def text_line(self, string: str = "") -> 'ESCPOSCommandBuilder':
        """Agrega una línea de texto seguida de avance de línea (LF)."""
        self.text(string)
        self.buffer.extend(b'\n')
        return self

    def separator(self, char: str = "-", custom_width: Optional[int] = None) -> 'ESCPOSCommandBuilder':
        """Agrega una línea separadora del ancho del papel."""
        w = custom_width or self.width
        line_str = (char * w)[:w]
        return self.text_line(line_str)

    def two_columns(self, left: str, right: str, custom_width: Optional[int] = None) -> 'ESCPOSCommandBuilder':
        """Formatea dos columnas ajustadas a los extremos (ej: Total Gs. ....... 150.000)."""
        w = custom_width or self.width
        space_len = w - len(left) - len(right)
        if space_len < 1:
            # Si se excede, truncar o enviar en dos líneas
            left = left[:w - len(right) - 1]
            space_len = 1
        line_str = f"{left}{' ' * space_len}{right}"
        return self.text_line(line_str)

    def three_columns(self, col1: str, col2: str, col3: str, w1: int = 18, w2: int = 10, w3: int = 12) -> 'ESCPOSCommandBuilder':
        """Formatea tres columnas con anchos específicos."""
        c1 = f"{col1:<{w1}}"[:w1]
        c2 = f"{col2:>{w2}}"[:w2]
        c3 = f"{col3:>{w3}}"[:w3]
        return self.text_line(f"{c1} {c2} {c3}")

    def qr_code(self, data: str, size: int = 4) -> 'ESCPOSCommandBuilder':
        """
        Genera comandos ESC/POS nativos para imprimir código QR estándar Modelo 2 (GS ( k).
        """
        data_bytes = data.encode('utf-8')
        length = len(data_bytes) + 3
        pL = length & 0xFF
        pH = (length >> 8) & 0xFF

        # 1. Seleccionar modelo QR (Modelo 2)
        self.buffer.extend(self.GS + b'(k\x04\x00\x31\x41\x32\x00')
        
        # 2. Ajustar tamaño de módulo (1 a 16)
        size_clamped = max(1, min(16, size))
        self.buffer.extend(self.GS + b'(k\x03\x00\x31\x43' + bytes([size_clamped]))
        
        # 3. Nivel de corrección de error (Nivel M = 49)
        self.buffer.extend(self.GS + b'(k\x03\x00\x31\x45\x31')
        
        # 4. Almacenar datos en el buffer de la impresora
        header = self.GS + b'(k' + bytes([pL, pH]) + b'\x31\x50\x30'
        self.buffer.extend(header + data_bytes)
        
        # 5. Imprimir el código QR
        self.buffer.extend(self.GS + b'(k\x03\x00\x31\x51\x30')
        return self

    def open_cash_drawer(self, pin: int = 0) -> 'ESCPOSCommandBuilder':
        """
        Genera pulso eléctrico para abrir el cajón de dinero conectado a la impresora (ESC p m t1 t2).
        pin: 0 para pin 2 (predeterminado), 1 para pin 5.
        """
        m = 0 if pin == 0 else 1
        self.buffer.extend(self.ESC + b'p' + bytes([m, 25, 250]))
        return self

    def feed(self, lines: int = 3) -> 'ESCPOSCommandBuilder':
        """Avanza n líneas de papel (ESC d n)."""
        lines_clamped = max(1, min(255, lines))
        self.buffer.extend(self.ESC + b'd' + bytes([lines_clamped]))
        return self

    def cut_paper(self, partial: bool = True) -> 'ESCPOSCommandBuilder':
        """Corta el papel térmica (GS V)."""
        if partial:
            self.buffer.extend(self.GS + b'V\x42\x00')
        else:
            self.buffer.extend(self.GS + b'V\x00')
        return self

    def get_bytes(self) -> bytes:
        """Retorna los bytes acumulados listos para transmisión."""
        return bytes(self.buffer)


class ESCPOSPrinterDriver:
    """
    Controlador de comunicación física con impresoras térmicas.
    Canales soportados: NETWORK (TCP/IP), WINRAW (USB Spooler Windows), SERIAL (COM), SIMULATOR.
    """
    CONN_NETWORK = "NETWORK"
    CONN_WINRAW = "WINRAW"
    CONN_SERIAL = "SERIAL"
    CONN_SIMULATOR = "SIMULATOR"

    def __init__(
        self,
        connection_type: str = CONN_SIMULATOR,
        ip: str = "192.168.1.200",
        port: int = 9100,
        printer_name: str = "",
        serial_port: str = "COM1",
        baudrate: int = 9600,
        timeout: float = 2.5
    ):
        self.connection_type = connection_type.upper()
        self.ip = ip
        self.port = port
        self.printer_name = printer_name
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = timeout
        
        # Buffer en memoria para testing y modo simulador
        self.simulated_output = bytearray()

    @staticmethod
    def get_available_windows_printers() -> List[str]:
        """Obtiene la lista de nombres de impresoras instaladas en el sistema Windows."""
        printers = []
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Print\Printers")
                i = 0
                while True:
                    try:
                        printers.append(winreg.EnumKey(key, i))
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception as e:
                logger.warning(f"No se pudieron enumerar impresoras por registro: {e}")
        return printers

    def send_raw(self, data: bytes) -> Tuple[bool, str]:
        """
        Envía un flujo de bytes crudos a la impresora según el canal configurado.
        Retorna (True, "OK") en caso de éxito, o (False, "Mensaje de error") si falló.
        """
        if not data:
            return True, "No hay datos para imprimir."

        if self.connection_type == self.CONN_SIMULATOR:
            self.simulated_output.extend(data)
            logger.info(f"Modo SIMULADOR: {len(data)} bytes almacenados en buffer.")
            return True, f"Simulador: {len(data)} bytes procesados correctamente."

        elif self.connection_type == self.CONN_NETWORK:
            return self._send_network(data)

        elif self.connection_type == self.CONN_WINRAW:
            return self._send_winraw(data)

        elif self.connection_type == self.CONN_SERIAL:
            return self._send_serial(data)

        else:
            return False, f"Tipo de conexión desconocido: '{self.connection_type}'"

    def _send_network(self, data: bytes) -> Tuple[bool, str]:
        """Envía datos por Socket TCP a impresora de red."""
        s = None
        try:
            logger.info(f"Conectando a impresora de red {self.ip}:{self.port} (timeout={self.timeout}s)...")
            s = socket.create_connection((self.ip, self.port), timeout=self.timeout)
            s.sendall(data)
            logger.info("Datos transmitidos con éxito a la impresora de red.")
            return True, f"Impresión enviada exitosamente a {self.ip}:{self.port}"
        except socket.timeout:
            err_msg = f"Tiempo de espera agotado al conectar con {self.ip}:{self.port}."
            logger.error(err_msg)
            return False, err_msg
        except ConnectionRefusedError:
            err_msg = f"Conexión rechazada por la impresora en {self.ip}:{self.port}."
            logger.error(err_msg)
            return False, err_msg
        except Exception as e:
            err_msg = f"Error de comunicación de red: {str(e)}"
            logger.error(err_msg)
            return False, err_msg
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass

    def _send_winraw(self, data: bytes) -> Tuple[bool, str]:
        """Envía datos crudos (RAW) a través del Spooler de Windows usando winspool.drv y ctypes."""
        if sys.platform != "win32":
            return False, "Modo WINRAW solo está disponible en sistemas Windows."

        if not self.printer_name:
            return False, "Nombre de impresora no especificado para modo WINRAW."

        import ctypes
        from ctypes import wintypes

        class DOC_INFO_1W(ctypes.Structure):
            _fields_ = [
                ("pDocName", wintypes.LPWSTR),
                ("pOutputFile", wintypes.LPWSTR),
                ("pDatatype", wintypes.LPWSTR)
            ]

        winspool = ctypes.windll.winspool.drv
        OpenPrinterW = winspool.OpenPrinterW
        StartDocPrinterW = winspool.StartDocPrinterW
        StartPagePrinter = winspool.StartPagePrinter
        WritePrinter = winspool.WritePrinter
        EndPagePrinter = winspool.EndPagePrinter
        EndDocPrinter = winspool.EndDocPrinter
        ClosePrinter = winspool.ClosePrinter

        hPrinter = wintypes.HANDLE()
        if not OpenPrinterW(self.printer_name, ctypes.byref(hPrinter), None):
            err_code = ctypes.GetLastError()
            return False, f"No se pudo abrir la impresora '{self.printer_name}' (Código error Win32: {err_code})."

        try:
            doc_info = DOC_INFO_1W(
                pDocName="Ticket POS ESCPOS",
                pOutputFile=None,
                pDatatype="RAW"
            )
            job_id = StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info))
            if job_id == 0:
                err_code = ctypes.GetLastError()
                return False, f"Fallo al iniciar trabajo de impresión en '{self.printer_name}' (Error: {err_code})."

            try:
                if not StartPagePrinter(hPrinter):
                    err_code = ctypes.GetLastError()
                    return False, f"Fallo al iniciar página en '{self.printer_name}' (Error: {err_code})."

                bytes_written = wintypes.DWORD()
                if not WritePrinter(hPrinter, data, len(data), ctypes.byref(bytes_written)):
                    err_code = ctypes.GetLastError()
                    return False, f"Error escribiendo bytes en '{self.printer_name}' (Error: {err_code})."

                EndPagePrinter(hPrinter)
            finally:
                EndDocPrinter(hPrinter)

            logger.info(f"Impresión enviada correctamente a '{self.printer_name}' ({len(data)} bytes).")
            return True, f"Ticket enviado exitosamente a '{self.printer_name}'."
        except Exception as e:
            logger.error(f"Error inesperado en impresión WinSpool RAW: {e}")
            return False, f"Error inesperado WinSpool: {str(e)}"
        finally:
            ClosePrinter(hPrinter)

    def _send_serial(self, data: bytes) -> Tuple[bool, str]:
        """Envía datos directamente a un puerto COM (RS-232 / USB-Serial)."""
        port_path = f"\\\\.\\{self.serial_port.upper()}" if sys.platform == "win32" else self.serial_port
        try:
            # Apertura de archivo de dispositivo directo en modo binario
            with open(port_path, 'wb', buffering=0) as com:
                com.write(data)
            logger.info(f"Datos transmitidos a puerto serial {self.serial_port}.")
            return True, f"Impresión enviada al puerto serial {self.serial_port}."
        except FileNotFoundError:
            return False, f"El puerto serial '{self.serial_port}' no fue encontrado."
        except PermissionError:
            return False, f"El puerto serial '{self.serial_port}' está en uso o no tiene permisos."
        except Exception as e:
            return False, f"Error en puerto serial: {str(e)}"

    def open_drawer(self, pin: int = 0) -> Tuple[bool, str]:
        """Envía el comando de apertura de gaveta de dinero."""
        builder = ESCPOSCommandBuilder()
        builder.open_cash_drawer(pin=pin)
        return self.send_raw(builder.get_bytes())


class ESCPOSPrintWorker(QThread):
    """
    Worker asíncrono para ejecutar impresiones físicas y pulsos de gaveta
    en segundo plano sin congelar la UI de PyQt6.
    """
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, driver: ESCPOSPrinterDriver, raw_data: bytes, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.raw_data = raw_data

    def run(self):
        try:
            success, msg = self.driver.send_raw(self.raw_data)
            self.finished_signal.emit(success, msg)
        except Exception as e:
            self.finished_signal.emit(False, f"Excepción en hilo de impresión: {str(e)}")
