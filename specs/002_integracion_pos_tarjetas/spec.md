# SPEC-002: INTEGRACIÓN DE TERMINALES ELECTRÓNICAS DE COBRO (POS / PINPAD)

**Estado:** En Planificación  
**Versión:** 1.0.0  
**Fecha:** Septiembre 2026

---

## 1. PROPÓSITO Y ALCANCE
Estandarizar la comunicación y procesamiento de pagos con terminales electrónicas de cobro (POS físicos / Pinpads de adquirentes como Bancard, Dinelco, Redelcom o protocolos TEF) integrados directamente al flujo de caja de `PaymentDialog` y al cierre de arqueo de `CashSession`.

---

## 2. REQUERIMIENTOS FUNCIONALES

### RF-01: Disparo Automático de Monto a Terminal POS
- El cajero selecciona el medio de pago electrónico (Tarjeta Débito, Tarjeta Crédito, PIX / QR Bancario).
- El sistema envía el monto adeudado (o monto parcial especificado) en `Decimal` a la terminal POS conectada (vía Socket TCP/IP, puerto Serie/USB o API local).

### RF-02: Recepción Atómica de Confirmación (Voucher / Auth Code)
- El sistema espera la respuesta del dispositivo sin congelar la interfaz de usuario (`QThread`).
- Si la transacción es aprobada, captura automáticamente:
  * Código de Autorización (`auth_code`).
  * Número de Referencia / Lote (`voucher_nro`, `lote_nro`).
  * Emisor de Tarjeta (Visa, Mastercard, Maestro, etc.).
  * Tipo de Operación (Débito, Crédito en 1 pago o cuotas).
- En caso de rechazo o cancelación en el aparato, la venta permanece abierta en pantalla sin alteraciones.

### RF-03: Resta Instantánea y Split Payments
- El monto aprobado se deduce automáticamente del saldo total adeudado:
  $$\text{Saldo Pendiente} = \text{Total Factura} - \sum \text{Pagos Acreditados}$$
- Si el saldo resultante es 0, la venta finaliza y emite el ticket/factura fiscal KuDE.
- Si queda saldo pendiente, el cajero puede combinar el pago restante con efectivo (PYG, USD, BRL, ARS) u otra tarjeta.

### RF-04: Asiento Contable y Cuadre de Cierre Z
- Los cobros con tarjeta se clasifican en la base de datos bajo el canal no monetario (bancario/adquirente).
- En el **Reporte Z** y **Arqueo de Caja**, el sistema concilia de forma independiente:
  1. **Efectivo Físico en Cajón** (conteo de billetes/monedas).
  2. **Total Lote POS Electrónico** (suma de vouchers autorizados).

---

## 3. REQUERIMIENTOS NO FUNCIONALES

### RNF-01: Cero Bloqueo de UI (Asincronía)
- La comunicación I/O con el dispositivo POS debe residir en un worker asíncrono para que el cajero pueda cancelar o consultar sin que la ventana quede "No responde".

### RNF-02: Precisión Decimal y Resiliencia
- Todo importe enviado y recibido debe validarse estrictamente con `decimal.Decimal`.
