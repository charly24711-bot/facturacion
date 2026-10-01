import time
import random
import uuid
from decimal import Decimal
from abc import ABC, abstractmethod
from PyQt6.QtCore import QThread, pyqtSignal

class BasePOSTerminalDriver(ABC):
    """Clase base abstracta para comunicación con terminales POS físicas / Pinpads."""
    
    @abstractmethod
    def process_payment(self, amount: Decimal, currency: str = "PYG") -> dict:
        """Procesa una transacción de cobro."""
        pass

    @abstractmethod
    def cancel_operation(self):
        """Cancela la operación en curso."""
        pass

class POSTerminalSimulator(BasePOSTerminalDriver):
    """
    Simulador determinista de Terminal POS / Pinpad para desarrollo y testing.
    Permite emular respuestas reales de Bancard / Dinelco / Redelcom sin hardware.
    """
    def __init__(self, terminal_id: str = "POS-VIRTUAL-01", force_result: str = "APPROVED"):
        self.terminal_id = terminal_id
        self.force_result = force_result  # 'APPROVED', 'REJECTED', 'TIMEOUT', 'RANDOM'
        self.is_cancelled = False

    def process_payment(self, amount: Decimal, currency: str = "PYG") -> dict:
        if self.is_cancelled:
            return {
                "success": False,
                "error": "Operación cancelada por el cajero o cliente.",
                "status_code": "CANCELLED"
            }
            
        # Simular latencia de red y digitación de PIN del cliente
        for _ in range(3):
            if self.is_cancelled:
                return {
                    "success": False,
                    "error": "Operación cancelada por el cajero o cliente.",
                    "status_code": "CANCELLED"
                }
            time.sleep(0.05)

        if self.force_result == "APPROVED" or (self.force_result == "RANDOM" and random.random() > 0.1):
            auth_code = str(random.randint(100000, 999999))
            voucher_nro = f"T{random.randint(1000, 9999)}"
            brands = ["VISA", "MASTERCARD", "MAESTRO", "CABAL", "PIX-QR"]
            brand = random.choice(brands)
            
            return {
                "success": True,
                "auth_code": auth_code,
                "voucher_nro": voucher_nro,
                "card_brand": brand,
                "terminal_id": self.terminal_id,
                "amount": amount,
                "currency": currency,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        elif self.force_result == "REJECTED":
            return {
                "success": False,
                "error": "Transacción rechazada por el banco emisor (Fondos Insuficientes / PIN Inválido).",
                "status_code": "DECLINED"
            }
        else:
            return {
                "success": False,
                "error": "Tiempo de espera agotado (Timeout de conexión con la terminal).",
                "status_code": "TIMEOUT"
            }

    def cancel_operation(self):
        self.is_cancelled = True

class POSTerminalWorker(QThread):
    """
    Worker asíncrono para ejecutar transacciones con el Pinpad sin bloquear la UI de PyQt6.
    """
    status_changed = pyqtSignal(str)
    payment_approved = pyqtSignal(dict)
    payment_failed = pyqtSignal(str)
    
    def __init__(self, amount: Decimal, currency: str = "PYG", driver: BasePOSTerminalDriver = None, parent=None):
        super().__init__(parent)
        self.amount = amount
        self.currency = currency
        self.driver = driver or POSTerminalSimulator()

    def run(self):
        try:
            self.status_changed.emit("Conectando con terminal POS...")
            time.sleep(0.3)
            self.status_changed.emit("Aguardando tarjeta / escaneo QR del cliente...")
            
            result = self.driver.process_payment(self.amount, self.currency)
            
            if result.get("success"):
                self.status_changed.emit("¡Cobro aprobado por el adquirente!")
                self.payment_approved.emit(result)
            else:
                err_msg = result.get("error", "Error desconocido en terminal.")
                self.status_changed.emit(f"Fallo: {err_msg}")
                self.payment_failed.emit(err_msg)
        except Exception as e:
            self.status_changed.emit(f"Error de comunicación: {str(e)}")
            self.payment_failed.emit(str(e))

    def cancel(self):
        if self.driver:
            self.driver.cancel_operation()
