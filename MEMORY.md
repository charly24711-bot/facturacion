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

---

## 3. ÍNDICE DE ESPECIFICACIONES SDD (`specs/`)

- [`specs/001_pos_core/`](file:///c:/ENTORNO%20LOCAL/Control/specs/001_pos_core): Núcleo de ventas, balanzas, liquidación impositiva y guardrail transaccional.
- [`specs/002_integracion_pos_tarjetas/`](file:///c:/ENTORNO%20LOCAL/Control/specs/002_integracion_pos_tarjetas): Integración de terminales electrónicas de cobro (POS/Pinpad), vouchers y deducción automática de saldo.

---

## 4. PATRONES DE CÓDIGO Y DECISIONES TÉCNICAS

1. **Guardrail de Ventas**: Toda inserción a `ventas` o descuento de inventario debe pasar por `POSGuardrail.validate_sale_item()`.
2. **Descuento de Stock FIFO**: La venta deduce stock de `ProductBatch` priorizando el lote con fecha de expiración más cercana.
3. **Manejo de Monedas Extranjeras**: Las cotizaciones son inmutables. El sistema almacena la tasa de cambio vigente al momento exacto de la transacción para auditorías contables.
4. **Resiliencia Offline**: Los registros transaccionales incluyen campos `uuid`, `synced: bool` y `sync_timestamp` para sincronización eventual no bloqueante.

---

## 5. HOJA DE RUTA / PRÓXIMAS MEJORAS
- [ ] Implementación de impresión directa ESC/POS vía socket/USB en hilo de fondo.
- [ ] Sincronizador de segundo plano `SyncWorker` con cola de reintentos exponenciales.
- [ ] Optimización de búsqueda de clientes por RUC utilizando índice FTS5 en SQLite.
