"""
tests/test_sync_engine.py - Suite de Pruebas Unitarias y de Integración para SyncEngine (SPEC-006)
Valida:
1. Precisión de tipos Decimal en serialización/deserialización JSON.
2. Encolado y ciclo de vida de transacciones en sync_outbox.
3. Push/Pull con MockSyncTransport y confirmación ACK.
4. Resiliencia y Backoff Exponencial ante fallos de conexión.
5. Ingestión de catálogo y cotizaciones inmutables.
"""

import os
import sys
import time
import pytest
import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import models
from utils.sync_engine import (
    DecimalJSONEncoder,
    sync_dumps,
    sync_loads,
    SyncTransport,
    MockSyncTransport,
    OutboxManager,
    SyncWorker
)


@pytest.fixture
def db_session():
    """Crea una base de datos SQLite en memoria para tests aislados."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Sembrar datos básicos
        curr_pyg = models.Currency(code="PYG", name="Guaraní", symbol="₲", decimals=0, is_base=True)
        curr_usd = models.Currency(code="USD", name="Dólar", symbol="$", decimals=2, is_base=False)
        curr_brl = models.Currency(code="BRL", name="Real", symbol="R$", decimals=2, is_base=False)
        session.add_all([curr_pyg, curr_usd, curr_brl])

        prod = models.Product(
            art_codigo="PROD01",
            art_descri="ARROZ SUPREMO 1KG",
            art_cbarra="7840001000018",
            art_preven=Decimal('8500'),
            art_costo=Decimal('6200'),
            art_impu=Decimal('10')
        )
        session.add(prod)
        session.commit()
        yield session
    finally:
        session.close()


class TestSyncEngine:

    def test_01_decimal_json_serialization(self):
        """Verifica que los valores Decimal y Fechas se serialicen y deserialicen sin pérdida de precisión."""
        data = {
            "monto_pyg": Decimal('150000'),
            "monto_usd": Decimal('19.75'),
            "peso_balanza": Decimal('1.455'),
            "fecha": datetime.datetime(2026, 10, 1, 8, 30, 0)
        }

        serialized = sync_dumps(data)
        assert isinstance(serialized, str)
        assert '"150000"' in serialized
        assert '"19.75"' in serialized
        assert '"1.455"' in serialized
        assert '"2026-10-01T08:30:00"' in serialized

        deserialized = sync_loads(serialized)
        assert deserialized["monto_pyg"] == "150000"
        assert Decimal(deserialized["monto_usd"]) == Decimal('19.75')
        assert Decimal(deserialized["peso_balanza"]) == Decimal('1.455')

    def test_02_outbox_enqueue_and_retrieval(self, db_session):
        """Verifica el encolado de eventos en sync_outbox y su recuperación por lotes."""
        # Encolar 3 entidades
        entry1 = OutboxManager.enqueue_entity(
            db_session,
            entity_name="Invoice",
            entity_uuid="uuid-inv-001",
            action="INSERT",
            payload_dict={"total": Decimal('50000'), "nro": 101}
        )
        entry2 = OutboxManager.enqueue_entity(
            db_session,
            entity_name="Payment",
            entity_uuid="uuid-pay-001",
            action="INSERT",
            payload_dict={"monto": Decimal('50000'), "metodo": "Efectivo"}
        )
        db_session.commit()

        assert entry1.id is not None
        assert entry2.id is not None

        # Comprobar pendientes
        count = OutboxManager.get_pending_count(db_session)
        assert count == 2

        pending = OutboxManager.get_pending_entries(db_session, limit=10)
        assert len(pending) == 2
        assert pending[0].entity_uuid == "uuid-inv-001"
        assert pending[1].entity_uuid == "uuid-pay-001"

    def test_03_outbox_mark_synced_and_failed(self, db_session):
        """Verifica la confirmación de sincronización y el registro de fallos en el outbox."""
        entry = OutboxManager.enqueue_entity(
            db_session,
            entity_name="Invoice",
            entity_uuid="uuid-inv-002",
            action="INSERT",
            payload_dict={"total": Decimal('120000')}
        )
        db_session.commit()

        # Simular fallo inicial
        OutboxManager.mark_failed(db_session, ["uuid-inv-002"], "Timeout de conexión (504)")
        db_session.refresh(entry)
        assert entry.retry_count == 1
        assert entry.status == 'FAILED'
        assert "Timeout" in entry.last_error
        assert entry.synced is False

        # Confirmar sincronización posterior
        synced_count = OutboxManager.mark_synced(db_session, ["uuid-inv-002"])
        assert synced_count == 1
        db_session.refresh(entry)
        assert entry.synced is True
        assert entry.status == 'SYNCED'
        assert entry.synced_at is not None

        # Ya no debe estar pendiente
        assert OutboxManager.get_pending_count(db_session) == 0

    def test_04_mock_transport_push_and_pull(self, db_session):
        """Valida la comunicación Push y Pull con MockSyncTransport."""
        transport = MockSyncTransport(is_online=True)
        assert transport.health_check() is True

        batch = [
            {
                "entity_name": "Invoice",
                "entity_uuid": "uuid-batch-001",
                "action": "INSERT",
                "payload": {"ven_total": "75000"}
            }
        ]

        response = transport.push_batch(batch)
        assert response["success"] is True
        assert "uuid-batch-001" in response["synced_uuids"]
        assert len(transport.received_outbox) == 1

        # Test Pull Catálogo
        transport.mock_products = [
            {
                "art_codigo": "PROD02",
                "art_descri": "LECHE ENTERA 1L",
                "art_cbarra": "7840001000025",
                "art_preven": "6500",
                "art_costo": "4500",
                "art_impu": "10",
                "is_active": True
            }
        ]
        transport.mock_currency_rates = [
            {
                "currency_code": "USD",
                "buy_rate": "7700",
                "sell_rate": "7750"
            }
        ]

        pull_res = transport.pull_catalog()
        assert pull_res["success"] is True
        assert len(pull_res["products"]) == 1
        assert len(pull_res["currency_rates"]) == 1

        # Ingestar en base de datos local
        stats = OutboxManager.apply_catalog_pull(db_session, pull_res)
        assert stats["products_updated"] == 1
        assert stats["rates_inserted"] == 1

        prod = db_session.query(models.Product).filter_by(art_codigo="PROD02").first()
        assert prod is not None
        assert prod.art_preven == Decimal('6500')

        rate = db_session.query(models.CurrencyRate).filter_by(currency_code="USD", is_active=True).first()
        assert rate is not None
        assert rate.sell_rate == Decimal('7750')

    def test_05_sync_worker_offline_resilience(self, db_session):
        """Verifica que el SyncWorker no colapse ante servidores caídos y aplique backoff exponencial."""
        transport = MockSyncTransport(is_online=False)
        worker = SyncWorker(transport=transport, sync_interval_seconds=1)

        # Encolar un evento
        OutboxManager.enqueue_entity(
            db_session,
            entity_name="Invoice",
            entity_uuid="uuid-offline-001",
            action="INSERT",
            payload_dict={"total": Decimal('99000')}
        )
        db_session.commit()

        # Ejecutar un ciclo
        worker._execute_sync_cycle(db_session=db_session)

        assert worker.consecutive_failures == 1
        assert worker.current_backoff == 2.0  # 2^0 * 2.0

        # Segundo fallo consecutivo
        worker._execute_sync_cycle(db_session=db_session)
        assert worker.consecutive_failures == 2
        assert worker.current_backoff == 4.0  # 2^1 * 2.0

        # Recuperación de red
        transport.is_online = True
        worker._execute_sync_cycle(db_session=db_session)

        assert worker.consecutive_failures == 0
        assert worker.current_backoff == worker.base_backoff
        assert OutboxManager.get_pending_count(db_session) == 0
