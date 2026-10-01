"""
utils/sync_engine.py - Motor de Sincronización Offline-First para POS Supermercado

Implementa:
1. Serializador JSON de alta precisión (cero float, manejo estricto de Decimal y Fechas ISO).
2. Abstracción de Transporte (SyncTransport, MockSyncTransport, HttpSyncTransport).
3. Gestor de Outbox Transaccional (OutboxManager).
4. Worker Asíncrono no-bloqueante en segundo plano (SyncWorker con QThread y Backoff Exponencial).
"""

import json
import logging
import time
import random
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition

from models import SyncOutbox, Product, Category, Brand, CurrencyRate, PriceList, ProductBarcode
from database import get_db

logger = logging.getLogger("SyncEngine")
logger.setLevel(logging.INFO)


class DecimalJSONEncoder(json.JSONEncoder):
    """Serializador JSON que preserva la precisión de Decimal y formatea tipos comunes."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
        return super().default(obj)


def sync_dumps(obj: Any) -> str:
    """Serializa un objeto a JSON utilizando DecimalJSONEncoder."""
    return json.dumps(obj, cls=DecimalJSONEncoder, ensure_ascii=False)


def sync_loads(payload_str: str) -> Any:
    """Deserializa un string JSON."""
    return json.loads(payload_str)


# ============================================================================
# ABSTRACCIÓN DE TRANSPORTE
# ============================================================================

class SyncTransport(ABC):
    """Interfaz abstracta para el transporte de sincronización con el servidor central."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica conectividad y disponibilidad del servidor central."""
        pass

    @abstractmethod
    def push_batch(self, outbox_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Envía un lote de eventos outbox al servidor central.
        Retorna:
            {
                "success": bool,
                "synced_uuids": list[str],
                "errors": list[dict],
                "message": str
            }
        """
        pass

    @abstractmethod
    def pull_catalog(self, last_sync_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene actualizaciones del catálogo maestro (productos, precios, cotizaciones).
        Retorna:
            {
                "success": bool,
                "products": list[dict],
                "currency_rates": list[dict],
                "server_timestamp": str
            }
        """
        pass


class MockSyncTransport(SyncTransport):
    """
    Simulador de servidor central en memoria para tests offline,
    pruebas de estrés y simulación de cortes de red.
    """

    def __init__(self, is_online: bool = True, simulated_latency: float = 0.0):
        self.is_online = is_online
        self.simulated_latency = simulated_latency
        self.received_outbox: List[Dict[str, Any]] = []
        self.synced_uuids: set[str] = set()
        self.mock_products: List[Dict[str, Any]] = []
        self.mock_currency_rates: List[Dict[str, Any]] = []
        self.should_fail: bool = False
        self.failure_error_message: str = "Simulated Server Error (500)"

    def health_check(self) -> bool:
        if self.simulated_latency > 0:
            time.sleep(self.simulated_latency)
        return self.is_online and not self.should_fail

    def push_batch(self, outbox_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.simulated_latency > 0:
            time.sleep(self.simulated_latency)

        if not self.is_online:
            raise ConnectionError("No se pudo conectar al servidor central (Mock Offline)")

        if self.should_fail:
            return {
                "success": False,
                "synced_uuids": [],
                "errors": [{"error": self.failure_error_message}],
                "message": self.failure_error_message
            }

        synced = []
        for entry in outbox_entries:
            uuid_val = entry.get("entity_uuid")
            if uuid_val:
                self.received_outbox.append(entry)
                self.synced_uuids.add(uuid_val)
                synced.append(uuid_val)

        return {
            "success": True,
            "synced_uuids": synced,
            "errors": [],
            "message": f"Sincronizados {len(synced)} registros correctamente."
        }

    def pull_catalog(self, last_sync_timestamp: Optional[str] = None) -> Dict[str, Any]:
        if self.simulated_latency > 0:
            time.sleep(self.simulated_latency)

        if not self.is_online or self.should_fail:
            raise ConnectionError("Error al consultar catálogo del servidor")

        now_str = datetime.datetime.utcnow().isoformat()
        return {
            "success": True,
            "products": list(self.mock_products),
            "currency_rates": list(self.mock_currency_rates),
            "server_timestamp": now_str
        }


class HttpSyncTransport(SyncTransport):
    """
    Transporte HTTP/HTTPS REST para comunicación con la API central.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        branch_code: str = "CDE-01",
        terminal_id: str = "POS-01",
        timeout: float = 3.0
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or ""
        self.branch_code = branch_code
        self.terminal_id = terminal_id
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"POS-SyncClient/1.0 ({self.branch_code}-{self.terminal_id})"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def health_check(self) -> bool:
        import urllib.request
        import urllib.error
        try:
            url = f"{self.base_url}/health"
            req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"Health check falló: {e}")
            return False

    def push_batch(self, outbox_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        import urllib.request
        import urllib.error
        url = f"{self.base_url}/api/sync/push"
        payload = {
            "branch_code": self.branch_code,
            "terminal_id": self.terminal_id,
            "sent_at": datetime.datetime.utcnow().isoformat(),
            "batch": outbox_entries
        }
        data_bytes = sync_dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=self._get_headers(), method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                response_data = json.loads(resp.read().decode('utf-8'))
                return response_data
        except Exception as e:
            logger.error(f"Error HTTP push_batch: {e}")
            raise ConnectionError(f"Falla de red al enviar lote: {e}")

    def pull_catalog(self, last_sync_timestamp: Optional[str] = None) -> Dict[str, Any]:
        import urllib.request
        import urllib.error
        url = f"{self.base_url}/api/sync/pull-catalog"
        if last_sync_timestamp:
            url += f"?since={last_sync_timestamp}"

        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Error HTTP pull_catalog: {e}")
            raise ConnectionError(f"Falla de red al solicitar catálogo: {e}")


# ============================================================================
# GESTOR DE OUTBOX TRANSACCIONAL
# ============================================================================

class OutboxManager:
    """Administrador de encolado, despacho y confirmación de eventos de sincronización."""

    @staticmethod
    def enqueue_entity(
        session,
        entity_name: str,
        entity_uuid: str,
        action: str,
        payload_dict: Dict[str, Any]
    ) -> SyncOutbox:
        """
        Encola un evento transaccional en `sync_outbox`.
        Debe ejecutarse dentro de la misma transacción de SQLAlchemy que la operación base.
        """
        payload_str = sync_dumps(payload_dict)
        outbox_entry = SyncOutbox(
            entity_name=entity_name,
            entity_uuid=entity_uuid,
            action=action.upper(),
            payload_json=payload_str,
            created_at=datetime.datetime.utcnow(),
            synced=False,
            status='PENDING',
            retry_count=0
        )
        session.add(outbox_entry)
        return outbox_entry

    @staticmethod
    def get_pending_entries(session, limit: int = 50) -> List[SyncOutbox]:
        """Obtiene hasta `limit` eventos pendientes de sincronización ordenados por creación."""
        return (
            session.query(SyncOutbox)
            .filter(SyncOutbox.synced == False)
            .order_by(SyncOutbox.id.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_pending_count(session) -> int:
        """Retorna la cantidad total de eventos pendientes en el outbox."""
        return session.query(SyncOutbox).filter(SyncOutbox.synced == False).count()

    @staticmethod
    def mark_synced(session, entity_uuids: List[str]) -> int:
        """Marca como sincronizados los registros cuyos UUIDs fueron confirmados por el servidor."""
        if not entity_uuids:
            return 0
        now = datetime.datetime.utcnow()
        count = (
            session.query(SyncOutbox)
            .filter(SyncOutbox.entity_uuid.in_(entity_uuids))
            .update(
                {
                    SyncOutbox.synced: True,
                    SyncOutbox.status: 'SYNCED',
                    SyncOutbox.synced_at: now
                },
                synchronize_session=False
            )
        )
        session.commit()
        return count

    @staticmethod
    def mark_failed(session, entity_uuids: List[str], error_message: str) -> None:
        """Incrementa el contador de reintentos y almacena el error para diagnóstico."""
        if not entity_uuids:
            return
        entries = session.query(SyncOutbox).filter(SyncOutbox.entity_uuid.in_(entity_uuids)).all()
        for entry in entries:
            entry.retry_count = (entry.retry_count or 0) + 1
            entry.last_error = error_message[:250]
            entry.status = 'FAILED'
        session.commit()

    @staticmethod
    def apply_catalog_pull(session, catalog_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Aplica los cambios del catálogo recibidos del servidor central en la base local.
        """
        products_updated = 0
        rates_inserted = 0

        # 1. Actualizar/Insertar Productos
        for p_data in catalog_data.get("products", []):
            codigo = p_data.get("art_codigo")
            if not codigo:
                continue

            product = session.query(Product).filter(Product.art_codigo == codigo).first()
            if not product:
                product = Product(art_codigo=codigo)
                session.add(product)

            if "art_descri" in p_data:
                product.art_descri = p_data["art_descri"]
            if "art_cbarra" in p_data:
                product.art_cbarra = p_data["art_cbarra"]
            if "art_preven" in p_data:
                product.art_preven = Decimal(str(p_data["art_preven"]))
            if "art_costo" in p_data:
                product.art_costo = Decimal(str(p_data["art_costo"]))
            if "art_impu" in p_data:
                product.art_impu = Decimal(str(p_data["art_impu"]))
            if "is_active" in p_data:
                product.is_active = bool(p_data["is_active"])

            products_updated += 1

        # 2. Insertar Cotizaciones Nuevas (Inmutables)
        for r_data in catalog_data.get("currency_rates", []):
            code = r_data.get("currency_code")
            buy = r_data.get("buy_rate")
            sell = r_data.get("sell_rate")
            if code and buy is not None and sell is not None:
                # Desactivar tasa anterior
                session.query(CurrencyRate).filter(
                    CurrencyRate.currency_code == code,
                    CurrencyRate.is_active == True
                ).update({"is_active": False})

                new_rate = CurrencyRate(
                    currency_code=code,
                    buy_rate=Decimal(str(buy)),
                    sell_rate=Decimal(str(sell)),
                    created_at=datetime.datetime.utcnow(),
                    is_active=True
                )
                session.add(new_rate)
                rates_inserted += 1

        session.commit()
        return {
            "products_updated": products_updated,
            "rates_inserted": rates_inserted
        }


# ============================================================================
# WORKER ASÍNCRONO DE SEGUNDO PLANO (QThread)
# ============================================================================

class SyncWorker(QThread):
    """
    Worker asíncrono para PyQt6 que ejecuta la sincronización periódica
    con algoritmo de Backoff Exponencial y detección de conectividad.
    """

    # Señales PyQt6
    status_changed = pyqtSignal(str, int)  # status ('ONLINE', 'SYNCING', 'OFFLINE', 'ERROR'), pending_count
    sync_started = pyqtSignal()
    sync_progress = pyqtSignal(int, int)  # synced_items, total_items
    sync_completed = pyqtSignal(int, int)  # pushed_count, pulled_count
    sync_failed = pyqtSignal(str)  # error_message

    def __init__(
        self,
        transport: SyncTransport,
        sync_interval_seconds: int = 15,
        parent=None
    ):
        super().__init__(parent)
        self.transport = transport
        self.sync_interval_seconds = sync_interval_seconds
        self._is_running = True
        self._mutex = QMutex()
        self._wait_cond = QWaitCondition()
        self._manual_trigger = False

        # Backoff Exponencial
        self.base_backoff = 2.0
        self.max_backoff = 60.0
        self.current_backoff = self.base_backoff
        self.consecutive_failures = 0

        self.last_catalog_sync_timestamp: Optional[str] = None

    def trigger_sync_now(self):
        """Dispara una sincronización inmediata bajo demanda."""
        self._mutex.lock()
        self._manual_trigger = True
        self._wait_cond.wakeAll()
        self._mutex.unlock()

    def stop(self):
        """Detiene el hilo de manera limpia."""
        self._mutex.lock()
        self._is_running = False
        self._wait_cond.wakeAll()
        self._mutex.unlock()
        self.wait(2000)

    def run(self):
        logger.info("SyncWorker iniciado en segundo plano.")
        while self._is_running:
            try:
                self._execute_sync_cycle()
            except Exception as e:
                logger.error(f"Error inesperado en ciclo de sincronización: {e}", exc_info=True)
                self.sync_failed.emit(str(e))

            # Espera periódica o interrupción por trigger manual
            self._mutex.lock()
            if self._is_running:
                # Si falló, aplicamos backoff; si no, el intervalo regular
                sleep_time = (
                    self.current_backoff
                    if self.consecutive_failures > 0
                    else self.sync_interval_seconds
                )
                # Agregar jitter (+- 10%)
                jitter = random.uniform(0.9, 1.1)
                effective_ms = int(sleep_time * jitter * 1000)

                self._manual_trigger = False
                self._wait_cond.wait(self._mutex, effective_ms)
            self._mutex.unlock()

        logger.info("SyncWorker finalizado.")

    def _execute_sync_cycle(self, db_session=None):
        """Ejecuta una ronda de Push de Outbox y Pull de Catálogo."""
        owns_db = False
        if db_session is None:
            db = get_db()
            owns_db = True
        else:
            db = db_session

        try:
            pending_count = OutboxManager.get_pending_count(db)

            # 1. Health Check
            is_healthy = self.transport.health_check()
            if not is_healthy:
                self.consecutive_failures += 1
                self._apply_backoff()
                self.status_changed.emit('OFFLINE', pending_count)
                return

            # Estado Online
            self.status_changed.emit('SYNCING' if pending_count > 0 else 'ONLINE', pending_count)
            self.sync_started.emit()

            pushed_total = 0
            pulled_total = 0

            # 2. Push Batch si hay pendientes
            if pending_count > 0:
                pending_entries = OutboxManager.get_pending_entries(db, limit=50)
                batch_payload = [
                    {
                        "id": entry.id,
                        "entity_name": entry.entity_name,
                        "entity_uuid": entry.entity_uuid,
                        "action": entry.action,
                        "payload": sync_loads(entry.payload_json),
                        "created_at": entry.created_at.isoformat() if entry.created_at else None
                    }
                    for entry in pending_entries
                ]

                batch_uuids = [e.entity_uuid for e in pending_entries]

                try:
                    response = self.transport.push_batch(batch_payload)
                    if response.get("success"):
                        synced_uuids = response.get("synced_uuids", [])
                        pushed_total = OutboxManager.mark_synced(db, synced_uuids)
                        self.sync_progress.emit(len(synced_uuids), len(pending_entries))
                    else:
                        err_msg = response.get("message", "Error reportado por servidor")
                        OutboxManager.mark_failed(db, batch_uuids, err_msg)
                        self.sync_failed.emit(err_msg)
                except Exception as e:
                    OutboxManager.mark_failed(db, batch_uuids, str(e))
                    raise e

            # 3. Pull Catalog
            try:
                catalog_data = self.transport.pull_catalog(self.last_catalog_sync_timestamp)
                if catalog_data.get("success"):
                    stats = OutboxManager.apply_catalog_pull(db, catalog_data)
                    pulled_total = stats["products_updated"] + stats["rates_inserted"]
                    self.last_catalog_sync_timestamp = catalog_data.get("server_timestamp")
            except Exception as e:
                logger.warning(f"Pull de catálogo falló pero push continuó: {e}")

            # Éxito: Resetear backoff
            self.consecutive_failures = 0
            self.current_backoff = self.base_backoff

            remaining_pending = OutboxManager.get_pending_count(db)
            self.status_changed.emit('ONLINE', remaining_pending)
            self.sync_completed.emit(pushed_total, pulled_total)

        except ConnectionError as ce:
            self.consecutive_failures += 1
            self._apply_backoff()
            remaining = OutboxManager.get_pending_count(db)
            self.status_changed.emit('OFFLINE', remaining)
            self.sync_failed.emit(f"Desconectado: {ce}")
        except Exception as ex:
            self.consecutive_failures += 1
            self._apply_backoff()
            remaining = OutboxManager.get_pending_count(db)
            self.status_changed.emit('ERROR', remaining)
            self.sync_failed.emit(f"Error sincronización: {ex}")
        finally:
            if owns_db and db is not None:
                db.close()

    def _apply_backoff(self):
        """Calcula el próximo tiempo de reintento exponencial."""
        self.current_backoff = min(
            self.base_backoff * (2 ** (self.consecutive_failures - 1)),
            self.max_backoff
        )
        logger.info(f"Reintento de sincronización agendado en {self.current_backoff:.1f}s (Fallas: {self.consecutive_failures})")
