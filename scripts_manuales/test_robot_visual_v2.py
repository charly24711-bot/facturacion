import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QTableView
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer
from ui.main_window import MainWindow
from decimal import Decimal

app = QApplication(sys.argv)
window = MainWindow()
window.show()

def get_button(widget, text_snippet):
    for btn in widget.findChildren(QPushButton):
        if text_snippet.lower() in btn.text().lower():
            return btn
    return None

def get_input(widget, obj_name):
    return widget.findChild(QLineEdit, obj_name)

state = 0

def tick():
    global state
    
    if state == 0:
        print("\n[Robot] === FASE 1: GESTIÓN DE ARTÍCULOS ===")
        print("[Robot] Abriendo Gestión de Artículos...")
        QTimer.singleShot(1500, state_1_product)
        window.open_product_management() # Modal
        
    elif state == 2:
        print("\n[Robot] === FASE 2: INGRESO DE STOCK ===")
        print("[Robot] Abriendo Compras...")
        QTimer.singleShot(1500, state_2_purchase)
        # Buscar el action de compras en el menu
        compras_opened = False
        for action in window.menuBar().actions():
            if action.menu():
                for sub in action.menu().actions():
                    if "compra" in sub.text().lower():
                        sub.trigger()
                        compras_opened = True
                        break
        
        if not compras_opened:
            print("[Robot] No se encontró el menú de compras. Omitiendo.")
            state = 3
            QTimer.singleShot(1000, tick)

    elif state == 3:
        print("\n[Robot] === FASE 3: OPERACIÓN DE VENTA ===")
        print("[Robot] Escribiendo código del artículo en el buscador...")
        window.txt_codigo.setFocus()
        window.txt_codigo.clear()
        QTest.keyClicks(window.txt_codigo, "ROBOT999")
        QTimer.singleShot(1000, state_3_enter)

def state_1_product():
    global state
    dialog = QApplication.activeModalWidget()
    if dialog:
        print("[Robot] Llenando datos del nuevo producto: ROBOT999...")
        txt_codigo = getattr(dialog, 'txt_codigo', None)
        txt_descri = getattr(dialog, 'txt_descri', None)
        txt_costo = getattr(dialog, 'txt_costo', None)
        txt_preven = getattr(dialog, 'txt_preven', None)
        
        if txt_codigo:
            txt_codigo.clear()
            QTest.keyClicks(txt_codigo, "ROBOT999")
        if txt_descri:
            txt_descri.clear()
            QTest.keyClicks(txt_descri, "PRODUCTO ROBOT VISUAL")
        if txt_costo:
            txt_costo.clear()
            QTest.keyClicks(txt_costo, "5000")
        if txt_preven:
            txt_preven.clear()
            QTest.keyClicks(txt_preven, "10000")
            
        btn_guardar = get_button(dialog, "guardar")
        if btn_guardar:
            print("[Robot] Presionando botón Guardar...")
            btn_guardar.click()
            
        print("[Robot] Cerrando pantalla de artículos...")
        QTimer.singleShot(1500, dialog.close)
        state = 2
        QTimer.singleShot(2000, tick)
    else:
        print("[Robot] No se pudo abrir la ventana de artículos.")
        state = 2
        QTimer.singleShot(1000, tick)

def state_2_purchase():
    global state
    dialog = QApplication.activeModalWidget()
    if dialog:
        print("[Robot] Cargando Factura de Compra...")
        
        # Llenar factura
        txt_nrofac = getattr(dialog, 'txt_nrofac', None)
        txt_timbra = getattr(dialog, 'txt_timbra', None)
        if txt_nrofac:
            txt_nrofac.clear()
            QTest.keyClicks(txt_nrofac, "001-001-9999999")
        if txt_timbra:
            txt_timbra.clear()
            QTest.keyClicks(txt_timbra, "12345678")
            
        # Simular búsqueda de artículo
        print("[Robot] Seleccionando artículo ROBOT999...")
        txt_search = getattr(dialog, 'txt_search', None)
        if txt_search:
            txt_search.clear()
            QTest.keyClicks(txt_search, "ROBOT999")
            QTest.keyClick(txt_search, Qt.Key.Key_Return)
            
        # Esperar un instante para que autocomplete rellene
        QTimer.singleShot(1000, lambda: __continue_purchase(dialog))
    else:
        print("[Robot] No se pudo abrir Compras.")
        state = 3
        QTimer.singleShot(1000, tick)
        
