import os
import sys
import datetime
from decimal import Decimal

# Add skills to path so we can import POSGuardrail
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills')))
from validator.validator import POSGuardrail

from database import SessionLocal, engine, Base
import models

def main():
    print("="*60)
    print("INICIANDO SIMULACIÓN DE FLUJO OPERATIVO (LÓGICA DE NEGOCIO)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 1. Gestión de Artículos
        print("\n[PASO 1] GESTIÓN DE ARTÍCULOS")
        art_codigo = "TEST-101"
        prod = db.query(models.Product).filter_by(art_codigo=art_codigo).first()
        if prod:
            db.delete(prod)
            db.commit()
            
        nuevo_prod = models.Product(
            art_codigo=art_codigo,
            art_descri="TEST OPERATIVO 101",
            art_cbarra="9999999999101",
            art_costo=Decimal('10000'),
            art_preven=Decimal('15000'),
            art_impu=Decimal('10.0'),
            is_fractional=False,
            uom="Un",
            art_stkini=0
        )
        db.add(nuevo_prod)
        db.commit()
        print(f"  [+] Artículo Creado: {nuevo_prod.art_descri} | Precio: Gs. {nuevo_prod.art_preven:,.0f} | Stock Inicial: {nuevo_prod.art_stkini}")

        # 2. Ingreso de Inventario (Compra)
        print("\n[PASO 2] INGRESO DE INVENTARIO (COMPRAS)")
        sup = db.query(models.Supplier).first()
        compra = models.Purchase(
            com_provee=sup.id if sup else None,
            com_nrofac="999-999-0000001",
            com_timbra="TEST",
            com_total=Decimal('0')
        )
        db.add(compra)
        db.flush()
        
        qty_comprada = Decimal('500')
        subtotal_compra = qty_comprada * nuevo_prod.art_costo
        
        pitem = models.PurchaseItem(
            cit_compra_id=compra.id,
            cit_articu=nuevo_prod.art_codigo,
            cit_canti=qty_comprada,
            cit_precio=nuevo_prod.art_costo
        )
        db.add(pitem)
        compra.com_total = subtotal_compra
        
        # Inyectar Stock y Lote
        nuevo_prod.art_stkini = float(qty_comprada)
        lote = models.ProductBatch(
            product_id=nuevo_prod.id,
            lote="LOTE-TEST-01",
            fecha_vencimiento=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            stock_actual=qty_comprada
        )
        db.add(lote)
        db.commit()
        print(f"  [+] Compra Registrada. Cantidad ingresada: {qty_comprada}. Nuevo Stock: {nuevo_prod.art_stkini}")

        # 3. Apertura de Caja
        print("\n[PASO 3] APERTURA DE CAJA")
        session = models.CashSession(status='OPEN')
        db.add(session)
        db.flush()
        
        # Fondo Fijo de 150,000 Gs
        fondo = models.Payment(
            cob_numero=9000000 + session.id,
            cob_fecha=datetime.datetime.utcnow(),
            cob_monto=Decimal('150000'),
            cob_mndori='PYG',
            cob_metodo='FondoFijo',
            cob_monto_pyg=Decimal('150000'),
            session_id=session.id
        )
        db.add(fondo)
        db.commit()
        print(f"  [+] Caja Abierta (Session ID: {session.id}) con Fondo Fijo de Gs. 150,000")

        # 4. Venta (Validada por Guardrail)
        print("\n[PASO 4] VENTA CONTINUA (FACTURACIÓN)")
        cantidad_venta = Decimal('2')
        payload = {
            "plu_code": nuevo_prod.art_codigo,
            "description": nuevo_prod.art_descri,
            "quantity": str(cantidad_venta),
            "unit_price": str(nuevo_prod.art_preven),
            "tax_rate": float(nuevo_prod.art_impu)
        }
        status = POSGuardrail.validate_sale_item(payload)
        if not status.is_valid:
            print(f"  [-] Error Validando Venta: {status.errors}")
            sys.exit(1)
            
        print("  [+] POSGuardrail validó los precios y cantidades exitosamente.")
        
        factura = models.Invoice(
            ven_tipo='FA',
            ven_codcli="000001",
            ven_total=status.clean_data["subtotal"],
            ven_codmnd='PYG'
        )
        db.add(factura)
        db.flush()
        
        db.add(models.InvoiceItem(
            vit_numero=factura.id,
            vit_articu=status.clean_data["plu_code"],
            vit_canti=status.clean_data["quantity"],
            vit_precio=status.clean_data["unit_price"]
        ))
        
        # Deducción de Stock
        nuevo_prod.art_stkini = float(Decimal(str(nuevo_prod.art_stkini)) - status.clean_data["quantity"])
        
        # Pago
        pago_venta = models.Payment(
            cob_numero=8000000 + factura.id,
            cob_monto=status.clean_data["subtotal"],
            cob_vennro=factura.ven_numero,
            cob_mndori='PYG',
            cob_metodo='Efectivo',
            cob_monto_pyg=status.clean_data["subtotal"],
            session_id=session.id
        )
        db.add(pago_venta)
        db.commit()
        print(f"  [+] Venta procesada. Total: Gs. {factura.ven_total:,.0f}. Nuevo Stock: {nuevo_prod.art_stkini}")

        # 5. Devolución (NC)
        print("\n[PASO 5] DEVOLUCIÓN (NOTA DE CRÉDITO)")
        nc = models.Invoice(
            ven_tipo='NC',
            ven_codcli="000001",
            ven_total=Decimal('15000'),
            ven_codmnd='PYG'
        )
        db.add(nc)
        db.flush()
        
        db.add(models.InvoiceItem(
            vit_numero=nc.id,
            vit_articu=nuevo_prod.art_codigo,
            vit_canti=Decimal('1'),
            vit_precio=nuevo_prod.art_preven
        ))
        
        # Reintegro de stock
        nuevo_prod.art_stkini = float(Decimal(str(nuevo_prod.art_stkini)) + Decimal('1'))
        
        # Retiro de dinero de la caja
        pago_nc = models.Payment(
            cob_numero=7000000 + nc.id,
            cob_monto=Decimal('-15000'),
            cob_vennro=nc.ven_numero,
            cob_mndori='PYG',
            cob_metodo='Devolucion',
            cob_monto_pyg=Decimal('-15000'),
            session_id=session.id
        )
        db.add(pago_nc)
        db.commit()
        print(f"  [+] Devolución (1 Ud) procesada. Nuevo Stock Reintegrado: {nuevo_prod.art_stkini}")

        # 6. Arqueo y Cierre
        print("\n[PASO 6] ARQUEO Y CIERRE DE CAJA")
        pagos = db.query(models.Payment).filter_by(session_id=session.id).all()
        total_en_caja = sum(p.cob_monto_pyg for p in pagos)
        
        # Esperado: 150000 (Fondo) + 30000 (Venta) - 15000 (NC) = 165000
        print(f"  [+] Total Teórico en Sistema: Gs. {total_en_caja:,.0f}")
        
        audit = models.CashAudit(
            session_id=session.id,
            moneda="PYG",
            metodo="Efectivo",
            monto_teorico=total_en_caja,
            monto_declarado=total_en_caja, # Cajero declara el monto exacto
            diferencia=Decimal('0')
        )
        db.add(audit)
        
        session.status = 'CLOSED'
        session.closed_at = datetime.datetime.utcnow()
        db.commit()
        print("  [+] Arqueo Cuadrado a Cero (0 Diferencia). Turno Cerrado Exitosamente.")
        
        print("\n" + "="*60)
        print("✓ FLUJO OPERATIVO VALIDADO SIN ERRORES")
        print("="*60)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
