"""
Wrapper / Exportador de tax_calculator desde .agents/skills/tax_calculator/scripts/tax_calculator.py
Garantiza resolución limpia de calcular_iva_linea en toda la aplicación y tests.
"""
import os
import sys

_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents', 'skills', 'tax_calculator', 'scripts'))
if _skill_path not in sys.path:
    sys.path.insert(0, _skill_path)

from decimal import Decimal, ROUND_HALF_UP

def calcular_iva_linea(monto_bruto: Decimal, tasa_iva: int) -> dict:
    """
    Desglosa el total cobrado según el régimen fiscal paraguayo.
    IVA 10% = Monto / 11
    IVA 5%  = Monto / 21
    Exenta  = Monto total (IVA = 0)
    """
    monto_bruto = monto_bruto.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    
    if tasa_iva == 10:
        iva = (monto_bruto / Decimal("11")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        gravada = monto_bruto - iva
        return {"bruto": monto_bruto, "gravada_10": gravada, "iva_10": iva, "gravada_5": Decimal("0"), "iva_5": Decimal("0"), "exenta": Decimal("0")}
    elif tasa_iva == 5:
        iva = (monto_bruto / Decimal("21")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        gravada = monto_bruto - iva
        return {"bruto": monto_bruto, "gravada_10": Decimal("0"), "iva_10": Decimal("0"), "gravada_5": gravada, "iva_5": iva, "exenta": Decimal("0")}
    else:
        return {"bruto": monto_bruto, "gravada_10": Decimal("0"), "iva_10": Decimal("0"), "gravada_5": Decimal("0"), "iva_5": Decimal("0"), "exenta": monto_bruto}