def __continue_purchase(dialog):
    global state
    btn_add = get_button(dialog, "agregar")
    if btn_add:
        btn_add.click()
        
    btn_guardar = get_button(dialog, "procesar")
    if btn_guardar:
        print("[Robot] Guardando compra...")
        btn_guardar.click()
        
    print("[Robot] Cerrando compras...")
    QTimer.singleShot(1500, dialog.close)
    state = 3
    QTimer.singleShot(2000, tick)

def state_3_enter():
    global state
    print("[Robot] Buscando producto...")
    QTest.keyClick(window.txt_codigo, Qt.Key.Key_Return)
    QTimer.singleShot(1500, state_3_quantity)

def state_3_quantity():
    print("[Robot] Modificando cantidad a 5 unidades...")
    widget = QApplication.focusWidget()
    if widget and hasattr(widget, 'clear'):
        widget.clear()
        QTest.keyClicks(widget, "5")
        QTest.keyClick(widget, Qt.Key.Key_Return)
    QTimer.singleShot(1500, state_3_pay)

def state_3_pay():
    print("[Robot] Presionando F2 para pagar...")
    QTimer.singleShot(1000, state_3_payment_dialog)
    QTest.keyClick(window, Qt.Key.Key_F2)

def state_3_payment_dialog():
    global state
    dialog = QApplication.activeModalWidget()
    if dialog:
        print("[Robot] Ingresando Efectivo: 100,000 Gs...")
        txt_efectivo = getattr(dialog, 'txt_efectivo', None)
        if txt_efectivo:
            txt_efectivo.clear()
            QTest.keyClicks(txt_efectivo, "100000")
            QTest.keyClick(txt_efectivo, Qt.Key.Key_Return)
            
        btn_confirm = get_button(dialog, "confirmar") or get_button(dialog, "guardar") or get_button(dialog, "facturar")
        if btn_confirm:
            print("[Robot] Confirmando Venta...")
            btn_confirm.click()
            
        QTimer.singleShot(1500, dialog.close)
        state = 4
        QTimer.singleShot(2000, state_4_arqueo)
    else:
        state = 4
        QTimer.singleShot(1500, state_4_arqueo)

def state_4_arqueo():
    global state
    print("\n[Robot] === FASE 4: CIERRE DE CAJA ===")
    print("[Robot] Abriendo Arqueo (Cierre de Turno)...")
    QTimer.singleShot(1500, interact_arqueo)
    
    # Buscar el boton de arqueo
    btn_arqueo = get_button(window, "cerrar turno")
    if btn_arqueo:
        btn_arqueo.click()
    else:
        print("[Robot] No se encontro boton de Cierre de Turno")
        QTimer.singleShot(1000, end_robot)

def interact_arqueo():
    dialog = QApplication.activeModalWidget()
    if dialog:
        print("[Robot] Cierre de turno visualizado.")
        btn_cerrar = get_button(dialog, "cierre z") or get_button(dialog, "ejecutar")
        if btn_cerrar:
            btn_cerrar.click()
        QTimer.singleShot(2000, dialog.close)
    QTimer.singleShot(2500, end_robot)

def end_robot():
    print("\n[Robot] =========================================")
    print("[Robot] SIMULACIÓN VISUAL DEL FLUJO TERMINADA CON ÉXITO")
    print("[Robot] =========================================")
    window.close()
    app.quit()

QTimer.singleShot(1500, tick)
sys.exit(app.exec())
