# MEMORY.md - MEMORIA OPERATIVA DEL PROYECTO POS

**Proyecto:** POS Supermercado Triple Frontera (Paraguay - Brasil - Argentina)  
**Última Actualización:** Septiembre 2026  
**Metodología:** Spec-Driven Development (SDD)

---

## 1. ESTADO DEL SISTEMA Y ARQUITECTURA

### 1.1 Stack y Tecnologías Base
- **Frontend / UI**: Python 3.12+ con PyQt6 bajo arquitectura MVC (`QTableView` con `QAbstractTableModel` en grilla de ventas).
- **Persistencia**: SQLite local (`stock_control.db`) con SQLAlchemy (ORM/Core) en modo WAL con `foreign_keys=ON`.
- **Aritmética Financiera**: 100% `decimal.Decimal` con cuantización estricta (`PYG`: `Decimal('1')`, `USD/BRL/ARS`: `Decimal('0.01')`, balanza: hasta `Decimal('0.001')`). Cero `float`.
- **Reglas Fiscales**: DNIT Paraguay (Ley 6380/19), liquidación de IVA en tiempo real (10%: `total/11`, 5%: `total/21`, Exentas: 0%), KuDE con CDC de 44 dígitos y exportador Hechauka (RG90).
- **Integración Balanzas**: Soporte para prefijos EAN-13 `20` y `21` (formato `PP CCCCC PPPP D`).

---

## 2. HITOS Y FASES COMPLETADAS

| Fase | Alcance Principal | Estado | Módulos Clave |
| :--- | :--- | :---: | :--- |
| **Fase 1: Núcleo POS & Ergonomía** | Ventas, atajos F1-F12, selector canales de precios, cancelación F9, sangrías/movimientos, arqueo ciego. | ✅ Completada | `main_window.py`, `payment_dialog.py`, `caja_movimiento_dialog.py`, `arqueo_dialog.py` |
| **Fase 2: Back-Office & Fiscal** | Gestión de usuarios RBAC con SHA-256, mermas/ajustes de stock, exportador Hechauka RG90. | ✅ Completada | `admin_window.py`, `users_management_dialog.py`, `stock_adjustment_dialog.py`, `hechauka_export_dialog.py` |
| **Fase 3: Góndola, Balanza & Seguridad** | Códigos de barras vectoriales EAN-13/Code-128, rotulado de góndolas A4/térmico, bloqueo de terminal F12 con PIN. | ✅ Completada | `barcode_renderer.py`, `shelf_labels_dialog.py`, `lock_screen_dialog.py` |
| **Fase 4: Multi-Moneda & Tesorería** | Cotizaciones históricas inmutables, pagos mixtos (PYG, USD, BRL, ARS, PIX, Tarjetas), cierre X y Z. | ✅ Completada | `cotizacion_dialog.py`, `caja_dialog.py`, `models.CashAudit` |
| **Fase 5: Validación & Stress 360°** | Stress de 1000 ventas concurrentes, 50 compras masivas FIFO, 25 devoluciones atómicas, guardrail POS. | ✅ Completada | `validator.py`, `test_stress_integral_360.py` |
| **Fase 6: Integración POS / Pinpad (SPEC-002)** | Driver/simulador POS, worker asíncrono QThread, vouchers (auth_code), deducción de saldo y tests. | ✅ Completada | `utils/pos_driver.py`, `payment_dialog.py`, `models.Payment` |
| **Fase 7: Padrón DNIT & Búsqueda RUC (SPEC-003)** | Índices B-Tree, Módulo 11 (< 10ms), búsqueda unaccent, alta automática de clientes y tests. | ✅ Completada | `client_search_dialog.py`, `ruc_validator.py`, `TaxpayerRegistry` |
| **Fase 8: Tickets Térmicos KuDE (SPEC-004)** | Formato 40 col 80mm, CDC 44 dígitos Módulo 11, QR e-Kuatia, vouchers POS y tests. | ✅ Completada | `ui/ticket_dialog.py`, `tax_calculator`, `qrcode` |
| **Fase 9: Impresión Física ESC/POS (SPEC-005)** | Driver binario directo (Red TCP/IP 9100, WinSpool RAW USB, Serial, Simulador), pulsos de gaveta y QThread. | ✅ Completada | `utils/escpos_driver.py`, `ui/ticket_dialog.py`, `models.CompanySettings` |
| **Fase 10: Sincronización Offline-First (SPEC-006)** | Motor Outbox, serializador JSON Decimal estricto, SyncWorker QThread con Backoff Exponencial y widget UI. | ✅ Completada | `utils/sync_engine.py`, `ui/sync_status_widget.py`, `models.SyncOutbox` |
| **Fase 11: Catálogo Táctil & Balanza RS232 (SPEC-007)** | Driver serial balanzas, Numpad táctil con presets, catálogo modal fullscreen y atajo F6. | ✅ Completada | `utils/scale_driver.py`, `ui/touch_catalog_dialog.py`, `ui/touch_numpad_dialog.py` |
| **Fase 12: Back-Office Fiscal & SIFEN v150 (SPEC-008)** | Liquidación IVA (10%, 5%, Exentas), monitor KuDE, lote JSON SIFEN, libro CSV y reportes ApexCharts. | ✅ Completada | `utils/fiscal_engine.py`, `ui/backoffice_fiscal_dialog.py` |

