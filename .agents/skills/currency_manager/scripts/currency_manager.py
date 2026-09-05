import sys
import argparse
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Ajustar import según ruta raíz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from models import Currency, CurrencyRate
from database import Base, engine

Session = sessionmaker(bind=engine)

def list_rates():
    session = Session()
    rates = session.query(CurrencyRate).filter_by(is_active=True).all()
    print("\n--- COTIZACIONES ACTIVAS (BASE: PYG) ---")
    for r in rates:
        print(f"[{r.currency_code}] Compra: {r.buy_rate:,.2f} Gs. | Venta: {r.sell_rate:,.2f} Gs. ({r.created_at.strftime('%Y-%m-%d %H:%M')})")
    session.close()

def set_rate(code: str, buy: Decimal, sell: Decimal):
    session = Session()
    code = code.upper()
    curr = session.query(Currency).filter_by(code=code).first()
    if not curr:
        print(f"[ERROR] La moneda '{code}' no existe en la base de datos.")
        session.close()
        return

    # Desactivar tasa anterior
    session.query(CurrencyRate).filter_by(currency_code=code, is_active=True).update({"is_active": False})
    
    # Crear nueva tasa activa
    new_rate = CurrencyRate(
        currency_code=code,
        buy_rate=buy,
        sell_rate=sell,
        created_at=datetime.now(),
        is_active=True
    )
    session.add(new_rate)
    session.commit()
    print(f"[OK] Nueva cotización para {code} guardada: Compra={buy} | Venta={sell}")
    session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill de Cotizaciones POS")
    parser.add_argument("--list", action="store_true", help="Listar tasas activas")
    parser.add_argument("--set", nargs=3, metavar=("MONEDA", "COMPRA", "VENTA"), help="Registrar nueva cotización")
    args = parser.parse_args()

    if args.list:
        list_rates()
    elif args.set:
        code, buy, sell = args.set
        set_rate(code, Decimal(buy), Decimal(sell))
    else:
        parser.print_help()
