import os
import sys
from decimal import Decimal

# Configurar entorno offscreen
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from database import SessionLocal
import models
from ui.main_window import MainWindow

def test_flujo_presupuesto():
    app = QApplication.instance() or QApplication(sys.argv)
    
    db = SessionLocal()
    # Tomar 2 productos de prueba
    p1 = db.query(models.Product).filter(models.Product.art_stkini > 5).first()
    p2 = db.query(models.Product).filter(models.Product.art_codigo != p1.art_codigo).first()
    
    cod1, desc1, stk1_inicial, pre1 = p1.art_codigo, p1.art_descri, Decimal(str(p1.art_stkini)), Decimal(str(p1.art_preven))
    cod2, desc2, stk2_inicial, pre2 = p2.art_codigo, p2.art_descri, Decimal(str(p2.art_stkini)), Decimal(str(p2.art_preven))
    db.close()
    
    print(f"=== TEST PRESUPUESTOS (COTIZACIONES) ===")
    print(f"Producto 1: {cod1} - {desc1} | Stock Inicial: {stk1_inicial} | Precio: Gs. {pre1:,.0f}")
    print(f"Producto 2: {cod2} - {desc2} | Stock Inicial: {stk2_inicial} | Precio: Gs. {pre2:,.0f}")
    
    window = MainWindow()
    
    # 1. Agregar productos al carrito
    window.ventas_model.add_item(p1, cantidad=Decimal('2'))
    window.ventas_model.add_item(p2, cantidad=Decimal('1'))
    window.txt_cliente.setText("000002 - JUAN PEREZ")
    window.calcular_totales()
    
    total_esperado_pyg = (Decimal('2') * pre1) + (Decimal('1') * pre2)
    print(f"Total Carrito Calculado: Gs. {window.lbl_pyg.text()} (Esperado: Gs. {total_esperado_pyg:,.0f})")
    
    # 2. Generar Presupuesto [F6]
    print("\n--- PASO 1: Generando Presupuesto ---")
    window.procesar_presupuesto()
    
    # 3. Validar Presupuesto en Base de Datos
    db = SessionLocal()
    ultimo_presupuesto = db.query(models.Budget).order_by(models.Budget.id.desc()).first()
    assert ultimo_presupuesto is not None, "El presupuesto no se guardó en la BD"
    assert ultimo_presupuesto.estado == 'PENDIENTE', f"Estado incorrecto: {ultimo_presupuesto.estado}"
    assert ultimo_presupuesto.total_pyg == total_esperado_pyg, f"Total discrepante: {ultimo_presupuesto.total_pyg} vs {total_esperado_pyg}"
    assert len(ultimo_presupuesto.items) == 2, f"Cantidad de ítems incorrecta: {len(ultimo_presupuesto.items)}"
    print(f"[OK] Presupuesto guardado exitosamente: {ultimo_presupuesto.numero} - Total: Gs. {ultimo_presupuesto.total_pyg:,.0f} - Estado: {ultimo_presupuesto.estado}")
    
    # 4. Validar que el STOCK FÍSICO NO FUE DESCONTADO
    p1_check = db.query(models.Product).filter_by(art_codigo=cod1).first()
    p2_check = db.query(models.Product).filter_by(art_codigo=cod2).first()
    assert Decimal(str(p1_check.art_stkini)) == stk1_inicial, f"El stock de {cod1} se alteró incorrectamente: {p1_check.art_stkini} != {stk1_inicial}"
    assert Decimal(str(p2_check.art_stkini)) == stk2_inicial, f"El stock de {cod2} se alteró incorrectamente: {p2_check.art_stkini} != {stk2_inicial}"
    print(f"[OK] Stock intacto verificado (0 deducción): {cod1}={p1_check.art_stkini}, {cod2}={p2_check.art_stkini}")
    db.close()
    
    # 5. Limpiar carrito y Cargar Presupuesto [F5]
    print("\n--- PASO 2: Cargar Presupuesto al Carrito ---")
    window.ventas_model.clear()
    window.txt_cliente.setText("000001 - CONSUMIDOR FINAL")
    window.calcular_totales()
    assert window.ventas_model.rowCount() == 0, "El carrito no se vació"
    
    # Simular carga desde BudgetSearchDialog
    budget_dict = {
        'id': ultimo_presupuesto.id,
        'numero': ultimo_presupuesto.numero,
        'codcli': ultimo_presupuesto.codcli,
        'cliente_nombre': ultimo_presupuesto.cliente_nombre,
        'items': [
            {
                'codigo': it.articu,
                'descripcion': it.descripcion,
                'cantidad': it.canti,
                'precio': it.precio,
                'impuesto_porc': it.impuesto_porc,
                'subtotal': it.subtotal
            }
            for it in ultimo_presupuesto.items
        ]
    }
    
    db = SessionLocal()
    window.txt_cliente.setText(f"{budget_dict['codcli']} - {budget_dict['cliente_nombre']}")
    for it in budget_dict['items']:
        p_obj = db.query(models.Product).filter_by(art_codigo=it['codigo']).first()
        window.ventas_model.add_item(p_obj, cantidad=it['cantidad'], precio_override=it['precio'])
    db.close()
    window.active_budget_id = budget_dict['id']
    window.calcular_totales()
    
    assert window.ventas_model.rowCount() == 2, "Los 2 artículos del presupuesto no se cargaron al carrito"
    print(f"[OK] Carrito restaurado desde Presupuesto: {window.ventas_model.rowCount()} artículos, Cliente: {window.txt_cliente.text()}")
    
    # 6. Facturar la venta [F11] Cobrar
    print("\n--- PASO 3: Cobrar y Facturar el Presupuesto ---")
    payments = [{
        'metodo': 'Efectivo',
        'moneda': 'PYG',
        'monto_origen': total_esperado_pyg,
        'monto_pyg': total_esperado_pyg
    }]
    window.guardar_venta_db(payments)
    
    # 7. Validar estado FACTURADO y descuento de stock
    db = SessionLocal()
    presupuesto_facturado = db.query(models.Budget).filter_by(id=ultimo_presupuesto.id).first()
    assert presupuesto_facturado.estado == 'FACTURADO', f"El presupuesto debió pasar a FACTURADO, estado actual: {presupuesto_facturado.estado}"
    print(f"[OK] Presupuesto actualizado a estado: {presupuesto_facturado.estado}")
    
    p1_final = db.query(models.Product).filter_by(art_codigo=cod1).first()
    p2_final = db.query(models.Product).filter_by(art_codigo=cod2).first()
    assert Decimal(str(p1_final.art_stkini)) == stk1_inicial - Decimal('2'), f"Stock de {cod1} no se descontó en la factura"
    assert Decimal(str(p2_final.art_stkini)) == stk2_inicial - Decimal('1'), f"Stock de {cod2} no se descontó en la factura"
    print(f"[OK] Stock descontado correctamente tras la factura: {cod1}={p1_final.art_stkini} (descontó 2), {cod2}={p2_final.art_stkini} (descontó 1)")
    
    db.close()
    if hasattr(window, 'sync_worker'):
        window.sync_worker.stop()
        window.sync_worker.wait(1000)
    window.close()
    print("\n========================================================")
    print(">>> TODOS LOS TESTS DE PRESUPUESTO PASARON CON ÉXITO <<<")
    print("========================================================")

if __name__ == '__main__':
    test_flujo_presupuesto()
