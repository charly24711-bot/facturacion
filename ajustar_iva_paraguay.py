from decimal import Decimal
from database import SessionLocal
import models

def clasificar_y_actualizar_iva():
    db = SessionLocal()
    
    # Palabras clave para Exentas (0%)
    iva_0_keywords = [
        'libro', 'revista', 'periodico', 'diario'
    ]
    
    # Palabras clave para IVA 10% prioritarias (Bebidas, Limpieza, Perfumería, Procesados)
    iva_10_keywords = [
        'gaseosa', 'cerveza', 'jugo', 'vino', 'bebida',
        'desodorante', 'lavandina', 'jabon', 'detergente', 'limpiador',
        'shampoo', 'acondicionador', 'crema dental',
        'fiambre', 'jamon', 'panceta', 'embutido', 'salame'
    ]
    
    # Palabras clave para IVA 5% en Paraguay (Ley 6380/19: Canasta familiar básica y agropecuarios en estado natural)
    iva_5_keywords = [
        'harina', 'azucar', 'yerba', 'leche', 'aceite', 'fideo', 'arroz',
        'queso paraguay', 'pan', 'sal', 'huevo', 'tomate', 'cebolla', 'papa',
        'zanahoria', 'locote', 'mandioca', 'banana', 'manzana', 'naranja',
        'carne', 'costilla', 'vacio', 'pechuga', 'muslo', 'pollo'
    ]
    
    productos = db.query(models.Product).all()
    actualizados_5 = []
    actualizados_10 = []
    actualizados_0 = []
    
    for p in productos:
        desc = p.art_descri.lower()
        
        if any(kw in desc for kw in iva_0_keywords):
            p.art_impu = Decimal('0.0')
            actualizados_0.append(f"{p.art_codigo} - {p.art_descri}")
        elif any(kw in desc for kw in iva_10_keywords):
            p.art_impu = Decimal('10.0')
            actualizados_10.append(f"{p.art_codigo} - {p.art_descri}")
        elif any(kw in desc for kw in iva_5_keywords):
            p.art_impu = Decimal('5.0')
            actualizados_5.append(f"{p.art_codigo} - {p.art_descri}")
        else:
            p.art_impu = Decimal('10.0')
            actualizados_10.append(f"{p.art_codigo} - {p.art_descri}")
            
    db.commit()
    db.close()
    
    print(f"Total productos en catálogo: {len(productos)}")
    print(f"-> Asignados a IVA 5% (Canasta Básica / Agro): {len(actualizados_5)}")
    print(f"-> Asignados a IVA 10% (Tasa General / Limpieza / Bebidas): {len(actualizados_10)}")
    print(f"-> Asignados a IVA 0% (Exentas): {len(actualizados_0)}")

if __name__ == "__main__":
    clasificar_y_actualizar_iva()
