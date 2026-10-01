# TASKS-006: Tareas de Implementación - Sincronización Offline-First

- [x] **Tarea 1**: Crear [`utils/sync_engine.py`](file:///c:/ENTORNO%20LOCAL/Control/utils/sync_engine.py) con `DecimalJSONEncoder`, `SyncTransport`, `MockSyncTransport`, `HttpSyncTransport`, `OutboxManager` y `SyncWorker (QThread)`.
- [x] **Tarea 2**: Extender [`models.py`](file:///c:/ENTORNO%20LOCAL/Control/models.py) para que `SyncOutbox` incluya `retry_count`, `last_error`, `status` y helper de serialización para entidades `SyncableModel`.
- [x] **Tarea 3**: Crear widget [`ui/sync_status_widget.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/sync_status_widget.py) e integrarlo en la barra de estado de [`ui/main_window.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/main_window.py).
- [x] **Tarea 4**: Crear suite de tests completa [`tests/test_sync_engine.py`](file:///c:/ENTORNO%20LOCAL/Control/tests/test_sync_engine.py) y verificar con `pytest`.
- [x] **Tarea 5**: Actualizar [`MEMORY.md`](file:///c:/ENTORNO%20LOCAL/Control/MEMORY.md) con la Fase 10 completada.

