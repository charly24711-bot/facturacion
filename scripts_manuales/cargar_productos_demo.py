import sys
import os
import random
from decimal import Decimal

# Añadir el entorno local y paquetes al path
sys.path.insert(0, r"c:\ENTORNO LOCAL\Control\venv\Lib\site-packages")
sys.path.insert(0, r"c:\ENTORNO LOCAL\Control")

import database
from models import Product, Category, Brand

def seed_database():
    db = database.get_db()
    
    try:
        # 1. Crear Categorías
        categorias = ["Bebidas", "Almacén", "Lácteos", "Limpieza", "Carnicería", "Verdulería", "Golosinas"]
        cat_objs = []
        for c_name in categorias:
            cat = db.query(Category).filter_by(name=c_name).first()
            if not cat:
                cat = Category(name=c_name)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_objs.append(cat)
            
        # 2. Crear Marcas
        marcas = ["Coca-Cola", "Brahma", "Quilmes", "Arcor", "La Serenísima", "Omo", "Nestlé", "Nescafé", "Bimbo", "Genérico"]
        brand_objs = []
        for b_name in marcas:
            brand = db.query(Brand).filter_by(name=b_name).first()
            if not brand:
                brand = Brand(name=b_name)
                db.add(brand)
                db.commit()
                db.refresh(brand)
            brand_objs.append(brand)
            
        # 3. Productos (Mock Data Local de Supermercado)
        productos_mock = [
            # Almacén
            {"cbarra": "7791234567890", "desc": "YERBA MATE KURUPÍ CLÁSICA 500G", "costo": 8000, "precio": 12500, "cat": "Almacén", "marca": "Genérico", "uom": "Un"},
            {"cbarra": "7799876543210", "desc": "AZÚCAR BLANCA TUKANG 1KG", "costo": 4500, "precio": 6500, "cat": "Almacén", "marca": "Genérico", "uom": "Un"},
            {"cbarra": "7791111111111", "desc": "ARROZ TÍO JUAN TIPO 1 1KG", "costo": 5000, "precio": 7000, "cat": "Almacén", "marca": "Genérico", "uom": "Un"},
            {"cbarra": "7792222222222", "desc": "FIDEOS SPAGHETTI ANITA 400G", "costo": 2500, "precio": 3800, "cat": "Almacén", "marca": "Genérico", "uom": "Un"},
            {"cbarra": "7793333333333", "desc": "CAFÉ NESCAFÉ CLÁSICO 200G", "costo": 35000, "precio": 45000, "cat": "Almacén", "marca": "Nescafé", "uom": "Un"},
            {"cbarra": "7794444444444", "desc": "PAN LACTAL BIMBO BLANCO 500G", "costo": 12000, "precio": 16500, "cat": "Almacén", "marca": "Bimbo", "uom": "Un"},
            
            # Bebidas
            {"cbarra": "7790000000010", "desc": "COCA-COLA SABOR ORIGINAL 2L RETORNABLE", "costo": 9000, "precio": 13000, "cat": "Bebidas", "marca": "Coca-Cola", "uom": "Un"},
            {"cbarra": "7790000000020", "desc": "CERVEZA BRAHMA LATA 473ML", "costo": 3500, "precio": 5500, "cat": "Bebidas", "marca": "Brahma", "uom": "Un"},
            {"cbarra": "7790000000030", "desc": "CERVEZA QUILMES CLÁSICA 1L RET", "costo": 7000, "precio": 10500, "cat": "Bebidas", "marca": "Quilmes", "uom": "Un"},
            {"cbarra": "7790000000040", "desc": "AGUA MINERAL KIN SIN GAS 2L", "costo": 2500, "precio": 4000, "cat": "Bebidas", "marca": "Coca-Cola", "uom": "Un"},
            
            # Limpieza
            {"cbarra": "7795555555555", "desc": "JABÓN EN POLVO OMO MULTIACCIÓN 800G", "costo": 14000, "precio": 21000, "cat": "Limpieza", "marca": "Omo", "uom": "Un"},
            {"cbarra": "7796666666666", "desc": "LAVANDINA AYUDÍN TRADICIONAL 1L", "costo": 3500, "precio": 5500, "cat": "Limpieza", "marca": "Genérico", "uom": "Un"},
            {"cbarra": "7797777777777", "desc": "DETERGENTE MAGISTRAL LIMÓN 300ML", "costo": 5500, "precio": 8500, "cat": "Limpieza", "marca": "Genérico", "uom": "Un"},
            
            # Lácteos
            {"cbarra": "7798888888888", "desc": "LECHE DESCREMADA LA SERENÍSIMA 1L", "costo": 6000, "precio": 8500, "cat": "Lácteos", "marca": "La Serenísima", "uom": "Un"},
            {"cbarra": "7799999999999", "desc": "QUESO CREMA CASANCREM CLÁSICO 200G", "costo": 12000, "precio": 17500, "cat": "Lácteos", "marca": "La Serenísima", "uom": "Un"},
            
            # Productos de Balanza (Peso)
            {"cbarra": "2000001000001", "desc": "TOMATE PERITA (KG)", "costo": 4000, "precio": 7500, "cat": "Verdulería", "marca": "Genérico", "uom": "Kg", "frac": True},
            {"cbarra": "2000002000002", "desc": "PAPA NEGRA (KG)", "costo": 2500, "precio": 4500, "cat": "Verdulería", "marca": "Genérico", "uom": "Kg", "frac": True},
            {"cbarra": "2100001000001", "desc": "CARNE VACUNA COSTILLA (KG)", "costo": 32000, "precio": 45000, "cat": "Carnicería", "marca": "Genérico", "uom": "Kg", "frac": True},
            {"cbarra": "2100002000002", "desc": "POLLO ENTERO FRESCO (KG)", "costo": 11000, "precio": 15500, "cat": "Carnicería", "marca": "Genérico", "uom": "Kg", "frac": True},
        ]
        
        # Diccionarios para buscar rapido ids
        cat_dict = {c.name: c.id for c in cat_objs}
        brand_dict = {b.name: b.id for b in brand_objs}
        
        print("Cargando productos en la base de datos local...")
        for i, item in enumerate(productos_mock):
            # Generar codigo interno tipo P00001
            art_codigo = f"P{i+1:05d}"
            
            prod = db.query(Product).filter_by(art_cbarra=item["cbarra"]).first()
            if not prod:
                prod = Product(
                    art_codigo=art_codigo,
                    art_descri=item["desc"],
                    art_cbarra=item["cbarra"],
                    art_costo=Decimal(str(item["costo"])),
                    art_preven=Decimal(str(item["precio"])),
                    art_codmnd="PYG",
                    art_impu=Decimal('10.0'), # Asumimos IVA 10% por defecto
                    art_stkini=Decimal('100.0') if not item.get('frac') else Decimal('50.000'),
                    category_id=cat_dict.get(item["cat"]),
                    brand_id=brand_dict.get(item["marca"]),
                    uom=item["uom"],
                    is_fractional=item.get("frac", False)
                )
                db.add(prod)
                
        db.commit()
        print(f"¡Carga completada exitosamente! Se revisaron/crearon {len(productos_mock)} productos.")
        
    except Exception as e:
        print(f"Error al cargar la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
