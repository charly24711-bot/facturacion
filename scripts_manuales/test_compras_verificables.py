import sys
import os
from decimal import Decimal
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
import models

def registrar_compra_verificable():
    db = SessionLocal()
    print("=== INICIANDO PRUEBA DE COMPRAS Y PROVEEDORES ===")

    try:
        # 1. Crear Proveedor si no existe
        sup = db.query(models.Supplier).filter_by(sup_ruc="80023456-1").first()
        if not sup:
            sup = models.Supplier(
                sup_codigo="PROV-001",
                sup_nombre="PROVEEDORES UNIDOS S.A.",
                sup_ruc="80023456-1",
                sup_telefo="0981-123456"
            )
            db.add(sup)
            db.flush()
            print(f"[+] Proveedor registrado: {sup.sup_nombre} (RUC: {sup.sup_ruc})")
        else:
            print(f"[*] Proveedor existente: {sup.sup_nombre} (RUC: {sup.sup_ruc})")

        # 2. Tomar un producto existente (Ej: P001 - Yerba Mate)
        prod = db.query(models.Product).filter_by(art_codigo="P001").first()
        if not prod:
            print("[-] Producto de prueba 'P001' no encontrado. Asegúrese de correr seed_products.py")
            return

        stock_inicial = prod.art_stkini or Decimal('0')
        print(f"[*] Stock Inicial de '{prod.art_descri}': {stock_inicial}")

        # 3. Registrar Compra (Cabecera)
        cantidad_comprada = Decimal('50.0')
        precio_costo = Decimal('6500')
        
        compra = models.Purchase(
            com_provee=sup.id,
            com_nrofac="001-001-0001234",
            com_timbra="12345678",
            com_total=cantidad_comprada * precio_costo,
            com_fecha=datetime.datetime.now()
        )
        db.add(compra)
        db.flush()
        print(f"[+] Factura de compra #{compra.com_nrofac} registrada.")

        # 4. Registrar Detalle de Compra y Actualizar Stock
        item = models.PurchaseItem(
            cit_compra_id=compra.id,
            cit_articu=prod.art_codigo,
            cit_canti=cantidad_comprada,
            cit_precio=precio_costo
        )
        db.add(item)
        
        # 5. Aplicar lógica de actualización de Stock
        prod.art_stkini = (prod.art_stkini or Decimal('0')) + cantidad_comprada
        prod.art_costo = precio_costo  # Actualizar el costo al último precio de compra
        
        # 6. Registrar Lote FIFO (Asumimos vencimiento a 6 meses para este ejemplo)
        lote_nro = f"COMPRA-{compra.id}"
        lote = models.ProductBatch(
            product_id=prod.id,
            lote=lote_nro,
            fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=180),
            stock_actual=cantidad_comprada
        )
        db.add(lote)
        print(f"[+] Lote FIFO '{lote_nro}' ingresado al stock.")

        db.commit()

        print(f"[*] Stock Final de '{prod.art_descri}': {prod.art_stkini} (Incrementado en {cantidad_comprada})")
        print("=== PRUEBA DE COMPRA COMPLETADA CON ÉXITO ===")

    except Exception as e:
        db.rollback()
        print(f"[!] Error durante la prueba de compra: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    registrar_compra_verificable()
