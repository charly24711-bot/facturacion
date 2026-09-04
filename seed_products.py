from database import SessionLocal
import models

def seed_products():
    db = SessionLocal()
    
    # Lista de 20 productos variados
    productos = [
        {"codigo": "P001", "desc": "Yerba Mate Campesino 500g", "costo": 7000, "precio": 10000, "stock": 150},
        {"codigo": "P002", "desc": "Coca Cola 2 Litros Retornable", "costo": 8500, "precio": 12000, "stock": 200},
        {"codigo": "P003", "desc": "Cerveza Pilsen Lata 350ml", "costo": 3500, "precio": 5000, "stock": 500},
        {"codigo": "P004", "desc": "Arroz San Pedro 1Kg", "costo": 4000, "precio": 6500, "stock": 100},
        {"codigo": "P005", "desc": "Fideo Anita Spaguetti 400g", "costo": 2500, "precio": 4000, "stock": 80},
        {"codigo": "P006", "desc": "Aceite Mirasol 900ml", "costo": 9000, "precio": 13500, "stock": 120},
        {"codigo": "P007", "desc": "Azúcar Blanca Halcón 1Kg", "costo": 4500, "precio": 6500, "stock": 300},
        {"codigo": "P008", "desc": "Sal Fina Rica 500g", "costo": 1500, "precio": 2500, "stock": 60},
        {"codigo": "P009", "desc": "Leche Trébol Entera 1 Litro", "costo": 4800, "precio": 6500, "stock": 200},
        {"codigo": "P010", "desc": "Queso Paraguay (Por Kg)", "costo": 28000, "precio": 40000, "stock": 30},
        {"codigo": "P011", "desc": "Pan Felipe (Por Kg)", "costo": 6000, "precio": 10000, "stock": 50},
        {"codigo": "P012", "desc": "Galletita Salvado Bagley 200g", "costo": 3000, "precio": 4500, "stock": 90},
        {"codigo": "P013", "desc": "Café Nescafé Tradición 50g", "costo": 12000, "precio": 16000, "stock": 40},
        {"codigo": "P014", "desc": "Mantequilla Ilolay 200g", "costo": 11000, "precio": 15500, "stock": 35},
        {"codigo": "P015", "desc": "Jabón Omo Multiacción 800g", "costo": 10000, "precio": 14000, "stock": 150},
        {"codigo": "P016", "desc": "Detergente Activo Limón 750ml", "costo": 5500, "precio": 8000, "stock": 100},
        {"codigo": "P017", "desc": "Papel Higiénico Scott 4 Rollos", "costo": 8000, "precio": 11500, "stock": 80},
        {"codigo": "P018", "desc": "Pasta Dental Colgate 90g", "costo": 6500, "precio": 9000, "stock": 120},
        {"codigo": "P019", "desc": "Shampoo Sedal 340ml", "costo": 14000, "precio": 19000, "stock": 60},
        {"codigo": "P020", "desc": "Desodorante Rexona Aerosol", "costo": 13000, "precio": 18500, "stock": 70},
    ]
    
    agregados = 0
    for p in productos:
        # Verificar que no exista
        existe = db.query(models.Product).filter_by(art_codigo=p["codigo"]).first()
        if not existe:
            nuevo_prod = models.Product(
                art_codigo=p["codigo"],
                art_descri=p["desc"],
                art_costo=p["costo"],
                art_preven=p["precio"],
                art_stkini=p["stock"],
                art_impu=10.0 # IVA 10% por defecto
            )
            db.add(nuevo_prod)
            agregados += 1
            
    try:
        db.commit()
        print(f"Se agregaron {agregados} productos exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"Error al agregar productos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_products()
