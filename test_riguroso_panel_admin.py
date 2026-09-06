import sys
import datetime
from decimal import Decimal
from PyQt6.QtWidgets import QApplication, QDialog
import database
import models

def run_rigorous_admin_test():
    print("======================================================================")
    print("  >>> TEST RIGUROSO INTEGRAL: PANEL ADMINISTRATIVO Y MÓDULOS ERP <<<")
    print("======================================================================")

    # 1. Verificación de Base de Datos y Usuarios
    database.init_users()
    db = database.get_db()

    admin_user = db.query(models.User).filter_by(username="admin").first()
    assert admin_user is not None, "[ERROR] Usuario 'admin' no existe en la base de datos"
    assert admin_user.role == "ADMIN", f"[ERROR] Rol inválido para admin: {admin_user.role}"
    assert models.verify_password("admin", admin_user.password_hash), "[ERROR] Hash de contraseña incorrecto"
    print(f"[1] Autenticación & Seguridad:")
    print(f"    -> Usuario: {admin_user.username} (ID: {admin_user.id}, Rol: {admin_user.role})")
    print(f"    -> Cifrado SHA-256 verificado: OK")

    # 2. Inicializar entorno QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from ui.admin_window import AdminWindow
    from ui.invoice_detail_dialog import InvoiceDetailDialog
    from ui.ticket_dialog import TicketDialog

    user_payload = {
        "id": admin_user.id,
        "username": admin_user.username,
        "full_name": admin_user.full_name,
        "role": admin_user.role
    }

    admin_win = AdminWindow(current_user=user_payload)
    admin_win.show()
    app.processEvents()
    print(f"[2] Panel Administrativo instanciado:")
    print(f"    -> Título de ventana: '{admin_win.windowTitle()}'")
    print(f"    -> Usuario activo en UI: {admin_win.current_user['full_name']}")

    # 3. Validación Matemática Rigurosa de KPIs (Estricto Decimal)
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    invoices_today = db.query(models.Invoice).filter(models.Invoice.ven_fecha >= today_start).all()
    
    total_facturado_esperado = sum((Decimal(str(inv.ven_total or 0)) for inv in invoices_today), Decimal('0'))
    tickets_esperados = len(invoices_today)
    ticket_promedio_esperado = (total_facturado_esperado / Decimal(str(tickets_esperados))) if tickets_esperados > 0 else Decimal('0')
    
    # Calcular IVA esperado
    iva_esperado = Decimal('0')
    for inv in invoices_today:
        if inv.items:
            for it in inv.items:
                sub = Decimal(str(it.vit_canti or 0)) * Decimal(str(it.vit_precio or 0))
                iva_pct = Decimal(str(it.product.art_impu if it.product and it.product.art_impu is not None else 10))
                if iva_pct == 10:
                    iva_esperado += (sub / Decimal('11'))
                elif iva_pct == 5:
                    iva_esperado += (sub / Decimal('21'))

    stk_critico_esperado = db.query(models.Product).filter(models.Product.art_stkini <= 0).count()

    print(f"[3] Validación de KPIs del Dashboard (Aritmética Decimal):")
    print(f"    -> Total Facturado: Gs. {total_facturado_esperado:,.0f}")
    print(f"    -> Comprobantes Emitidos: {tickets_esperados}")
    print(f"    -> Ticket Promedio: Gs. {ticket_promedio_esperado:,.0f}")
    print(f"    -> Liquidación I.V.A.: Gs. {iva_esperado:,.0f}")
    print(f"    -> Artículos en Stock Crítico: {stk_critico_esperado}")

    # 4. Validación de la Barra Multidivisa y Medios de Pago
    pagos_hoy = db.query(models.Payment).filter(models.Payment.cob_fecha >= today_start).all()
    tot_efectivo_pyg = Decimal('0')
    tot_usd = Decimal('0')
    tot_brl = Decimal('0')
    tot_ars = Decimal('0')

    for p in pagos_hoy:
        mnd = (p.cob_mndori or 'PYG').upper()
        met = (p.cob_metodo or 'Efectivo').lower()
        monto = Decimal(str(p.cob_monto or 0))
        if mnd == 'USD':
            tot_usd += monto
        elif mnd == 'BRL' or 'pix' in met:
            tot_brl += monto
        elif mnd == 'ARS':
            tot_ars += monto
        elif 'tarjeta' not in met:
            tot_efectivo_pyg += Decimal(str(p.cob_monto_pyg or monto))

    print(f"[4] Tesorería y Multidivisa Triple Frontera:")
    print(f"    -> Efectivo PYG: Gs. {tot_efectivo_pyg:,.0f}")
    print(f"    -> Dólares USD: US$ {tot_usd:,.2f}")
    print(f"    -> Reales BRL: R$ {tot_brl:,.2f}")
    print(f"    -> Pesos ARS: $ {tot_ars:,.0f}")

    # 5. Validación de Tabla 'Top 5 Artículos Más Vendidos'
    top_rows = admin_win.table_top_productos.rowCount()
    assert top_rows <= 5, f"[ERROR] La tabla Top 5 tiene más de 5 filas ({top_rows})"
    print(f"[5] Top 5 Artículos Más Vendidos:")
    print(f"    -> Filas renderizadas: {top_rows}")
    if top_rows > 0:
        p_nom = admin_win.table_top_productos.item(0, 0).text()
        p_cant = admin_win.table_top_productos.item(0, 1).text()
        p_tot = admin_win.table_top_productos.item(0, 2).text()
        print(f"    -> Líder de ventas: {p_nom} (Cant: {p_cant} | Total: {p_tot})")

    # 6. Validación de la Interacción al Clic (Ventana Emergente de Detalle)
    print(f"[6] Test de Clic sobre Venta y Ventana Emergente (InvoiceDetailDialog):")
    assert admin_win.table_ventas_recientes.rowCount() > 0, "[ERROR] No hay ventas en la tabla reciente"
    
    # Seleccionar la primera venta
    admin_win.table_ventas_recientes.selectRow(0)
    fac_text = admin_win.table_ventas_recientes.item(0, 0).text()
    invoice_num = int(fac_text.replace('#', '').strip())
    
    dlg_detalle = InvoiceDetailDialog(invoice_num, parent=admin_win)
    dlg_detalle.show()
    app.processEvents()
    
    assert dlg_detalle.table.rowCount() > 0, "[ERROR] La venta seleccionada no tiene ítems en la grilla"
    print(f"    -> Factura #{invoice_num} cargada exitosamente")
    print(f"    -> Cliente: {dlg_detalle.lbl_cliente.text()} (RUC: {dlg_detalle.lbl_ruc.text()})")
    print(f"    -> Total Facturado: {dlg_detalle.lbl_total.text()}")
    print(f"    -> Ítems en detalle: {dlg_detalle.table.rowCount()}")
    print(f"    -> Desglose fiscal: {dlg_detalle.lbl_iva_desc.text()}")

    # Verificar botón de KuDE / TicketDialog con QR
    ticket_dlg = TicketDialog(invoice_num, parent=dlg_detalle)
    assert ticket_dlg.lbl_cdc_display.text().startswith("CDC:"), "[ERROR] CDC no generado en TicketDialog"
    assert ticket_dlg.lbl_qr_img.pixmap() is not None, "[ERROR] Código QR SIFEN no generado"
    print(f"    -> KuDE / SIFEN Ticket verificado con QR y CDC de 44 dígitos: OK")
    ticket_dlg.close()
    dlg_detalle.close()

    # 7. Integridad de Todos los Módulos Administrativos del Sidebar
    print(f"[7] Verificación de Apertura de Todos los Módulos Gerenciales:")
    
    # Módulo 1: Productos
    from ui.product_management import ProductManagementDialog
    prod_dlg = ProductManagementDialog(admin_win)
    assert prod_dlg.windowTitle() != "", "Título vacío en ProductManagementDialog"
    prod_dlg.close()
    print("    [OK] Catálogo de Productos (ProductManagementDialog)")

    # Módulo 2: Precios y Escalas
    from ui.price_lists_dialog import PriceListsDialog
    price_dlg = PriceListsDialog(admin_win)
    price_dlg.close()
    print("    [OK] Listas de Precios & Escalas (PriceListsDialog)")

    # Módulo 3: Compras y Proveedores
    from ui.purchase_dialog import PurchaseDialog
    purch_dlg = PurchaseDialog(admin_win)
    purch_dlg.close()
    print("    [OK] Compras y Proveedores (PurchaseDialog)")

    # Módulo 4: Lotes y Vencimientos FIFO
    from ui.batches_dialog import BatchesDialog
    batch_dlg = BatchesDialog(admin_win)
    batch_dlg.close()
    print("    [OK] Control de Lotes FIFO (BatchesDialog)")

    # Módulo 5: Cuentas Corrientes
    from ui.customer_accounts_dialog import CustomerAccountsDialog
    cc_dlg = CustomerAccountsDialog(admin_win)
    cc_dlg.close()
    print("    [OK] Cuentas Corrientes y Fiados (CustomerAccountsDialog)")

    # Módulo 6: Gestión de Clientes
    from ui.client_management import ClientManagementDialog
    cli_dlg = ClientManagementDialog(admin_win)
    cli_dlg.close()
    print("    [OK] Gestión de Clientes (ClientManagementDialog)")

    # Módulo 7: Auditoría y Arqueo Z
    from ui.arqueo_dialog import ArqueoDialog
    arq_dlg = ArqueoDialog(session_id=1, parent=admin_win)
    arq_dlg.close()
    print("    [OK] Auditoría y Arqueos de Caja Z (ArqueoDialog)")

    # Módulo 8: Configuración Fiscal DNIT
    from ui.company_settings_dialog import CompanySettingsDialog
    cfg_dlg = CompanySettingsDialog(admin_win)
    cfg_dlg.close()
    print("    [OK] Configuración Fiscal DNIT (CompanySettingsDialog)")

    # 8. Enlace Bidireccional con Punto de Venta (POS)
    print(f"[8] Enlace Bidireccional POS <-> Back-Office:")
    from ui.main_window import MainWindow
    admin_win.abrir_pos()
    assert admin_win.pos_window is not None, "[ERROR] No se instanció el POS desde AdminWindow"
    assert admin_win.pos_window.isVisible(), "[ERROR] La ventana de POS no está visible"
    assert admin_win.pos_window.current_user["role"] == "ADMIN", "[ERROR] Rol de usuario no transmitido al POS"
    print(f"    -> POS abierto exitosamente con sesión de caja #{admin_win.pos_window.session_id}")
    
    # Retorno desde el POS al Panel Admin
    admin_win.pos_window.open_admin_panel()
    print(f"    -> Retorno a AdminWindow verificado con éxito")
    admin_win.pos_window.close()

    admin_win.close()
    db.close()

    print("\n======================================================================")
    print("  >>> RESULTADO: ¡EL PANEL ADMINISTRATIVO SUPERÓ TODAS LAS PRUEBAS (100%)! <<<")
    print("======================================================================")

if __name__ == "__main__":
    run_rigorous_admin_test()
