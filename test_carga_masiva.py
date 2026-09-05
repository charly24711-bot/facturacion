import random
import sys
import datetime
from decimal import Decimal
import os

# Add skills to path so we can import POSGuardrail
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills')))
from validator.validator import POSGuardrail

from database import SessionLocal, engine, Base
import models

Base.metadata.create_all(bind=engine)

PROVEEDORES_NOMBRES = ["Distribuidora", "Importadora", "Comercial", "Logistica", "Frigorifico", "Lacteos", "Bebidas", "Agropecuaria"]
PROVEEDORES_APELLIDOS = ["Sur", "Norte", "Este", "Oeste", "Guarani", "Asuncion", "Paraguay", "Chaco", "Itaipu", "Yacyreta"]

PRODUCTOS_BASE = [
    "Arroz Blanco", "Arroz Integral", "Fideo Spaguetti", "Fideo Tirabuzon", 
    "Aceite de Soja", "Aceite de Girasol", "Azucar Blanca", "Azucar Morena", 
    "Yerba Mate Tradicional", "Yerba Mate Compuesta", "Cerveza Lata", 
    "Cerveza Botella", "Gaseosa Cola 2L", "Gaseosa Naranja 2L", 
    "Agua Mineral 1L", "Jugo en Caja 1L", "Leche Entera", "Leche Descremada",
    "Queso Paraguay", "Queso Muzzarella", "Harina 0000", "Harina Leudante",
    "Jabón en Polvo", "Detergente Líquido", "Lavandina", "Desodorante Ambiente",
    "Shampoo Anticaspa", "Acondicionador", "Crema Dental", "Jabón de Tocador"
]
PRODUCTOS_BALANZA = [
    "Tomate Lisa", "Tomate Santa Cruz", "Cebolla", "Papa", "Zanahoria", 
    "Locote Verde", "Locote Rojo", "Mandioca", "Banana", "Manzana", 
    "Naranja", "Carne Molida", "Costilla Vacuna", "Vacio", "Pechuga de Pollo", 
    "Muslo de Pollo", "Queso de Cerdo", "Fiambre Primavera", "Jamon Cocido", "Panceta"
]

