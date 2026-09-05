# .agents/skills/validator/validator.py
from decimal import Decimal, InvalidOperation
from typing import NamedTuple, List, Dict, Any

class ValidationStatus(NamedTuple):
    is_valid: bool
    errors: List[str]
    clean_data: Dict[str, Any]

def to_decimal(val: Any, default: str = "0") -> Decimal:
    """Convierte de forma segura strings, floats o ints a Decimal puro."""
    if val is None:
        return Decimal(default)
    if isinstance(val, Decimal):
        return val
    try:
        clean_str = str(val).strip().replace(",", ".")
        return Decimal(clean_str)
    except (InvalidOperation, ValueError):
        return Decimal(default)

class POSGuardrail:
    """Validador determinista pre-transacción para reglas de negocio POS Paraguay."""
    
    @staticmethod
    def validate_sale_item(payload: dict) -> ValidationStatus:
        errors = []
        try:
            qty = to_decimal(payload.get("quantity", "0"))
            price = to_decimal(payload.get("unit_price", "0"))
            tax_rate = int(payload.get("tax_rate", 10))
        except Exception as e:
            return ValidationStatus(False, [f"Error de conversión: {str(e)}"], {})

        if qty <= Decimal("0"):
            errors.append("La cantidad debe ser mayor a 0.")

        if qty.as_tuple().exponent < -3:
            errors.append("La cantidad excede los 3 decimales permitidos para balanzas.")

        subtotal = qty * price
        if subtotal % Decimal("1") != Decimal("0"):
            errors.append(f"Subtotal ({subtotal}) inválido. PYG no admite centavos.")

        if tax_rate not in (10, 5, 0):
            errors.append(f"Tasa IVA ({tax_rate}%) inválida. Solo se admite 10, 5 o 0.")

        if errors:
            return ValidationStatus(False, errors, {})

        return ValidationStatus(True, [], {
            "plu_code": str(payload.get("plu_code", "")).strip(),
            "description": str(payload.get("description", "")).strip(),
            "quantity": qty,
            "unit_price": price.quantize(Decimal("1")),
            "subtotal": subtotal.quantize(Decimal("1")),
            "tax_rate": tax_rate
        })
