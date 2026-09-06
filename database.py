from decimal import Decimal, ROUND_HALF_UP

def _safe_dec(v):
    from decimal import Decimal
    if v is None: return Decimal('0')
    if isinstance(v, Decimal): return v
    return Decimal(str(v).replace(',', '.'))

def format_stock_qty(val) -> str:
    """
    Formatea una cantidad o stock eliminando ceros innecesarios a la derecha.
    - Si es entero (ej. 120.0000000000): devuelve '120' o '1,200'.
    - Si tiene decimales (balanza ej. 1.2500000000): devuelve '1.25' o hasta 3 decimales sin ceros superfluos.
    - Para números negativos (ej. -8.0000000000): devuelve '-8'.
    """
    if val is None:
        return "0"
    try:
        from decimal import Decimal
        d = Decimal(str(val))
        if d == d.to_integral():
            return f"{int(d):,}"
        # Decimal con hasta 3 decimales sin ceros superfluos al final
        s = f"{d:,.3f}".rstrip('0').rstrip('.')
        return s
    except Exception:
        return str(val)

def format_iva_rate(val) -> str:
    """
    Formatea la tasa de IVA paraguaya vigente (10%, 5% o Exenta).
    """
    if val is None:
        return "10%"
    try:
        from decimal import Decimal
        d = Decimal(str(val))
        if d == 0:
            return "Exenta (0%)"
        elif d == 5:
            return "5%"
        elif d == 10:
            return "10%"
        else:
            if d == d.to_integral():
                return f"{int(d)}%"
            return f"{d}%"
    except Exception:
        return f"{val}%"

def resolve_image_path(image_path: str = None, art_codigo: str = None) -> str:
    """
    Resuelve la ruta absoluta de la imagen del producto con soporte robusto:
    1. Si image_path existe en disco (absoluto o relativo al CWD o a la raíz del proyecto).
    2. Si no, busca automáticamente por código de artículo en assets/images/{art_codigo}.png.
    Devuelve la ruta absoluta si existe, o None si no se encuentra.
    """
    import os
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    candidates = []
    if image_path:
        candidates.append(image_path)
        candidates.append(os.path.join(project_root, image_path))
        candidates.append(os.path.join(project_root, 'assets', 'images', os.path.basename(image_path)))
        
    if art_codigo:
        candidates.append(os.path.join(project_root, 'assets', 'images', f"{art_codigo}.png"))
        candidates.append(os.path.join(project_root, 'assets', 'images', f"{str(art_codigo).zfill(6)}.png"))
        
    for cand in candidates:
        if cand and os.path.exists(cand):
            return os.path.abspath(cand)
            
    return None

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Cambiamos a SQLite temporalmente para facilitar el desarrollo sin depender de un servidor MySQL activo.
# Luego se puede cambiar a: "mysql+pymysql://root:password@localhost/stock_control"
DATABASE_URL = "sqlite:///./stock_control.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import unicodedata
from sqlalchemy import event

def strip_accents(text):
    if text is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(text)) if unicodedata.category(c) != "Mn").upper()

@event.listens_for(engine, "connect")
def set_sqlite_functions(dbapi_connection, connection_record):
    try:
        dbapi_connection.create_function("unaccent", 1, strip_accents)
    except Exception:
        pass

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def init_users():
    """
    Inicializa los usuarios por defecto en la base de datos si no existen:
    - admin / admin (Rol: ADMIN)
    - cajero / 1234 (Rol: CAJERO)
    """
    import models
    Base.metadata.create_all(bind=engine)
    db = get_db()
    try:
        admin_user = db.query(models.User).filter_by(username='admin').first()
        if not admin_user:
            admin_user = models.User(
                username='admin',
                password_hash=models.hash_password('admin'),
                full_name='Administrador General',
                role='ADMIN',
                is_active=True
            )
            db.add(admin_user)
        
        cajero_user = db.query(models.User).filter_by(username='cajero').first()
        if not cajero_user:
            cajero_user = models.User(
                username='cajero',
                password_hash=models.hash_password('1234'),
                full_name='Cajero de Turno',
                role='CAJERO',
                is_active=True
            )
            db.add(cajero_user)
            
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error inicializando usuarios: {e}")
    finally:
        db.close()


