# WORKFLOW: COBRO MIXTO (SPLIT) Y VUELTO CRUZADO

## Objetivo
Resolver transacciones donde el cliente combina distintos medios de pago y monedas, manteniendo la precisión matemática en Guaraníes (PYG).

## 1. Conversión de Importes
1. El total de la venta siempre se consolida y liquida en **PYG** (sin decimales).
2. Para pagos en moneda extranjera, el sistema aplica la cotización de **Compra** activa:
   $$\text{Monto PYG} = \text{Monto Moneda Extranjera} \times \text{buy\_rate}$$

## 2. Secuencia de Cobro
1. El total adeudado inicia en el saldo de la venta: $S_0 = \text{Total PYG}$.
2. Por cada pago ingresado:
   - Pago 1: Efectivo USD $20.00 \to 20.00 \times 7.500 = 150.000\text{ Gs.}$
   - Nuevo Saldo: $S_1 = S_0 - 150.000\text{ Gs.}$
   - Pago 2: PIX BRL $50.00 \to 50.00 \times 1.450 = 72.500\text{ Gs.}$
   - Nuevo Saldo: $S_2 = S_1 - 72.500\text{ Gs.}$
3. Cuando la suma de pagos supera o iguala a $S_0$, el saldo restante se convierte en **Vuelto**.

## 3. Cálculo de Vuelto en Moneda Solicitada
1. Si el cliente pide vuelto en PYG:
   $$\text{Vuelto PYG} = \text{Pagos Totales PYG} - \text{Total Venta PYG}$$
2. Si el cliente pide vuelto en USD/BRL/ARS (sujeto a disponibilidad en gaveta):
   $$\text{Vuelto Moneda} = \frac{\text{Vuelto PYG}}{\text{sell\_rate}}$$
   *(Aplica redondeo hacia abajo a 2 decimales para evitar pérdidas por fracción centesimal).*
