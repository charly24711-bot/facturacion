from database import engine, Base, SessionLocal
import models
from decimal import Decimal

def init_db():
    print("Creando tablas en la base de datos...")
    models.Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Insertar monedas por defecto si la tabla está vacía
    if db.query(models.Currency).count() == 0:
        monedas_base = [
            models.Currency(code='PYG', name='Guaraní', symbol='Gs.', decimals=0, is_base=True),
            models.Currency(code='USD', name='Dólar Estadounidense', symbol='US$', decimals=2, is_base=False),
            models.Currency(code='BRL', name='Real Brasileño', symbol='R$', decimals=2, is_base=False),
            models.Currency(code='ARS', name='Peso Argentino', symbol='$', decimals=2, is_base=False),
        ]
        db.add_all(monedas_base)
        
        tasas = [
            models.CurrencyRate(currency_code='PYG', buy_rate=Decimal("1.0"), sell_rate=Decimal("1.0")),
            models.CurrencyRate(currency_code='USD', buy_rate=Decimal("7450.0"), sell_rate=Decimal("7500.0")),
            models.CurrencyRate(currency_code='BRL', buy_rate=Decimal("1320.0"), sell_rate=Decimal("1350.0")),
            models.CurrencyRate(currency_code='ARS', buy_rate=Decimal("5.5"), sell_rate=Decimal("6.0"))
        ]
        db.add_all(tasas)
    
    # Insertar clientes de prueba si la tabla está vacía
    if db.query(models.Client).count() == 0:
        clientes = [
            models.Client(cli_codigo="002276", cli_nombre="DESPENSA SAN CAYETANO", cli_ruc="1234567-8", cli_limite=Decimal("5000000.0")),
            models.Client(cli_codigo="002815", cli_nombre="SUPERMERCADO LA ESPERANZA", cli_ruc="8765432-1", cli_limite=Decimal("10000000.0")),
            models.Client(cli_codigo="000001", cli_nombre="CONSUMIDOR FINAL", cli_ruc="444444-4", cli_limite=Decimal("0.0")),
        ]
        db.add_all(clientes)
        
    # Insertar productos de prueba si la tabla está vacía
    if db.query(models.Product).count() == 0:
        productos = [
            models.Product(art_codigo="000014", art_descri="ESCOBA ANGULAR CON PALO C/12", art_cbarra="7751234567890", art_costo=Decimal("5000.0"), art_preven=Decimal("8000.0"), art_stkini=50, art_impu=Decimal("10.0"), image_path="assets/images/000014.png"),
            models.Product(art_codigo="000043", art_descri="ARROZ PONY GLASEADO 250GR C/20", art_cbarra="7750987654321", art_costo=Decimal("15000.0"), art_preven=Decimal("23000.0"), art_stkini=100, art_impu=Decimal("5.0"), image_path="assets/images/000043.png"),
        ]
        db.add_all(productos)
        
    db.commit()
    db.close()
    print("Base de datos inicializada con éxito.")

if __name__ == "__main__":
    init_db()
