import re
from decimal import Decimal

def aplicar_formato_moneda(text, currency, line_edit):
    """
    Formatea dinámicamente el texto de un QLineEdit según la moneda.
    Para Guaraníes (PYG) usa puntos como separador de miles.
    Para otras monedas permite caracteres numéricos y separador decimal.
    """
    if not text:
        return
        
    if "PYG" in currency:
        raw = "".join(c for c in text if c.isdigit())
        if raw:
            try:
                formatted = f"{int(raw):,}".replace(",", ".")
                line_edit.blockSignals(True)
                line_edit.setText(formatted)
                line_edit.blockSignals(False)
            except ValueError:
                pass
    else:
        # Para otras monedas, permitir un separador decimal (coma o punto)
        clean = "".join(c for c in text if c.isdigit() or c in ".,")
        if clean != text:
            line_edit.blockSignals(True)
            line_edit.setText(clean)
            line_edit.blockSignals(False)


def parsear_monto(text, currency):
    """
    Parsea de manera robusta un string a un Decimal.
    Cumple con la 'Regla de la Coma' en todo el sistema.
    Retorna un string normalizado listo para Decimal(monto_str)
    """
    txt = text.strip()
    if not txt:
        return "0"
        
    if "PYG" in currency:
        monto_str = txt.replace(".", "").replace(",", "")
    else:
        # Si tiene punto y coma (ej. 1.000,50) -> el último es el decimal
        if "." in txt and "," in txt:
            if txt.rfind(",") > txt.rfind("."):
                monto_str = txt.replace(".", "").replace(",", ".")
            else:
                monto_str = txt.replace(",", "")
        # Si solo tiene coma, asumimos que es decimal (ej. 10,50)
        elif "," in txt:
            # A menos que sean exactamente 3 números después de la única coma
            partes = txt.split(",")
            if len(partes) == 2 and len(partes[1]) == 3:
                monto_str = txt.replace(",", "") # Asumimos miles
            else:
                monto_str = txt.replace(",", ".")
        else:
            monto_str = txt
            
    return monto_str
