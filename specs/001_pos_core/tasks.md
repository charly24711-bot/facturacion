# TASKS-001: CHECKLIST DE TAREAS - NÚCLEO POS

**Especificación:** [SPEC-001](file:///c:/ENTORNO%20LOCAL/Control/specs/001_pos_core/spec.md) | **Plan:** [PLAN-001](file:///c:/ENTORNO%20LOCAL/Control/specs/001_pos_core/plan.md)  
**Estado:** 100% Completado

---

## Tareas de Implementación

- [x] **T-001.1**: Diseñar e implementar `VentasTableModel` derivado de `QAbstractTableModel` para gestión de carrito en memoria.
- [x] **T-001.2**: Integrar decodificador EAN-13 para balanzas in-store con prefijos 20 y 21.
- [x] **T-001.3**: Implementar cálculo en vivo de IVA 10%, 5% y Exentas en panel fiscal de `MainWindow`.
- [x] **T-001.4**: Crear diálogo de cobros `PaymentDialog` con soporte multi-moneda (PYG, USD, BRL, ARS).
- [x] **T-001.5**: Implementar guardrail de validación en `.agents/skills/validator/validator.py` con comprobaciones numéricas en `Decimal`.
- [x] **T-001.6**: Integrar consulta offline del Padrón DNIT con algoritmo Módulo 11 para cálculo de DV.
- [x] **T-001.7**: Ejecutar pruebas de estrés integral (1000 ventas, compras masivas, notas de crédito) y verificar paso al 100%.