def generate_mock_data():
    db = SessionLocal()
    
    print("[*] Iniciando Carga Masiva...")
    
    # 1. Crear 50 Proveedores
    print("[1/5] Creando 50 Proveedores...")
    proveedores_ids = []
    for i in range(50):
        nombre = f"{random.choice(PROVEEDORES_NOMBRES)} {random.choice(PROVEEDORES_APELLIDOS)} {i+1}"
        sup = models.Supplier(
            sup_codigo=f"PRV-{i+1000}",
            sup_nombre=nombre,
            sup_ruc=f"800{random.randint(10000,99999)}-{random.randint(0,9)}",
            sup_telefo=f"0981 {random.randint(100000, 999999)}"
        )
        db.add(sup)
        db.flush()
        proveedores_ids.append(sup.id)
        
    db.commit()
    
    # 2. Crear 100 Productos (80 normales, 20 balanza)
    print("[2/5] Creando 100 Productos...")
    productos_creados = []
    
    for i in range(80):
        nombre = f"{random.choice(PRODUCTOS_BASE)} {random.randint(10, 99) * 10}g"
        costo = Decimal(random.randint(20, 150) * 100)
        precio = costo * Decimal('1.3') # 30% margen
        prod = models.Product(
            art_codigo=f"{i+2000:06d}",
            art_descri=nombre,
            art_cbarra=f"78400000{i:04d}",
            art_costo=costo,
            art_preven=precio.quantize(Decimal('1')),
            art_impu=Decimal('10.0'),
            is_fractional=False,
            uom="Un"
        )
        db.add(prod)
        db.flush()
        productos_creados.append(prod)
        
    for i in range(20):
        nombre = f"{random.choice(PRODUCTOS_BALANZA)} (Balanza)"
        costo = Decimal(random.randint(50, 400) * 100)
        precio = costo * Decimal('1.4')
        prod = models.Product(
            art_codigo=f"{i+3000:06d}",
            art_descri=nombre,
            art_cbarra=f"20{i+3000:05d}000000",
            art_costo=costo,
            art_preven=precio.quantize(Decimal('1')),
            art_impu=Decimal('10.0'),
            is_fractional=True,
            uom="Kg"
        )
        db.add(prod)
        db.flush()
        productos_creados.append(prod)
        
    db.commit()
    
    # 3. Simular 50 Compras (1 a cada proveedor) para inyectar stock
    print("[3/5] Simulando 50 Compras de Stock...")
    for sup_id in proveedores_ids:
        # Elegir 5-15 productos al azar
        prods_compra = random.sample(productos_creados, random.randint(5, 15))
        
        compra = models.Purchase(
            com_provee=sup_id,
            com_nrofac=f"001-001-{random.randint(1000, 99999):07d}",
            com_timbra=f"12345{random.randint(100, 999)}",
            com_total=Decimal('0')
        )
        db.add(compra)
        db.flush()
        
        total_compra = Decimal('0')
        for p in prods_compra:
            qty = Decimal(f"{random.randint(10, 50)}") if not p.is_fractional else Decimal(f"{random.uniform(5, 20):.3f}")
            costo_unit = Decimal(str(p.art_costo))
            subtotal = (qty * costo_unit).quantize(Decimal('1'))
            
            pitem = models.PurchaseItem(
                cit_compra_id=compra.id,
                cit_articu=p.art_codigo,
                cit_canti=qty,
                cit_precio=costo_unit
            )
            db.add(pitem)
            total_compra += subtotal
            
            # Sumar stock y crear lote
            p.art_stkini = float(Decimal(str(p.art_stkini or 0)) + qty)
            lote = models.ProductBatch(
                product_id=p.id,
                lote=f"LT-{random.randint(1000,9999)}",
                fecha_vencimiento=datetime.datetime.utcnow() + datetime.timedelta(days=random.randint(30, 365)),
                stock_actual=qty
            )
            db.add(lote)
            
        compra.com_total = total_compra
    db.commit()
    
    # 4. Simular Ventas (Validando con POSGuardrail)
    print("[4/5] Simulando Ventas y Validando con POSGuardrail...")
    cliente_generico = db.query(models.Client).filter_by(cli_codigo="000001").first()
    if not cliente_generico:
        cliente_generico = models.Client(cli_codigo="000001", cli_nombre="CONSUMIDOR FINAL")
        db.add(cliente_generico)
        db.commit()

    for v in range(50):
        prods_venta = random.sample(productos_creados, random.randint(2, 8))
        
        # Validar ítems con Guardrail
        items_validos = []
        for p in prods_venta:
            payload = {
                "plu_code": p.art_codigo,
                "description": p.art_descri,
                "quantity": str(random.randint(1, 5)) if not p.is_fractional else f"{random.uniform(0.1, 2.5):.3f}",
                "unit_price": str(p.art_preven),
                "tax_rate": 10
            }
            status = POSGuardrail.validate_sale_item(payload)
            if status.is_valid:
                items_validos.append(status.clean_data)
            else:
                print(f"Error de validación inyectado (Simulación): {status.errors}")
                
        if not items_validos:
            continue
            
        # Generar Factura
        total_venta = sum(item["subtotal"] for item in items_validos)
        factura = models.Invoice(
            ven_tipo='FA',
            ven_codcli=cliente_generico.cli_codigo,
            ven_total=total_venta,
            ven_codmnd='PYG'
        )
        db.add(factura)
        db.flush()
        
        for item in items_validos:
            db.add(models.InvoiceItem(
                vit_numero=factura.id,
                vit_articu=item["plu_code"],
                vit_canti=item["quantity"],
                vit_precio=item["unit_price"]
            ))
            # Restar stock
            prod_db = db.query(models.Product).filter_by(art_codigo=item["plu_code"]).first()
            prod_db.art_stkini = float(Decimal(str(prod_db.art_stkini)) - item["quantity"])
            
        db.commit()

    # 5. Simular Devoluciones (Notas de Crédito)
    print("[5/5] Simulando 10 Devoluciones (Notas de Crédito)...")
    facturas_venta = db.query(models.Invoice).filter_by(ven_tipo='FA').limit(10).all()
    for fac in facturas_venta:
        if not fac.items: continue
        
        nc = models.Invoice(
            ven_tipo='NC',
            ven_codcli=fac.ven_codcli,
            ven_total=Decimal('0'),
            ven_codmnd='PYG'
        )
        db.add(nc)
        db.flush()
        
        total_nc = Decimal('0')
        # Devolver solo un item de la factura
        item_a_devolver = fac.items[0]
        
        # Guardrail para la devolucion
        payload = {
            "plu_code": item_a_devolver.vit_articu,
            "description": "Devolucion",
            "quantity": str(item_a_devolver.vit_canti),
            "unit_price": str(item_a_devolver.vit_precio),
            "tax_rate": 10
        }
        status = POSGuardrail.validate_sale_item(payload)
        
        if status.is_valid:
            db.add(models.InvoiceItem(
                vit_numero=nc.id,
                vit_articu=status.clean_data["plu_code"],
                vit_canti=status.clean_data["quantity"],
                vit_precio=status.clean_data["unit_price"]
            ))
            total_nc += status.clean_data["subtotal"]
            
            # Reintegrar stock
            prod_db = db.query(models.Product).filter_by(art_codigo=item_a_devolver.vit_articu).first()
            prod_db.art_stkini = float(Decimal(str(prod_db.art_stkini)) + status.clean_data["quantity"])
            
        nc.ven_total = total_nc
    
    db.commit()
    db.close()
    
    print("\n" + "="*50)
    print("CARGA Y TEST FINALIZADO CON ÉXITO")
    print("="*50)

if __name__ == "__main__":
    generate_mock_data()
