# PLAN-006: Plan de Implementación - Sincronización Offline-First

## Fase 1: Módulo Central de Sincronización (`utils/sync_engine.py`)
1. **Serializador/Deserializador JSON Seguro para Decimales**:
   - Implementar `DecimalEncoder` y `parse_decimal_dict` para evitar cualquier conversión a float.
2. **Abstracción de Transporte (`SyncTransport`)**:
   - Clase base abstracta con métodos `push_batch(outbox_entries)` y `pull_catalog(last_sync_timestamp)`.
   - `MockSyncTransport`: Implementación completa en memoria para testing con capacidad de simular latencia, errores HTTP 500, timeouts y respuestas válidas.
   - `HttpSyncTransport`: Implementación basada en `urllib` / `requests` con autenticación por Bearer Token / API Key de sucursal y caja.
3. **Gestor de Outbox (`OutboxManager`)**:
   - Métodos helper para encolar entidades `SyncableModel` dentro de la misma sesión/transacción de SQLAlchemy.
   - Recolección de registros no sincronizados en lotes de N elementos.
   - Marcado de ACK (confirmación de recepción) atómico.

## Fase 2: Worker Asíncrono de Segundo Plano (`SyncWorker`)
1. **Heredero de `QThread`**:
   - Bucle de sincronización con temporizador configurable (ej. cada 15 segundos).
   - Backoff exponencial con jitter: si falla la conexión, los reintentos escalan (1s -> 2s -> 4s -> 8s -> ... -> 60s).
   - Emisión de señales PyQt6 (`status_changed`, `sync_progress`, `sync_completed`, `sync_error`).
2. **Manejo de Errores y Reconexión Suave**:
   - Captura de excepciones sin crashear el worker ni la UI.
   - Detección de recuperación de conectividad.

## Fase 3: Integración en Transacciones de Venta y Modelos
1. **Verificación de `models.py`**:
   - Asegurar que `SyncOutbox` cuente con campos de control: `retry_count`, `last_error`, `status`.
   - Crear listeners o helpers en el guardrail de ventas para encolar en `SyncOutbox` al registrar ventas, cobros y movimientos de caja.

## Fase 4: Indicador de Sincronización en la UI de Caja
1. **`SyncStatusWidget`**:
   - Componente visual para la barra de estado de [`ui/main_window.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/main_window.py).
   - Muestra icono de estado, contador de pendientes y tooltip informativo.
   - Botón de sincronización manual interactivo.

## Fase 5: Suite de Pruebas Automatizadas
1. **`tests/test_sync_engine.py`**:
   - Test de serialización/deserialización de montos con `decimal.Decimal`.
   - Test de encolado atómico en `sync_outbox`.
   - Test de push batch con confirmación ACK en `MockSyncTransport`.
   - Test de reintentos exponenciales y resiliencia ante cortes simulados de red.
   - Test de pull de catálogo y actualización de productos locales.
