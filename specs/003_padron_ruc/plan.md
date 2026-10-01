# PLAN-003: ARQUITECTURA TÉCNICA DEL MOTOR DE PADRÓN DNIT Y CLIENTES

**Especificación Asociada:** [SPEC-003](file:///c:/ENTORNO%20LOCAL/Control/specs/003_padron_ruc/spec.md)  
**Estado:** Implementado

---

## 1. ARQUITECTURA DE CONSULTA E ÍNDICES

```
┌─────────────────────────────────────────────────────────┐
│              Cajero Digita RUC / C.I. / Nombre          │
│          [PaymentDialog]  ó  [ClientSearchDialog]       │
└────────────────────────────┬────────────────────────────┘
                             │ Debounce (150ms)
┌────────────────────────────▼────────────────────────────┐
│                    Motor de Búsqueda RUC                │
│  - Limpieza de texto: normalización y `strip_accents`   │
│  - Algoritmo DV Módulo 11 (ruc_validator skill)         │
└────────────────────────────┬────────────────────────────┘
                             │ Query Optimizada con Índices
┌────────────────────────────▼────────────────────────────┐
│             SQLite DB (`stock_control.db`)              │
│  - `clients`: Índice en `cli_ruc`, `cli_nombre`         │
│  - `padron_ruc`: Índice B-Tree en `ruc` y `razon_social`│
└─────────────────────────────────────────────────────────┘
```

---

## 2. OPTIMIZACIONES DE BASE DE DATOS

1. **Índices Compuestos y B-Tree**:
   - `CREATE INDEX IF NOT EXISTS idx_padron_ruc_base ON padron_ruc(ruc);`
   - `CREATE INDEX IF NOT EXISTS idx_padron_razon ON padron_ruc(razon_social);`
   - `CREATE INDEX IF NOT EXISTS idx_client_ruc ON clients(cli_ruc);`
   - `CREATE INDEX IF NOT EXISTS idx_client_nombre ON clients(cli_nombre);`

2. **Carga en Transacción Masiva**:
   - `PRAGMA synchronous = OFF;` y `PRAGMA journal_mode = MEMORY;` durante la carga masiva inicial de padrones de la DNIT para alcanzar > 20.000 reg/seg.

---

## 3. INTEGRACIÓN CON SKILL `ruc_validator`

- El módulo central `.agents/skills/ruc_validator/ruc_validator.py` contiene las funciones puras:
  * `calcular_dv_ruc(ruc_base)`
  * `validar_ruc(ruc_completo)`
  * `formatear_ruc(texto)`
  * `obtener_contribuyente(db, ruc_o_ci, auto_cache)`
