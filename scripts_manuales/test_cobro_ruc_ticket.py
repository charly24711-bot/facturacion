import os
import sys
from decimal import Decimal

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PyQt6.QtWidgets import QApplication, QMessageBox

# Silenciar mensajes modales
QMessageBox.information = lambda *a, **k: None
QMessageBox.warning = lambda *a, **k: None
QMessageBox.critical = lambda *a, **k: None

app = QApplication.instance() or QApplication([])

from database import SessionLocal
import models
from ui.payment_dialog import PaymentDialog
from ui.ticket_dialog import TicketDialog

print("=" * 70)
print("  >>> TEST END-TO-END: COBRO CON RUC EN CAJA Y TICKET CON IVA <<<")
print("=" * 70)

db = SessionLocal()

# 1. Asegurar sesión de caja activa
session = db.query(models.CashSession).filter_by(status='OPEN').first()
if not session:
    session = models.CashSession(status='OPEN')
    db.add(session)
    db.commit()
    db.refresh(session)
print(f"[1] Sesión de caja activa: #{session.id}")

# 2. Simular apertura del PaymentDialog con un total de Gs. 96,500
totals = {'PYG': 96500.0, 'USD': 15.95, 'BRL': 77.20, 'ARS': 24125.0}
dialog = PaymentDialog(totals, client=None)

# 3. El cajero pregunta el RUC al cliente e ingresa '80001234'
print("[2] Cajero ingresa RUC '80001234'...")
dialog.txt_cliente_ruc.setText("80001234")
dialog.consultar_ruc_cliente()

print("    -> RUC normalizado:", dialog.txt_cliente_ruc.text())
print("    -> Razón Social auto-completada:", dialog.txt_cliente_nombre.text())
print("    -> Estado Padrón:", dialog.lbl_cliente_status.text())

assert dialog.txt_cliente_ruc.text() == "80001234-8", f"Esperado 80001234-8, obtenido {dialog.txt_cliente_ruc.text()}"
assert "DISTRIBUIDORA DEL ESTE" in dialog.txt_cliente_nombre.text()
assert "DNIT" in dialog.lbl_cliente_status.text() or "Registrado" in dialog.lbl_cliente_status.text()

# 4. El cliente paga en efectivo Gs. 100,000
print("[3] Registrando pago en efectivo Gs. 100,000...")
dialog.combo_moneda.setCurrentText("PYG")
dialog.combo_metodo.setCurrentText("Efectivo")
dialog.txt_monto.setText("100000")
dialog.agregar_pago()

print("    -> Total recibido:", dialog.lbl_recibido.text())
print("    -> Vuelto a entregar:", dialog.lbl_vuelto_pyg.text())
assert dialog.btn_cobrar.isEnabled() is True
assert dialog.lbl_vuelto_pyg.text() == "3,500"

# 5. Confirmar cobro
print("[4] Procesando confirmación de cobro...")
dialog.procesar_cobro()
assert dialog.payment_successful is True
assert dialog.selected_client is not None
print(f"    -> Cliente asignado a la venta: {dialog.selected_client.cli_codigo} - {dialog.selected_client.cli_nombre} (RUC: {dialog.selected_client.cli_ruc})")

# 6. Guardar Factura en base de datos vinculada a este cliente
cliente_venta = dialog.selected_client
nueva_venta = models.Invoice(
    ven_codcli=cliente_venta.cli_codigo,
    ven_total=Decimal("96500"),
    ven_codmnd='PYG'
)
db.add(nueva_venta)
db.flush()

# Agregar detalle de factura (Arroz IVA 10% y Tomate IVA 5%)
prod_arroz = db.query(models.Product).filter_by(art_codigo="000001").first()
prod_tomate = db.query(models.Product).filter_by(art_codigo="000035").first()

item1 = models.InvoiceItem(
    vit_numero=nueva_venta.ven_numero,
    vit_articu=prod_arroz.art_codigo if prod_arroz else "000001",
    vit_canti=Decimal("3"),
    vit_precio=Decimal("28000") # 84,000 (IVA 10%)
)
item2 = models.InvoiceItem(
    vit_numero=nueva_venta.ven_numero,
    vit_articu=prod_tomate.art_codigo if prod_tomate else "000035",
    vit_canti=Decimal("1.250"),
    vit_precio=Decimal("10000") # 12,500 (IVA 5%)
)
db.add(item1)
db.add(item2)

# Guardar pago
pago = models.Payment(
    cob_monto=Decimal("100000"),
    cob_monto_pyg=Decimal("100000"),
    cob_vennro=nueva_venta.ven_numero,
    cob_mndori='PYG',
    cob_metodo='Efectivo',
    session_id=session.id
)
db.add(pago)
db.commit()
print(f"[5] Factura #{nueva_venta.id} (VEN_NUMERO: {nueva_venta.ven_numero}) guardada exitosamente.")

# 7. Generar Ticket con IVA
print("[6] Generando Ticket / Factura con IVA...")
ticket_dlg = TicketDialog(nueva_venta.id)
ticket_text = ticket_dlg.ticket_text

print("\n--- CONTENIDO DEL TICKET GENERADO ---")
print(ticket_text)
print("-------------------------------------\n")

# Verificaciones en el ticket
assert f"FACTURA/TICKET : #{nueva_venta.id:06d}" in ticket_text
assert "CLIENTE : DISTRIBUIDORA DEL ESTE" in ticket_text
assert "RUC/CI  : 80001234-8" in ticket_text
assert "TOTAL A PAGAR:" in ticket_text and "96.500" in ticket_text
assert "VUELTO ENTREGADO:" in ticket_text and "3.500" in ticket_text
assert "LIQUIDACIÓN DEL I.V.A." in ticket_text
assert "Gravadas 10%:" in ticket_text and "76.364" in ticket_text
assert "IVA 10%:" in ticket_text and "7.636" in ticket_text
assert "Gravadas 5%:" in ticket_text and "11.905" in ticket_text
assert "IVA 5%:" in ticket_text and "595" in ticket_text
assert "TOTAL I.V.A.:" in ticket_text and "8.231" in ticket_text

db.close()

print("[OK] ¡EL FLUJO COMPLETO DE COBRO CON RUC Y EMISIÓN DE TICKET CON IVA FUNCIONA A LA PERFECCIÓN!")
