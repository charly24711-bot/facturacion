from database import SessionLocal, engine
import models
import datetime

def seed_supermarket_data():
    db = SessionLocal()
    
    # 1. Crear Categorías
    categorias_nombres = ["Almacén", "Bebidas", "Lácteos", "Limpieza", "Perfumería", "Fiambres y Quesos", "Panadería"]
    cat_map = {}
    for nombre in categorias_nombres:
        c = db.query(models.Category).filter_by(name=nombre).first()
        if not c:
            c = models.Category(name=nombre)
            db.add(c)
            db.flush()
        cat_map[nombre] = c.id
        
    # 2. Crear Marcas
    marcas_nombres = ["Coca-Cola", "Pilsen", "Trébol", "Omo", "Sedal", "Campesino", "Generico", "San Pedro", "Anita", "Mirasol"]
    brand_map = {}
    for nombre in marcas_nombres:
        b = db.query(models.Brand).filter_by(name=nombre).first()
        if not b:
            b = models.Brand(name=nombre)
            db.add(b)
            db.flush()
        brand_map[nombre] = b.id
        
    # 3. Crear Productos
    productos = [
        {"codigo": "P001", "desc": "Yerba Mate Campesino 500g", "costo": 7000, "precio": 10000, "stock": 150, "cat": "Almacén", "brand": "Campesino", "uom": "Un", "frac": False},
        {"codigo": "P002", "desc": "Coca Cola 2 Litros Retornable", "costo": 8500, "precio": 12000, "stock": 200, "cat": "Bebidas", "brand": "Coca-Cola", "uom": "Un", "frac": False},
        {"codigo": "P003", "desc": "Cerveza Pilsen Lata 350ml", "costo": 3500, "precio": 5000, "stock": 500, "cat": "Bebidas", "brand": "Pilsen", "uom": "Un", "frac": False},
        {"codigo": "P010", "desc": "Queso Paraguay", "costo": 28000, "precio": 40000, "stock": 30.5, "cat": "Fiambres y Quesos", "brand": "Generico", "uom": "Kg", "frac": True},
        {"codigo": "P011", "desc": "Pan Felipe", "costo": 6000, "precio": 10000, "stock": 50.2, "cat": "Panadería", "brand": "Generico", "uom": "Kg", "frac": True},
        {"codigo": "P015", "desc": "Jabón Omo Multiacción 800g", "costo": 10000, "precio": 14000, "stock": 150, "cat": "Limpieza", "brand": "Omo", "uom": "Un", "frac": False},
        {"codigo": "P019", "desc": "Shampoo Sedal 340ml", "costo": 14000, "precio": 19000, "stock": 60, "cat": "Perfumería", "brand": "Sedal", "uom": "Un", "frac": False},
    ]
    
    for p in productos:
        prod = db.query(models.Product).filter_by(art_codigo=p["codigo"]).first()
        if not prod:
            prod = models.Product(
                art_codigo=p["codigo"],
                art_descri=p["desc"],
                art_cbarra=f"7750000{p['codigo']}", # Codigo principal falso
                art_costo=p["costo"],
                art_preven=p["precio"],
                art_stkini=p["stock"],
                art_impu=10.0,
                art_stkmin=10,
                art_stkmax=200,
                category_id=cat_map.get(p["cat"]),
                brand_id=brand_map.get(p["brand"]),
                uom=p["uom"],
                is_fractional=p["frac"],
                location="Góndola 1",
                is_active=True
            )
            db.add(prod)
            db.flush()
            
            # Crear código de barra por Pack (Ej. Cerveza Pilsen Pack x6)
            if p["codigo"] == "P003":
                barcode_pack = models.ProductBarcode(
                    product_id=prod.id,
                    barcode="7750000PACK6",
                    factor_conversion=6.0
                )
                db.add(barcode_pack)
                
            # Crear Lote para Lácteos/Fiambres
            if p["codigo"] == "P010":
                lote = models.ProductBatch(
                    product_id=prod.id,
                    lote="LOTE-001",
                    fecha_vencimiento=datetime.datetime.utcnow() + datetime.timedelta(days=15),
                    stock_actual=p["stock"]
                )
                db.add(lote)

    try:
        db.commit()
        print("Datos de Supermercado sembrados con éxito.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_supermarket_data()
