import os
import sys
import uuid
import datetime
from decimal import Decimal, ROUND_HALF_UP

# Configurar Qt para ejecutarse de forma headless (offscreen)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Agregar skills al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills/ean13_parser/scripts')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.agents/skills/tax_calculator/scripts')))

from validator.validator import POSGuardrail
import ean13_parser
import tax_calculator

from database import SessionLocal, engine, Base
import models

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def banner(titulo):
    print("\n" + "=" * 70)
    print(f"  >>> {titulo} <<<")
    print("=" * 70)

def assert_no_float(obj, name=""):
    assert not isinstance(obj, float), f"VIOLACIÓN DE REGLA FRONTERA: {name} es de tipo 'float' ({obj}), debe ser Decimal!"

def test_todo_el_flujo():
    banner("1. VERIFICACIÓN DE ESTRUCTURA Y RESILIENCIA OFFLINE-FIRST")
    db = SessionLocal()
    
    # 1.1 Verificar campos de resiliencia en modelos clave (uuid, synced, sync_timestamp)
    print("[+] Verificando tablas transaccionales (synced, sync_timestamp, uuid)...")
    for model_cls in [models.Invoice, models.InvoiceItem, models.Payment]:
        assert hasattr(model_cls, 'synced'), f"Falta 'synced' en {model_cls.__name__}"
        assert hasattr(model_cls, 'sync_timestamp'), f"Falta 'sync_timestamp' en {model_cls.__name__}"
        assert hasattr(model_cls, 'uuid'), f"Falta 'uuid' en {model_cls.__name__}"
    print("    -> Tablas transaccionales validadas correctamente.")

    banner("2. VERIFICACIÓN DE COTIZACIONES MULTIDIVISA INMUTABLES")
    # 2.1 Asegurar monedas base
    for cur_code, cur_name, cur_sym, cur_dec, cur_base in [
        ("PYG", "Guaraní", "Gs", 0, True),
        ("USD", "Dólar Americano", "US$", 2, False),
        ("BRL", "Real Brasileño", "R$", 2, False),
        ("ARS", "Peso Argentino", "$", 2, False),
    ]:
        if not db.query(models.Currency).filter_by(code=cur_code).first():
            db.add(models.Currency(
                code=cur_code, name=cur_name, symbol=cur_sym, decimals=cur_dec, is_base=cur_base
            ))
    db.flush()

    # Asegurar tasas iniciales si no existen
    for code, val in [("USD", Decimal('7500')), ("BRL", Decimal('1500')), ("ARS", Decimal('10'))]:
        if not db.query(models.CurrencyRate).filter_by(currency_code=code, is_active=True).first():
            db.add(models.CurrencyRate(
                currency_code=code, buy_rate=val, sell_rate=val, is_active=True
            ))
    db.commit()

    # 2.2 Probar regla de inmutabilidad: un cambio de tasa genera un registro nuevo sin UPDATE destructivo
    rate_anterior = db.query(models.CurrencyRate).filter_by(currency_code="USD", is_active=True).first()
    id_anterior = rate_anterior.id
    valor_anterior = Decimal(str(rate_anterior.buy_rate))
    valor_nuevo = valor_anterior + Decimal('25')
    print(f"[+] Testeando regla de inmutabilidad al actualizar cotización USD de {valor_anterior} a {valor_nuevo}...")
    
    # Desactivar anterior e insertar nuevo
    rate_anterior.is_active = False
    rate_nuevo = models.CurrencyRate(
        currency_code="USD",
        buy_rate=valor_nuevo,
        sell_rate=valor_nuevo,
        created_at=datetime.datetime.now(),
        is_active=True
    )
    db.add(rate_nuevo)
    db.commit()

    # Verificar que el registro anterior NO fue borrado ni sobreescrito
    registro_viejo = db.query(models.CurrencyRate).filter_by(id=id_anterior).first()
    assert Decimal(str(registro_viejo.buy_rate)) == valor_anterior, "La tasa histórica fue sobreescrita destructivamente!"
    assert registro_viejo.is_active is False, "La tasa histórica debería estar inactiva"
    assert rate_nuevo.is_active is True, "La nueva tasa debería estar activa"
    print(f"    -> Inmutabilidad verificada: Registro histórico intacto ({valor_anterior}) y nueva tasa activa ({valor_nuevo}).")

    # Tasas actuales
    rates = {r.currency_code: r.buy_rate for r in db.query(models.CurrencyRate).filter_by(is_active=True).all()}
    print(f"[+] Cotizaciones activas: USD={rates.get('USD')}, BRL={rates.get('BRL')}, ARS={rates.get('ARS')}")
    assert rates.get('USD') is not None, "Debe existir cotización USD"
    assert rates.get('BRL') is not None, "Debe existir cotización BRL"
    assert rates.get('ARS') is not None, "Debe existir cotización ARS"
    for cur, val in rates.items():
        assert_no_float(val, f"Cotización {cur}")
    print("    -> Cotizaciones validadas como Decimal.")

    banner("3. VERIFICACIÓN DE IVA PARAGUAY (SKILL tax_calculator)")
    # Fórmulas de IVA Paraguay: IVA 10 = total / 11, IVA 5 = total / 21, Exentas = 0
    subtotal_10 = Decimal('110000')
    res_10 = tax_calculator.calcular_iva_linea(subtotal_10, 10)
    print(f"[+] IVA 10% sobre Gs. {subtotal_10:,.0f} -> {res_10['iva_10']:,.0f} (Esperado: 10,000)")
    assert res_10['iva_10'] == Decimal('10000')

    subtotal_5 = Decimal('105000')
    res_5 = tax_calculator.calcular_iva_linea(subtotal_5, 5)
    print(f"[+] IVA 5% sobre Gs. {subtotal_5:,.0f} -> {res_5['iva_5']:,.0f} (Esperado: 5,000)")
    assert res_5['iva_5'] == Decimal('5000')

    subtotal_exenta = Decimal('50000')
    res_ex = tax_calculator.calcular_iva_linea(subtotal_exenta, 0)
    print(f"[+] IVA Exenta sobre Gs. {subtotal_exenta:,.0f} -> {res_ex['exenta']:,.0f} (IVA: 0)")
    assert res_ex['iva_10'] == Decimal('0') and res_ex['iva_5'] == Decimal('0')

    banner("4. VERIFICACIÓN DE BALANZA IN-STORE (EAN-13)")
    # Estructura: 20 (Prefijo) + 00035 (PLU 5 digitos) + 01250 (1.250 kg) + 3 (Check)
    barcode_balanza = "2000035012503"
    parsed = ean13_parser.parse_scale_barcode(barcode_balanza, modo="peso")
    print(f"[+] Código Balanza: {barcode_balanza}")
    print(f"    -> Es Balanza: {parsed.get('es_balanza')}")
    print(f"    -> PLU: {parsed.get('plu')} | Peso: {parsed.get('peso_kg')} kg")
    assert parsed.get("es_balanza") is True
    assert parsed.get("plu") == "00035"
    assert Decimal(str(parsed.get("peso_kg"))) == Decimal('1.250')

    banner("5. CREACIÓN DE PRODUCTOS DE TEST Y LOTES FIFO")
    for old_code in ["003020", "000035"]:
        old_prod = db.query(models.Product).filter_by(art_codigo=old_code).first()
        if old_prod:
            db.query(models.ProductBatch).filter_by(product_id=old_prod.id).delete()
            db.delete(old_prod)
            db.commit()

    # 5.1 Producto Estándar
    prod_std = models.Product(
        art_codigo="003020",
        art_descri="ARROZ TEST 5KG",
        art_cbarra="7840001000012",
        art_costo=Decimal('20000'),
        art_preven=Decimal('28000'),
        art_impu=Decimal('10'),
        is_fractional=False,
        art_stkini=Decimal('50')
    )
    db.add(prod_std)
    db.flush()
    
    # Dos lotes con distintos vencimientos para testear FIFO
    b1 = models.ProductBatch(
        product_id=prod_std.id,
        lote="LOTE-VENCE-PRONTO",
        fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=10),
        stock_actual=Decimal('5')
    )
    b2 = models.ProductBatch(
        product_id=prod_std.id,
        lote="LOTE-VENCE-TARDE",
        fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=120),
        stock_actual=Decimal('45')
    )
    db.add_all([b1, b2])

    # 5.2 Producto Balanza
    prod_bal = models.Product(
        art_codigo="000035",
        art_descri="TOMATE SANTA CRUZ (KG)",
        art_cbarra=barcode_balanza,
        art_costo=Decimal('6000'),
        art_preven=Decimal('10000'), # 10,000 Gs el kg
        art_impu=Decimal('5'),
        is_fractional=True,
        art_stkini=Decimal('100')
    )
    db.add(prod_bal)
    db.flush()
    b_bal = models.ProductBatch(
        product_id=prod_bal.id,
        lote="LOTE-TOMATE-01",
        fecha_vencimiento=datetime.datetime.now() + datetime.timedelta(days=5),
        stock_actual=Decimal('100')
    )
    db.add(b_bal)

    db.commit()
    print(f"[+] Producto Estándar: {prod_std.art_descri} (Stock: {prod_std.art_stkini})")
    print(f"[+] Producto Balanza: {prod_bal.art_descri} (Stock: {prod_bal.art_stkini})")

    banner("6. TEST DE LA INTERFAZ DE USUARIO (PyQt6 MainWindow)")
    # Inicializar aplicación Qt
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    # 6.1 Verificar sesión de caja abierta
    print(f"[+] CashSession inicializada en UI: Session ID #{window.session_id}")
    assert window.session_id is not None

    # 6.2 Escanear producto estándar
    print("[+] Escaneando código de barras de Arroz: 7840001000012...")
    window.txt_codigo.setText("7840001000012")
    window.buscar_producto()
    assert window.ventas_model.rowCount() == 1
    assert window.ventas_model.items[0]['codigo'] == "003020"
    assert window.ventas_model.items[0]['cantidad'] == Decimal('1')
    assert window.ventas_model.items[0]['precio'] == Decimal('28000')

    # Cambiar cantidad del producto estándar a 3 unidades
    window.ventas_model.setData(window.ventas_model.index(0, 4), Decimal('3'))
    assert window.ventas_model.items[0]['cantidad'] == Decimal('3')
    print("    -> Cantidad actualizada a 3 unidades.")

    # 6.3 Escanear producto balanza con código EAN-13
    print(f"[+] Escaneando código de balanza: {barcode_balanza}...")
    window.txt_codigo.setText(barcode_balanza)
    window.buscar_producto()
    assert window.ventas_model.rowCount() == 2
    assert window.ventas_model.items[1]['codigo'] == "000035"
    assert window.ventas_model.items[1]['cantidad'] == Decimal('1.250')
    # Precio unitario 10,000 * 1.250 kg = 12,500 Gs
    subtotal_bal = window.ventas_model.items[1]['total']
    print(f"    -> Producto Balanza agregado: Cantidad={window.ventas_model.items[1]['cantidad']} kg, Subtotal=Gs. {subtotal_bal:,.0f}")
    assert subtotal_bal == Decimal('12500')

    # 6.4 Validar totales en la interfaz
    window.calcular_totales()
    # Total esperado: (3 * 28000) + 12500 = 84000 + 12500 = 96,500 Gs
    total_esperado = Decimal('96500')
    total_ui_pyg = Decimal(window.lbl_pyg.text().replace(',', ''))
    print(f"[+] Total Calculado en UI: Gs. {total_ui_pyg:,.0f} (Esperado: Gs. {total_esperado:,.0f})")
    assert total_ui_pyg == total_esperado
    assert Decimal(window.lbl_total_gral.text().replace(',', '')) == total_esperado

    total_usd = Decimal(window.lbl_usd.text().replace(',', ''))
    total_brl = Decimal(window.lbl_brl.text().replace(',', ''))
    total_ars = Decimal(window.lbl_ars.text().replace(',', ''))
    print(f"[+] Totales Multidivisa en Pantalla: USD {total_usd}, BRL {total_brl}, ARS {total_ars}")
    assert total_usd > Decimal('0')
    assert total_brl > Decimal('0')
    assert total_ars > Decimal('0')

    banner("7. GUARDAR VENTA MULTIDIVISA Y VALIDAR CON POSGuardrail")
    # Registrar pago mixto: 50,000 Gs en Efectivo PYG + resto en USD
    # Restante: 46,500 Gs / rate_usd
    rate_usd = rates.get('USD', Decimal('7500'))
    usd_necesario = (Decimal('46500') / rate_usd).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    pagos = [
        {
            'metodo': 'Efectivo',
            'moneda': 'PYG',
            'monto_origen': Decimal('50000'),
            'monto_pyg': Decimal('50000')
        },
        {
            'metodo': 'Efectivo',
            'moneda': 'USD',
            'monto_origen': usd_necesario,
            'monto_pyg': Decimal('46500')
        }
    ]

    # Ejecutar guardado a través del método de MainWindow (que valida con POSGuardrail y descuenta lotes)
    stock_std_antes = db.query(models.Product).filter_by(art_codigo="003020").first().art_stkini
    stock_bal_antes = db.query(models.Product).filter_by(art_codigo="000035").first().art_stkini

    window.guardar_venta_db(pagos)

    # 7.1 Verificar persistencia y descuento de stock
    db.close()
    db = SessionLocal()
    ultima_factura = db.query(models.Invoice).order_by(models.Invoice.id.desc()).first()
    assert ultima_factura is not None
    assert ultima_factura.ven_total == total_esperado
    assert len(ultima_factura.items) == 2
    assert len(ultima_factura.payments) == 2
    print(f"[+] Factura #{ultima_factura.id} registrada con éxito. Total: Gs. {ultima_factura.ven_total:,.0f}")

    # Verificar que el stock se descontó con Decimal estricto
    prod_std_despues = db.query(models.Product).filter_by(art_codigo="003020").first()
    prod_bal_despues = db.query(models.Product).filter_by(art_codigo="000035").first()
    print(f"[+] Stock Arroz: Antes={stock_std_antes} -> Después={prod_std_despues.art_stkini} (Descontado: 3)")
    print(f"[+] Stock Tomate: Antes={stock_bal_antes} -> Después={prod_bal_despues.art_stkini} (Descontado: 1.250)")
    assert prod_std_despues.art_stkini == stock_std_antes - Decimal('3')
    assert prod_bal_despues.art_stkini == stock_bal_antes - Decimal('1.250')

    # 7.2 Verificar FIFO de lotes
    # El lote que vence pronto tenía 5 unidades, se vendieron 3, deben quedar 2
    lote_pronto = db.query(models.ProductBatch).filter_by(lote="LOTE-VENCE-PRONTO").first()
    print(f"[+] Trazabilidad FIFO: Lote que vence pronto tiene stock remanente={lote_pronto.stock_actual} (Esperado: 2)")
    assert lote_pronto.stock_actual == Decimal('2')

    banner("8. ARQUEO DE CAJA Y CUADRE DE SESIÓN")
    # Verificar que los pagos quedaron asociados a la sesión activa
    pagos_sesion = db.query(models.Payment).filter_by(session_id=window.session_id).all()
    total_efectivo_pyg = sum(p.cob_monto_pyg for p in pagos_sesion)
    print(f"[+] Total registrado en sesión #{window.session_id}: Gs. {total_efectivo_pyg:,.0f}")
    assert total_efectivo_pyg >= total_esperado

    # Registrar arqueo de caja
    audit = models.CashAudit(
        session_id=window.session_id,
        moneda="PYG",
        metodo="Efectivo",
        monto_teorico=total_efectivo_pyg,
        monto_declarado=total_efectivo_pyg,
        diferencia=Decimal('0')
    )
    db.add(audit)
    
    # Cerrar sesión
    sesion_obj = db.query(models.CashSession).filter_by(id=window.session_id).first()
    sesion_obj.status = 'CLOSED'
    sesion_obj.closed_at = datetime.datetime.now()
    db.commit()
    print(f"[+] Arqueo cerrado sin diferencias. Sesión #{sesion_obj.id} cerrada a las {sesion_obj.closed_at}")

    db.close()
    window.close()

    banner("¡TODAS LAS PRUEBAS DEL FLUJO COMPLETO PASARON EXITOSAMENTE!")

if __name__ == "__main__":
    test_todo_el_flujo()
