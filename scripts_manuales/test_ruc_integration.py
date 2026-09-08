import os
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.append(os.path.abspath('.agents/skills'))
from ruc_validator.ruc_validator import calcular_dv_ruc, formatear_ruc, validar_ruc

# 1. Test unitario Módulo 11 DNIT
print('[1] Testeando Módulo 11 DNIT...')
dv_80001234 = calcular_dv_ruc('80001234')
assert dv_80001234 == 8, f"Esperado 8, obtenido {dv_80001234}"

dv_4455667 = calcular_dv_ruc('4455667')
assert dv_4455667 == 5, f"Esperado 5, obtenido {dv_4455667}"

assert formatear_ruc('80001234') == '80001234-8'
assert validar_ruc('80001234-8')[0] is True
assert validar_ruc('80001234-5')[0] is False
print('    -> Algoritmo Módulo 11 100% verificado.')

# 2. Test UI Ficha de Clientes (Autocompletado RUC y CI)
print('[2] Testeando Ficha de Clientes ABM...')
from PyQt6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = lambda *a, **k: None
QMessageBox.warning = lambda *a, **k: None

from ui.client_management import ClientManagementDialog
app = QApplication.instance() or QApplication([])
dlg = ClientManagementDialog()

# Probar autocompletado por RUC
dlg.txt_ruc.setText('80001234')
dlg.on_ruc_changed()
print('    -> RUC tras consulta:', dlg.txt_ruc.text())
print('    -> Nombre autocompletado:', dlg.txt_nombre.text())
print('    -> Status:', dlg.lbl_ruc_status.text())
assert dlg.txt_ruc.text() == '80001234-8'
assert 'DISTRIBUIDORA DEL ESTE' in dlg.txt_nombre.text()

# Probar autocompletado por CI
dlg.clear_form()
dlg.txt_ci.setText('4455667')
dlg.on_ci_changed()
print('    -> RUC desde CI:', dlg.txt_ruc.text())
print('    -> Nombre desde CI:', dlg.txt_nombre.text())
assert dlg.txt_ruc.text() == '4455667-5'
assert 'CARLOS ALBERTO' in dlg.txt_nombre.text()

# 3. Test Búsqueda y Selección en Factura [F8] (ClientSearchDialog)
print('[3] Testeando Búsqueda de Clientes [F8] con Padrón DNIT...')
from ui.client_search_dialog import ClientSearchDialog
search_dlg = ClientSearchDialog()
search_dlg.txt_search.setText('frigorifico')
search_dlg.search_clients()
print('    -> Filas encontradas para "frigorifico":', search_dlg.table.rowCount())
assert search_dlg.table.rowCount() > 0

# Simular doble clic en el primer resultado del padrón
search_dlg.select_client(search_dlg.table.item(0, 0))
assert search_dlg.selected_client is not None
print('    -> Cliente seleccionado/creado al vuelo:', search_dlg.selected_client.cli_codigo, search_dlg.selected_client.cli_nombre)

# 4. Test RUC específico del usuario: 3200967-4
print('[4] Testeando RUC 3200967-4...')
dlg.clear_form()
dlg.txt_ruc.setText('3200967-4')
dlg.on_ruc_changed()
print('    -> RUC:', dlg.txt_ruc.text())
print('    -> Nombre obtenido:', dlg.txt_nombre.text())
print('    -> Status:', dlg.lbl_ruc_status.text())
assert dlg.txt_ruc.text() == '3200967-4'
assert 'BENITEZ' in dlg.txt_nombre.text() or 'IRMINA' in dlg.txt_nombre.text()

# 5. Test RUC sin guión ingresado por el usuario: 8063338
print('[5] Testeando RUC pegado sin guion 8063338...')
dlg.clear_form()
dlg.txt_ruc.setText('8063338')
dlg.on_ruc_changed()
print('    -> RUC normalizado:', dlg.txt_ruc.text())
print('    -> Nombre obtenido:', dlg.txt_nombre.text())
print('    -> Status:', dlg.lbl_ruc_status.text())
assert dlg.txt_ruc.text() == '806333-8'
assert 'MERCEDES' in dlg.txt_nombre.text() or 'AMANCIA' in dlg.txt_nombre.text()

print('\n[OK] ¡TODAS LAS PRUEBAS DEL PADRÓN RUC PASARON EXITOSAMENTE!')
