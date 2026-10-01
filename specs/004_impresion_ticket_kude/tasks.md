# TASKS-004: CHECKLIST DE TAREAS - TICKETS FISCALES KUDE

**Especificación:** [SPEC-004](file:///c:/ENTORNO%20LOCAL/Control/specs/004_impresion_ticket_kude/spec.md) | **Plan:** [PLAN-004](file:///c:/ENTORNO%20LOCAL/Control/specs/004_impresion_ticket_kude/plan.md)  
**Estado:** 100% Completado y Verificado

---

## Tareas de Implementación

- [x] **T-004.1**: Asegurar que `ui/ticket_dialog.py` incluya el desglose de vouchers de terminales POS (`auth_code`, `voucher_nro`, `card_brand`) en los medios de pago.
- [x] **T-004.2**: Añadir inyección de `sys.path` y bloque ejecutable `if __name__ == '__main__':` en `ui/ticket_dialog.py` para pruebas visuales directas.
- [x] **T-004.3**: Garantizar que el cálculo del CDC de 44 dígitos y la URL del Código QR e-Kuatia respeten estrictamente la fórmula Módulo 11 de la DNIT y encajen en 40 columnas.
- [x] **T-004.4**: Crear suite de pruebas automatizadas `tests/test_ticket_kude_printer.py` validando ancho de 40 columnas, CDC de 44 dígitos, liquidación de IVA y vouchers POS.
