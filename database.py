from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Cambiamos a SQLite temporalmente para facilitar el desarrollo sin depender de un servidor MySQL activo.
# Luego se puede cambiar a: "mysql+pymysql://root:password@localhost/stock_control"
DATABASE_URL = "sqlite:///./stock_control.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass
