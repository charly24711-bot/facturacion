# TASKS-003: CHECKLIST DE TAREAS - PADRÓN DNIT Y BÚSQUEDA DE CLIENTES

**Especificación:** [SPEC-003](file:///c:/ENTORNO%20LOCAL/Control/specs/003_padron_ruc/spec.md) | **Plan:** [PLAN-003](file:///c:/ENTORNO%20LOCAL/Control/specs/003_padron_ruc/plan.md)  
**Estado:** 100% Completado y Verificado

---

## Tareas de Implementación

- [x] **T-003.1**: Crear índices B-Tree de alto rendimiento en SQLite para `padron_ruc(ruc, razon_social)` y `clients(cli_ruc, cli_nombre)`.
- [x] **T-003.2**: Optimizar la consulta en `ui/client_search_dialog.py` combinando resultados de clientes frecuentes y padrón sin duplicación ni latencia perceptible.
- [x] **T-003.3**: Garantizar que el alta automática de clientes a partir del padrón asigne el código correlativo de 6 dígitos y RUC normalizado.
- [x] **T-003.4**: Crear pruebas de rendimiento y validación de RUC en `tests/test_padron_ruc_performance.py` verificando tiempos de respuesta < 10ms y cálculo de DV Módulo 11.
