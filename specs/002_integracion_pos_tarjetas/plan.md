# PLAN-002: ARQUITECTURA TÉCNICA DE INTEGRACIÓN POS / PINPAD

**Especificación Asociada:** [SPEC-002](file:///c:/ENTORNO%20LOCAL/Control/specs/002_integracion_pos_tarjetas/spec.md)  
**Estado:** Implementado

---

## 1. ARQUITECTURA DE INTEGRACIÓN

```
┌────────────────────────────────────────────────────────┐
│                   PaymentDialog (PyQt6 UI)             │
│  [Botón: Cobrar con POS] ──> [Modal Esperando Tarjeta] │
└───────────────────────────┬────────────────────────────┘
                            │ Dispara señal / Worker
┌───────────────────────────▼────────────────────────────┐
│               POSTerminalWorker (QThread)              │
│  - Abre conexión (Socket IP / Serial RS232 / REST)     │
│  - Envía Payload {monto, moneda, terminal_id}          │
│  - Escucha eventos: Esperando Pin, Aprobado, Rechazado │
└───────────────────────────┬────────────────────────────┘
                            │ Retorna Signal (Success/Fail)
┌───────────────────────────▼────────────────────────────┐
│                    Payment Processing Layer            │
│  - Registra Payment en `payments_list`                 │
│  - Actualiza `saldo_pendiente` en tiempo real          │
│  - Graba `auth_code` y `voucher` en `models.Pago`      │
└────────────────────────────────────────────────────────┘
```

---

## 2. MODIFICACIONES EN EL MODELO DE DATOS

En `models.Pago` / `models.DetallePago`:
* `auth_code`: `String(64)` - Código de autorización emitido por el adquirente.
* `voucher_nro`: `String(64)` - Número de comprobante/secuencia de la terminal.
* `card_brand`: `String(32)` - Marca de la tarjeta (Visa, Mastercard, etc.).
* `terminal_id`: `String(32)` - Identificador de la terminal POS física.

---

## 3. MITIGACIÓN DE RIESGOS

- **Timeout o Caída de Terminal**: Implementar temporizador de 60 segundos con opción de cancelación manual por el cajero sin abortar la venta.
- **Doble Cargo Accidental**: Deshabilitar el botón de cobro inmediatamente tras el envío del comando hasta recibir la confirmación o aborto.
