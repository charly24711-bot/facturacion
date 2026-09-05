import sys
from decimal import Decimal

def parse_scale_barcode(barcode: str, modo: str = "peso") -> dict:
    """
    Parsea códigos generados por balanzas (Systel, Toledo, Marcas estándar).
    - barcode: Cadena de 13 dígitos numéricos.
    - modo: 'peso' (el valor incrustado son gramos) o 'precio' (el valor incrustado es monto en PYG).
    """
    barcode = barcode.strip()
    if len(barcode) != 13 or not barcode.isdigit():
        return {"valido": False, "error": "El código debe tener exactamente 13 dígitos numéricos."}

    prefix = barcode[0:2]
    if prefix not in ("20", "21"):
        return {
            "valido": True,
            "tipo": "PRODUCTO_ESTANDAR",
            "codigo": barcode,
            "es_balanza": False
        }

    plu_code = barcode[2:7]
    valor_raw = Decimal(barcode[7:12])
    check_digit = barcode[12]

    if modo == "peso":
        # Los 5 dígitos representan peso en kilogramos con 3 decimales (ej: 01500 = 1.500 kg)
        cantidad = (valor_raw / Decimal("1000")).quantize(Decimal("0.001"))
        return {
            "valido": True,
            "tipo": "BALANZA_PESO",
            "es_balanza": True,
            "plu": plu_code,
            "peso_kg": cantidad,
            "digito_verificador": check_digit
        }
    else:
        # Los 5 dígitos representan el precio total impreso (PYG sin decimales)
        return {
            "valido": True,
            "tipo": "BALANZA_PRECIO",
            "es_balanza": True,
            "plu": plu_code,
            "monto_total": valor_raw,
            "digito_verificador": check_digit
        }

if __name__ == "__main__":
    test_code = sys.argv[1] if len(sys.argv) > 1 else "2000105012503"
    resultado = parse_scale_barcode(test_code, modo="peso")
    print(f"\nParsing barcode: {test_code}")
    print(resultado)
