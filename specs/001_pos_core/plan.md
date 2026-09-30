# PLAN-001: ARQUITECTURA TÉCNICA DEL NÚCLEO POS

**Especificación Asociada:** [SPEC-001](file:///c:/ENTORNO%20LOCAL/Control/specs/001_pos_core/spec.md)  
**Estado:** Implementado

---

## 1. ARQUITECTURA DE COMPONENTES

```
┌────────────────────────────────────────────────────────┐
│                   PyQt6 Presentation Layer             │
│  [MainWindow] ──> [VentasTableModel] ──> [PaymentDialog] │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Business & Validation Layer         │
│         [POSGuardrail] (validator.py)                  │
│         [FiscalEngine] (IVA 10/5/0, CDC 44)            │
│         [MultiCurrencyEngine] (PYG/USD/BRL/ARS)        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Persistence Layer (SQLite)          │
│   SQLAlchemy ORM (Session Local WAL)                   │
│   Tablas: ventas, detalles, pagos, clientes, lotes     │
└────────────────────────────────────────────────────────┘
```

---

## 2. MODELO DE DATOS Y FLUJO TRANSACCIONAL

1. **Venta (`models.Venta`)**:
   - `id`, `uuid`, `nro_factura`, `fecha`, `cliente_id`, `total_pyg`, `total_usd`, `total_brl`, `total_ars`, `estado`, `synced`.
2. **Detalle (`models.DetalleVenta`)**:
   - `venta_id`, `articulo_id`, `cantidad` (Decimal), `precio_unitario` (Decimal), `iva_tipo` (10, 5, 0), `subtotal` (Decimal).
3. **Guardrail Pre-Commit**:
   - Invocación de `POSGuardrail.validate_sale_item()` antes de registrar cada ítem o persistir la factura.

---

## 3. GESTIÓN DE RIESGOS Y DECISIONES TÉCNICAS

- **Riesgo de Bloqueo de UI por Balanza**: La decodificación EAN-13 se realiza de forma síncrona en el procesador de buffer de teclado/scanner sin llamadas I/O bloqueantes.
- **Riesgo de Inconsistencia de Redondeo**: Normalización con `quantize(Decimal('1'))` para PYG y `quantize(Decimal('0.01'))` para divisas extranjeras.
