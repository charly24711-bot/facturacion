# WORKFLOW: ARQUEO DE CAJA CIEGO Y CIERRES X / Z

## Objetivo
Garantizar la cuadratura de tesorería multimoneda y prevenir fraudes o desfasajes cambiarios al finalizar un turno.

## 1. Arqueo Ciego (Ingreso por Cajero)
1. El cajero solicita "Cerrar Turno" en la UI.
2. El sistema bloquea nuevas ventas y **NO** muestra los totales teóricos del sistema.
3. El cajero cuenta y declara físicamente:
   - Efectivo Guaraníes (PYG)
   - Efectivo Dólares (USD)
   - Efectivo Reales (BRL)
   - Efectivo Pesos Argentinos (ARS)
   - Cupones POS / Tarjetas (en PYG)
   - Comprobantes de Transferencias / PIX (BRL o PYG)

## 2. Generación de Reporte X (Corte Parcial)
1. Requiere autorización de Supervisor (PIN/Contraseña).
2. El sistema calcula las diferencias por divisa:
   $$\text{Diferencia} = \text{Monto Declarado} - \text{Monto Teórico en Caja}$$
3. Imprime ticket ESC/POS con el detalle de ventas parciales sin asentar el cierre contable definitivo en la base.

## 3. Generación de Reporte Z (Cierre Definitivo)
1. Cierra formalmente el turno del cajero en la tabla `cash_registers` / `turnos`.
2. Asienta fecha/hora de fin, saldo inicial, total recaudado por moneda y sobrante/faltante.
3. Exporta la transacción a la cola de sincronización con marca `synced = False`.
4. Emite el ticket de cierre Z fiscal/interno y abre la gaveta de dinero.
