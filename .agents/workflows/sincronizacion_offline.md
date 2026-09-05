# WORKFLOW: RESILIENCIA Y REPLICACIÓN OFFLINE-FIRST

## Objetivo
Permitir que la caja opere de forma 100% autónoma en SQLite local (`stock_control.db`) y sincronice transacciones con el servidor central de forma asíncrona cuando haya conectividad.

## 1. Detección de Estado de Red
1. Un hilo secundario (`QThread`) realiza un ping HTTP liviano (`/api/v1/health`) al servidor central cada 30 segundos.
2. La interfaz POS actualiza su indicador: **Verde (Online)** o **Naranja (Modo Local / Offline)**.

## 2. Cola de Salida (Caja Local -> Central)
1. Al confirmarse una venta o cierre de caja:
   - Se guarda en el SQLite local dentro de una transacción atómica (`BEGIN TRANSACTION`).
   - Se crea un registro en `sync_outbox` con: `entity_name`, `entity_uuid`, `action` (INSERT/UPDATE), `payload_json`, `created_at`, `synced = False`.
2. El servicio de sincronización lee lotes de 20 registros pendientes en `sync_outbox`.
3. Envía el lote por POST al endpoint central.
4. Si el servidor responde `200 OK` con los UUIDs confirmados, el SQLite local marca `synced = True` y registra `synced_at`.

## 3. Cola de Entrada (Central -> Caja Local)
1. La caja consulta cambios en el catálogo maestro enviando su última marca de agua: `GET /api/v1/sync/catalog?since=<timestamp>`.
2. El servidor responde con novedades de:
   - Productos nuevos o dados de baja.
   - Actualización de precios y códigos de barras.
   - Nuevas cotizaciones oficiales del día (`currency_rates`).
3. El SQLite local aplica los cambios dentro de una transacción.
