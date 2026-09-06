import os
import sys
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont
from database import SessionLocal
import models

def get_product_theme(desc: str):
    d = desc.lower()
    
    # 1. Carnicería / Aves
    if any(k in d for k in ['carne', 'costilla', 'vacio', 'pechuga', 'muslo', 'pollo', 'cerdo', 'panceta', 'jamon']):
        return {
            'bg_top': (225, 29, 72),
            'bg_bot': (159, 18, 57),
            'tag': 'CARNICERÍA',
            'icon': '🥩' if not any(k in d for k in ['pollo', 'pechuga', 'muslo']) else '🍗',
            'box_color': (255, 241, 242)
        }
    # 2. Verdulería / Frutería
    if any(k in d for k in ['tomate', 'cebolla', 'papa', 'zanahoria', 'locote', 'mandioca', 'banana', 'manzana', 'naranja']):
        icon = '🍅' if 'tomate' in d else ('🍌' if 'banana' in d else ('🍎' if 'manzana' in d else ('🍊' if 'naranja' in d else '🥔')))
        return {
            'bg_top': (101, 163, 13),
            'bg_bot': (63, 98, 18),
            'tag': 'VERDULERÍA / FRUTAS',
            'icon': icon,
            'box_color': (247, 254, 231)
        }
    # 3. Lácteos y Quesos
    if any(k in d for k in ['leche', 'queso']):
        return {
            'bg_top': (14, 165, 233),
            'bg_bot': (3, 105, 161),
            'tag': 'LÁCTEOS Y QUESOS',
            'icon': '🥛' if 'leche' in d else '🧀',
            'box_color': (240, 249, 255)
        }
    # 4. Bebidas / Cervezas
    if any(k in d for k in ['gaseosa', 'cerveza', 'jugo', 'agua', 'vino']):
        icon = '🍺' if 'cerveza' in d else ('🥤' if 'gaseosa' in d else ('🧃' if 'jugo' in d else '💧'))
        return {
            'bg_top': (234, 88, 12),
            'bg_bot': (194, 65, 12),
            'tag': 'BEBIDAS',
            'icon': icon,
            'box_color': (255, 247, 237)
        }
    # 5. Limpieza del Hogar
    if any(k in d for k in ['lavandina', 'detergente', 'jabon en polvo', 'desodorante ambiente', 'escoba']):
        return {
            'bg_top': (16, 185, 129),
            'bg_bot': (4, 120, 87),
            'tag': 'LIMPIEZA DEL HOGAR',
            'icon': '🧹' if 'escoba' in d else '🧴',
            'box_color': (236, 253, 245)
        }
    # 6. Perfumería y Cuidado Personal
    if any(k in d for k in ['shampoo', 'acondicionador', 'crema dental', 'jabon de tocador', 'sedal']):
        return {
            'bg_top': (147, 51, 234),
            'bg_bot': (109, 40, 217),
            'tag': 'CUIDADO PERSONAL',
            'icon': '✨',
            'box_color': (250, 245, 255)
        }
    # 7. Almacén / Canasta Básica (Harina, Fideo, Arroz, Azúcar, Yerba)
    icon = '🌾'
    if 'fideo' in d: icon = '🍝'
    elif 'yerba' in d: icon = '🌿'
    elif 'azucar' in d: icon = '🍬'
    elif 'arroz' in d: icon = '🍚'
    
    return {
        'bg_top': (245, 158, 11),
        'bg_bot': (180, 83, 9),
        'tag': 'ALMACÉN / CANASTA',
        'icon': icon,
        'box_color': (254, 252, 232)
    }

def crear_imagen_producto(codigo: str, descripcion: str, uom: str, precio: str, filepath: str):
    width, height = 400, 400
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    theme = get_product_theme(descripcion)
    
    # 1. Dibujar degradado vertical de fondo
    r1, g1, b1 = theme['bg_top']
    r2, g2, b2 = theme['bg_bot']
    for y in range(height):
        ratio = y / height
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # 2. Caja blanca central para tarjeta de producto
    margin = 25
    draw.rounded_rectangle(
        [margin, margin, width - margin, height - margin],
        radius=20,
        fill=theme['box_color'],
        outline=(255, 255, 255),
        width=3
    )
    
    # 3. Badge de Categoría
    draw.rounded_rectangle(
        [margin + 20, margin + 18, width - margin - 20, margin + 48],
        radius=8,
        fill=(r1, g1, b1)
    )
    
    # Fuentes estándar del sistema Windows
    try:
        font_tag = ImageFont.truetype("arialbd.ttf", 13)
        font_title = ImageFont.truetype("arialbd.ttf", 18)
        font_icon = ImageFont.truetype("seguiemj.ttf", 64)
        font_price = ImageFont.truetype("arialbd.ttf", 22)
        font_sub = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font_tag = ImageFont.load_default()
        font_title = font_tag
        font_icon = font_tag
        font_price = font_tag
        font_sub = font_tag

    # Texto del tag
    tag_text = theme['tag']
    draw.text((width // 2, margin + 33), tag_text, font=font_tag, fill=(255, 255, 255), anchor="mm")
    
    # 4. Icono representativo grande en el centro
    draw.text((width // 2, height // 2 - 30), theme['icon'], font=font_icon, fill=(30, 30, 30), anchor="mm")
    
    # 5. Nombre del producto (dividido en 2 líneas si es largo)
    desc_clean = descripcion.strip()
    words = desc_clean.split()
    if len(desc_clean) > 24 and len(words) > 2:
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        draw.text((width // 2, height // 2 + 55), line1, font=font_title, fill=(30, 41, 59), anchor="mm")
        draw.text((width // 2, height // 2 + 78), line2, font=font_title, fill=(30, 41, 59), anchor="mm")
    else:
        draw.text((width // 2, height // 2 + 65), desc_clean, font=font_title, fill=(30, 41, 59), anchor="mm")
        
    # 6. Franja de Precio y Código
    draw.rounded_rectangle(
        [margin + 20, height - margin - 60, width - margin - 20, height - margin - 15],
        radius=10,
        fill=(255, 255, 255),
        outline=(203, 213, 225),
        width=2
    )
    
    precio_str = f"Gs. {precio}"
    cod_str = f"CÓD: {codigo} ({uom})"
    draw.text((margin + 35, height - margin - 38), cod_str, font=font_sub, fill=(100, 116, 139), anchor="lm")
    draw.text((width - margin - 35, height - margin - 38), precio_str, font=font_price, fill=(22, 101, 52), anchor="rm")
    
    img.save(filepath, "PNG")

def procesar_todos_los_productos():
    db = SessionLocal()
    productos = db.query(models.Product).all()
    
    out_dir = os.path.abspath("assets/images")
    os.makedirs(out_dir, exist_ok=True)
    
    actualizados = 0
    for p in productos:
        filename = f"{p.art_codigo}.png"
        filepath = os.path.join(out_dir, filename)
        
        precio_formateado = f"{Decimal(str(p.art_preven or 0)):,.0f}"
        crear_imagen_producto(
            codigo=p.art_codigo,
            descripcion=p.art_descri,
            uom=p.uom or "Un",
            precio=precio_formateado,
            filepath=filepath
        )
        
        # Guardar ruta relativa normalizada en la BD
        rel_path = f"assets/images/{filename}"
        p.image_path = rel_path
        actualizados += 1
        
    db.commit()
    db.close()
    print(f"Éxito: Se generaron y asignaron {actualizados} fotos de productos en '{out_dir}'.")

if __name__ == "__main__":
    procesar_todos_los_productos()
