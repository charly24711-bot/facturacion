import sys
import os

# Add skills to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills')))
from ruc_validator.ruc_validator import calcular_dv_ruc

from database import SessionLocal, engine, Base
import models

def seed_default_taxpayers():
    """Siembra contribuyentes comunes y de prueba en la tabla padron_ruc."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Lista de contribuyentes frecuentes en comercio/retail paraguayo
    contribuyentes = [
        ("80001234", "DISTRIBUIDORA DEL ESTE S.A."),
        ("80015432", "SUPERMERCADOS ASUNCIÓN S.A."),
        ("80023456", "IMPORTADORA GUARANÍ S.R.L."),
        ("80034567", "AGROPECUARIA CHACO S.A."),
        ("80045678", "BEBIDAS Y GASEOSAS DEL SUR S.A."),
        ("80056789", "LOGÍSTICA TRIPLE FRONTERA S.A."),
        ("80067890", "COMERCIAL CIENTÍFICA S.R.L."),
        ("80078901", "FRIGORÍFICO CONCEPCIÓN S.A."),
        ("80089012", "RETAIL PARAGUAY S.A."),
        ("80090123", "FARMACIAS CATEDRAL S.A."),
        ("80000001", "BANCO CENTRAL DEL PARAGUAY"),
        ("80000100", "BANCO CONTINENTAL S.A.E.C.A."),
        ("80000200", "BANCO ITAÚ PARAGUAY S.A."),
        ("80000300", "TELEFONÍA CELULAR DEL PARAGUAY S.A. (TIGO)"),
        ("4455667", "CARLOS ALBERTO ROLÓN"),
        ("1234567", "JUAN PÉREZ BENÍTEZ"),
        ("2345678", "MARÍA ELENA GONZÁLEZ"),
        ("3456789", "PEDRO JAVIER MARTÍNEZ"),
        ("5678901", "ANA PATRICIA DUARTE"),
        ("6789012", "LUCAS RAMÓN AYALA"),
        ("7890123", "DESPENSA SAN CAYETANO S.R.L.")
    ]
    
    insertados = 0
    for ruc_base, razon in contribuyentes:
        dv = str(calcular_dv_ruc(ruc_base))
        existente = db.query(models.TaxpayerRegistry).filter_by(ruc=ruc_base).first()
        if not existente:
            registro = models.TaxpayerRegistry(
                ruc=ruc_base,
                dv=dv,
                razon_social=razon,
                estado='A'
            )
            db.add(registro)
            insertados += 1
            
    db.commit()
    total = db.query(models.TaxpayerRegistry).count()
    db.close()
    print(f"[+] Padrón RUC inicializado. Nuevos insertados: {insertados} | Total en Padrón: {total}")

def import_dnit_txt_file(filepath: str):
    """
    Importa un archivo oficial de la DNIT (ruc0.txt a ruc9.txt) a SQLite.
    Estructura esperada por línea (separada por '|'):
    RUC|RAZON_SOCIAL|DV|ESTADO...
    """
    if not os.path.exists(filepath):
        print(f"[-] Archivo no encontrado: {filepath}")
        return
        
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    count = 0
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                ruc_base = parts[0].strip()
                razon = parts[1].strip()
                dv = parts[2].strip()
                estado = parts[3].strip() if len(parts) > 3 else 'A'
                
                existente = db.query(models.TaxpayerRegistry).filter_by(ruc=ruc_base).first()
                if not existente:
                    db.add(models.TaxpayerRegistry(
                        ruc=ruc_base,
                        dv=dv,
                        razon_social=razon,
                        estado=estado
                    ))
                    count += 1
                if count % 5000 == 0:
                    db.commit()
                    print(f"  [+] Procesados {count} contribuyentes...")
                    
    db.commit()
    db.close()
    print(f"[+] Importación finalizada. Total cargados: {count}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        import_dnit_txt_file(sys.argv[1])
    else:
        seed_default_taxpayers()