---

## 3. ÍNDICE DE ESPECIFICACIONES SDD (`specs/`)

- [`specs/001_pos_core/`](file:///c:/ENTORNO%20LOCAL/Control/specs/001_pos_core): Núcleo de ventas, balanzas, liquidación impositiva y guardrail transaccional.
- [`specs/002_integracion_pos_tarjetas/`](file:///c:/ENTORNO%20LOCAL/Control/specs/002_integracion_pos_tarjetas): Integración de terminales electrónicas de cobro (POS/Pinpad), vouchers y deducción automática de saldo.
- [`specs/003_padron_ruc/`](file:///c:/ENTORNO%20LOCAL/Control/specs/003_padron_ruc): Padrón DNIT offline, indexación B-Tree y motor de búsqueda instantánea de clientes.
- [`specs/004_impresion_ticket_kude/`](file:///c:/ENTORNO%20LOCAL/Control/specs/004_impresion_ticket_kude): Emisión y formato de tickets térmicos fiscales (KuDE / SIFEN 80mm).
- [`specs/005_impresion_escpos/`](file:///c:/ENTORNO%20LOCAL/Control/specs/005_impresion_escpos): Emisión física instantánea mediante comandos binarios ESC/POS y apertura de gaveta.
- [`specs/006_sincronizacion_offline/`](file:///c:/ENTORNO%20LOCAL/Control/specs/006_sincronizacion_offline): Sincronización offline-first con patrón Outbox, transporte HTTP/Mock y reintentos exponenciales.
- [`specs/007_catalogo_tactil/`](file:///c:/ENTORNO%20LOCAL/Control/specs/007_catalogo_tactil): Catálogo táctil de góndola, pesaje en vivo RS232 y numpad táctil modal.
- [`specs/008_backoffice_fiscal/`](file:///c:/ENTORNO%20LOCAL/Control/specs/008_backoffice_fiscal): Panel de auditoría fiscal, comprobantes KuDE, generador JSON SIFEN v150 y reportes ApexCharts.

---

## 4. PATRONES DE CÓDIGO Y DECISIONES TÉCNICAS

1. **Guardrail de Ventas**: Toda inserción a `ventas` o descuento de inventario debe pasar por `POSGuardrail.validate_sale_item()`.
2. **Descuento de Stock FIFO**: La venta deduce stock de `ProductBatch` priorizando el lote con fecha de expiración más cercana.
3. **Manejo de Monedas Extranjeras**: Las cotizaciones son inmutables. El sistema almacena la tasa de cambio vigente al momento exacto de la transacción para auditorías contables.
4. **Resiliencia Offline**: Los registros transaccionales incluyen campos `uuid`, `synced: bool` y `sync_timestamp` para sincronización eventual no bloqueante.
5. **Hardware Asíncrono**: Todo acceso a impresoras térmicas, balanzas o terminales POS corre en hilos `QThread` independientes.
6. **Patrón Outbox Idempotente**: Las operaciones de venta y cobro persisten eventos en `sync_outbox` que son despachados asíncronamente por `SyncWorker` con desduplicación garantizada por UUID.
7. **Ergonomía Táctil y Balanza**: Los productos pesables en mostrador interactúan con `ScaleDriver` y `TouchQuantityDialog` preservando 3 decimales estrictos (`Decimal('0.001')`).
8. **Auditoría Fiscal y SIFEN**: Los libros de venta y lotes JSON respetan la ecuación de balance fiscal (`Base Imponible + IVA == Total General`) y generan CDCs de 44 dígitos con Módulo 11.

---

## 5. HOJA DE RUTA / PRÓXIMAS MEJORAS
- [ ] Optimización de búsqueda de clientes por RUC utilizando índice FTS5 en SQLite (SPEC-009).
- [ ] Panel de auditoría de sincronización y visor de cola outbox en tiempo real.
