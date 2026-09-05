name: "currency_manager"
description: "Gestor y simulador de cotizaciones multidivisa. Permite listar y establecer tasas de cambio."
---
# Currency Manager

Esta skill permite gestionar las tasas de cotización (Compra/Venta) en la base de datos de control de stock.

## Uso

Para listar las cotizaciones activas:
```bash
python .agents/skills/currency_manager/scripts/currency_manager.py --list
```

Para establecer una nueva cotización (ej. BRL, compra=1450, venta=1480):
```bash
python .agents/skills/currency_manager/scripts/currency_manager.py --set BRL 1450 1480
```
