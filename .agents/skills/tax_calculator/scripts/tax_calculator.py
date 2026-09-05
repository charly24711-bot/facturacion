import sys
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

if __name__ == "__main__":
    ejemplo_10 = calcular_iva_linea(Decimal("110000"), 10)
    ejemplo_5 = calcular_iva_linea(Decimal("21000"), 5)
    print("Prueba IVA 10% sobre 110.000 Gs.:", ejemplo_10)
    print("Prueba IVA 5% sobre 21.000 Gs.:", ejemplo_5)
