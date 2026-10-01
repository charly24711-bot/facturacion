---
name: validator
description: Validador determinista pre-transaccional de reglas de negocio POS y finanzas en Guaraníes (PYG) y Triple Frontera.
---

# Skill: Validator POS

Valida la integridad de artículos, cantidades, subtotales, pesaje de balanza y tasas impositivas antes de persistir ventas o alterar existencias en `stock_control.db`.

## Reglas Obligatorias
- Toda operación aritmética debe utilizar `decimal.Decimal` con cuantización estricta.
- Prohibido el uso de `float`.
- Moneda base PYG sin decimales (`Decimal('1')`).
- Cantidades fraccionarias de balanza con hasta 3 decimales (`Decimal('0.001')`).
- Tasas de IVA permitidas: 10%, 5% y 0% (exentas).

## Uso
```python
from validator import POSGuardrail

resultado = POSGuardrail.validate_sale_item({
    "plu_code": "200010005001",
    "description": "Costilla de Primera",
    "quantity": "1.500",
    "unit_price": "45000",
    "tax_rate": 5
})

if not resultado.is_valid:
    print(resultado.errors)
```
