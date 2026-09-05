# setup_agent_validator.py
import sys
from pathlib import Path

# 1. Definición de rutas base
ROOT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = ROOT_DIR / ".agents"
SKILLS_DIR = AGENTS_DIR / "skills"
VALIDATOR_DIR = SKILLS_DIR / "validator"
AGENTS_MD_PATH = AGENTS_DIR / "AGENTS.md"

# 2. Código fuente robusto para validator.py
VALIDATOR_CODE = '''# .agents/skills/validator/validator.py
from decimal import Decimal, InvalidOperation
from typing import NamedTuple, List, Dict, Any

class ValidationStatus(NamedTuple):
    is_valid: bool
    errors: List[str]
    clean_data: Dict[str, Any]

class POSGuardrail:
    """Validador determinista pre-transacción para reglas de negocio POS Paraguay."""
    
    @staticmethod
    def validate_sale_item(payload: dict) -> ValidationStatus:
        errors = []
        
        # Validación y parsing numérico estricto (prohibido float)
        try:
            qty = Decimal(str(payload.get("quantity", "0")))
            price = Decimal(str(payload.get("unit_price", "0")))
            tax_rate = int(payload.get("tax_rate", 10))
        except (InvalidOperation, ValueError) as e:
            return ValidationStatus(False, [f"Error de conversión numérica: {str(e)}"], {})

        # Invariante 1: Límite balanza (máximo 3 decimales)
        if qty.as_tuple().exponent < -3:
            errors.append("La cantidad excede los 3 decimales de precisión de balanza.")

        if qty <= Decimal('0'):
            errors.append("La cantidad debe ser mayor a 0.")

        # Invariante 2: Moneda base PYG sin decimales
        subtotal = qty * price
        if subtotal % Decimal('1') != Decimal('0'):
            errors.append(f"Subtotal inválido ({subtotal}). PYG no permite fracciones.")

        # Invariante 3: Tasas tributarias oficiales de Paraguay
        if tax_rate not in (10, 5, 0):
            errors.append(f"Tasa tributaria ({tax_rate}%) inválida. Solo se permite 10, 5 o 0.")

        if errors:
            return ValidationStatus(False, errors, {})

        clean_data = {
            "plu_code": str(payload.get("plu_code", "")).strip(),
            "description": str(payload.get("description", "")).strip(),
            "quantity": qty,
            "unit_price": price.quantize(Decimal('1')),
            "subtotal": subtotal.quantize(Decimal('1')),
            "tax_rate": tax_rate
        }
        return ValidationStatus(True, [], clean_data)
'''

INIT_CODE = '''# .agents/skills/validator/__init__.py
from .validator import POSGuardrail, ValidationStatus

__all__ = ["POSGuardrail", "ValidationStatus"]
'''

SKILL_DOC_BLOCK = '''
### Skill: validator
- **Ruta**: `.agents/skills/validator/validator.py`
- **Propósito**: Guardia determinista pre-transacción para ventas, balanza e IVA paraguayo.
- **Entrada**: Diccionario (`plu_code`, `quantity`, `unit_price`, `tax_rate`).
- **Salida**: `ValidationStatus(is_valid: bool, errors: list, clean_data: dict)`.
- **Regla Inquebrantable**: Ningún dato se persiste en `stock_control.db` ni se pasa a la UI si `is_valid` es False.
'''


def run_setup():
    print("[*] Iniciando reorganización de arquitectura del agente...")

    # Verificación de entorno
    if not AGENTS_DIR.exists():
        print(f"[!] Error: No se encontró la carpeta '{AGENTS_DIR}'. Ejecuta el script desde la raíz del proyecto.")
        sys.exit(1)

    # 1. Crear directorio del paquete validator
    VALIDATOR_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[+] Carpeta de skill asegurada: {VALIDATOR_DIR}")

    # 2. Escribir validator.py dentro del paquete
    target_validator_file = VALIDATOR_DIR / "validator.py"
    target_validator_file.write_text(VALIDATOR_CODE, encoding="utf-8")
    print(f"[+] Archivo creado/actualizado: {target_validator_file}")

    # 3. Escribir __init__.py
    target_init_file = VALIDATOR_DIR / "__init__.py"
    target_init_file.write_text(INIT_CODE, encoding="utf-8")
    print(f"[+] Archivo de exportación creado: {target_init_file}")

    # 4. Limpiar archivos sueltos anteriores para no duplicar
    loose_files = [
        AGENTS_DIR / "validator.py",
        SKILLS_DIR / "validator.py"
    ]
    for old_file in loose_files:
        if old_file.exists():
            old_file.unlink()
            print(f"[-] Eliminado archivo suelto obsoleto: {old_file}")

    # 5. Registrar en AGENTS.md si no está presente
    if AGENTS_MD_PATH.exists():
        content = AGENTS_MD_PATH.read_text(encoding="utf-8")
        if "Skill: validator" not in content:
            updated_content = content + "\n" + SKILL_DOC_BLOCK
            AGENTS_MD_PATH.write_text(updated_content, encoding="utf-8")
            print(f"[+] Skill 'validator' registrada con éxito en {AGENTS_MD_PATH}")
        else:
            print("[i] La skill 'validator' ya se encontraba documentada en AGENTS.md.")
    else:
        print(f"[!] Aviso: No se encontró {AGENTS_MD_PATH}. Creando uno nuevo con la definición...")
        AGENTS_MD_PATH.write_text(f"# Directivas de Agentes\n{SKILL_DOC_BLOCK}", encoding="utf-8")

    print("\n[✓] Configuración completada correctamente.")


if __name__ == "__main__":
    run_setup()