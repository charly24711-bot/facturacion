# master_fix_pos.py
import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = ROOT_DIR / ".agents"
SKILLS_DIR = AGENTS_DIR / "skills"
VALIDATOR_DIR = SKILLS_DIR / "validator"
AGENTS_MD = AGENTS_DIR / "AGENTS.md"
MAIN_WINDOW = ROOT_DIR / "ui" / "main_window.py"
DATABASE_PY = ROOT_DIR / "database.py"

VALIDATOR_PY_CODE = '''# .agents/skills/validator/validator.py
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
'''

INIT_PY_CODE = '''# .agents/skills/validator/__init__.py
from .validator import POSGuardrail, ValidationStatus, to_decimal

__all__ = ["POSGuardrail", "ValidationStatus", "to_decimal"]
'''

AGENTS_DOC = '''
### Skill: validator
- **Ruta**: `.agents/skills/validator/validator.py`
- **Uso obligatorio**: Todo flujo debe pasar por `POSGuardrail.validate_sale_item()` antes de registrar ventas o alterar stock en `stock_control.db`.
- **Regla Estricta**: No usar `float`. Toda operación aritmética con stock o precios se debe realizar exclusivamente con `decimal.Decimal`.
'''

def setup_validator_package():
    print("[1/3] Estructurando paquete de agente .agents/skills/validator/...")
    VALIDATOR_DIR.mkdir(parents=True, exist_ok=True)
    
    (VALIDATOR_DIR / "validator.py").write_text(VALIDATOR_PY_CODE, encoding="utf-8")
    (VALIDATOR_DIR / "__init__.py").write_text(INIT_PY_CODE, encoding="utf-8")

    # Limpieza de archivos sueltos anteriores
    for old_file in [AGENTS_DIR / "validator.py", SKILLS_DIR / "validator.py"]:
        if old_file.exists():
            old_file.unlink()
            print(f"  [-] Eliminado archivo suelto obsoleto: {old_file.name}")

    if AGENTS_MD.exists():
        content = AGENTS_MD.read_text(encoding="utf-8")
        if "Skill: validator" not in content:
            AGENTS_MD.write_text(content + "\n" + AGENTS_DOC, encoding="utf-8")
            print("  [+] Skill documentada en AGENTS.md")
    print("  [OK] Estructura de agente normalizada.")

def patch_python_source(file_path: Path):
    if not file_path.exists():
        print(f"  [!] Archivo no encontrado para parcheo: {file_path}")
        return

    content = file_path.read_text(encoding="utf-8")
    original = content

    # 1. Asegurar importación de Decimal
    if "from decimal import Decimal" not in content:
        content = "from decimal import Decimal, ROUND_HALF_UP\n" + content

    # 2. Inyectar función de coerción segura si no existe
    if "def _safe_dec(" not in content:
        safe_func = (
            "\ndef _safe_dec(v):\n"
            "    from decimal import Decimal\n"
            "    if v is None: return Decimal('0')\n"
            "    if isinstance(v, Decimal): return v\n"
            "    return Decimal(str(v).replace(',', '.'))\n"
        )
        content = content.replace("from decimal import Decimal, ROUND_HALF_UP\n", "from decimal import Decimal, ROUND_HALF_UP\n" + safe_func)

    # 3. Corregir asignaciones -= y += que mezclan Decimal y float
    # Transforma 'x -= y' en 'x = _safe_dec(x) - _safe_dec(y)'
    content = re.sub(
        r"(\w+(?:\.\w+)?)\s*-=\s*([a-zA-Z0-9_\.\(\)]+)",
        r"\1 = _safe_dec(\1) - _safe_dec(\2)",
        content
    )
    content = re.sub(
        r"(\w+(?:\.\w+)?)\s*\+=\s*([a-zA-Z0-9_\.\(\)]+)",
        r"\1 = _safe_dec(\1) + _safe_dec(\2)",
        content
    )

    # 4. Reemplazar conversiones 'float(' en flujos de cálculo
    content = re.sub(r"float\(([^)]+)\)", r"_safe_dec(\1)", content)

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        print(f"  [OK] Parcheado exitosamente: {file_path.name}")
    else:
        print(f"  [i] Sin cambios requeridos en: {file_path.name}")

def run():
    print("=" * 60)
    print("INICIANDO REPARACIÓN INTEGRAL POS (SUPERMERCADO)")
    print("=" * 60)
    
    setup_validator_package()
    
    print("\n[2/3] Parcheando código de interfaz gráfica (PyQt6)...")
    patch_python_source(MAIN_WINDOW)

    print("\n[3/3] Parcheando capa de base de datos...")
    patch_python_source(DATABASE_PY)

    print("\n" + "=" * 60)
    print("REPARACIÓN FINALIZADA CON ÉXITO")
    print("Ejecuta 'python main.py' para probar la venta y descuento de stock.")
    print("=" * 60)

if __name__ == "__main__":
    run()