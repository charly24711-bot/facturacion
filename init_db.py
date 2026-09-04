from database import engine, Base, SessionLocal
import models

def init_db():
    print("Creando tablas en la base de datos...")
    models.Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Insertar clientes de prueba si la tabla está vacía
    if db.query(models.Client).count() == 0:
        clientes = [
            models.Client(cli_codigo="002276", cli_nombre="DESPENSA SAN CAYETANO", cli_ruc="1234567-8", cli_limite=5000000.0),
            models.Client(cli_codigo="002815", cli_nombre="SUPERMERCADO LA ESPERANZA", cli_ruc="8765432-1", cli_limite=10000000.0),
            models.Client(cli_codigo="000001", cli_nombre="CONSUMIDOR FINAL", cli_ruc="444444-4", cli_limite=0.0),
        ]
        db.add_all(clientes)
        
    # Insertar productos de prueba si la tabla está vacía
    if db.query(models.Product).count() == 0:
        productos = [
            models.Product(art_codigo="000014", art_descri="ESCOBA ANGULAR CON PALO C/12", art_cbarra="7751234567890", art_costo=5000.0, art_preven=8000.0, art_stkini=50, art_impu=10.0),
            models.Product(art_codigo="000043", art_descri="ARROZ PONY GLASEADO 250GR C/20", art_cbarra="7750987654321", art_costo=15000.0, art_preven=23000.0, art_stkini=100, art_impu=5.0),
        ]
        db.add_all(productos)
        
    db.commit()
    db.close()
    print("Base de datos inicializada con éxito.")

if __name__ == "__main__":
    init_db()
