# TASKS-002: CHECKLIST DE TAREAS - INTEGRACIÓN POS / PINPAD

**Especificación:** [SPEC-002](file:///c:/ENTORNO%20LOCAL/Control/specs/002_integracion_pos_tarjetas/spec.md) | **Plan:** [PLAN-002](file:///c:/ENTORNO%20LOCAL/Control/specs/002_integracion_pos_tarjetas/plan.md)  
**Estado:** 100% Completado y Verificado

---

## Tareas de Implementación

- [x] **T-002.1**: Extender el modelo `models.Pago` para almacenar `auth_code`, `voucher_nro`, `card_brand` y `terminal_id`.
- [x] **T-002.2**: Diseñar la clase base abstracta `POSTerminalDriver` y un emulador/driver de prueba `POSTerminalSimulator` para pruebas sin hardware físico.
- [x] **T-002.3**: Implementar el hilo secundario `POSTerminalWorker(QThread)` en `utils/pos_driver.py` para transacciones no bloqueantes.
- [x] **T-002.4**: Integrar botón "📲 Cobrar con Terminal POS [F7]" y feedback visual reactivo en `ui/payment_dialog.py`.
- [x] **T-002.5**: Automatizar la deducción del saldo restante al recibir la señal de cobro exitoso.
- [x] **T-002.6**: Actualizar el Reporte Z y diálogo de Arqueo (`ui/arqueo_dialog.py`) para consolidar el subtotal de vouchers de tarjetas vs efectivo real.
- [x] **T-002.7**: Crear suite de pruebas automatizadas `tests/test_pos_terminal_integration.py` validando cobros aprobados, rechazados y pagos split.
