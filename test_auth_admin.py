import sys
from decimal import Decimal
from PyQt6.QtWidgets import QApplication
import database
import models

def test_auth_and_admin_panel():
    print("======================================================================")
    print("  >>> TEST END-TO-END: MODELO USER, LOGIN Y PANEL ADMINISTRATIVO <<<")
    print("======================================================================")
    
    # 1. Verificar inicialización de usuarios
    database.init_users()
    db = database.get_db()
    
    admin = db.query(models.User).filter_by(username="admin").first()
    assert admin is not None, "El usuario admin no fue creado"
    assert admin.role == "ADMIN", f"Rol incorrecto: {admin.role}"
    assert models.verify_password("admin", admin.password_hash), "La verificación de password falló para admin"
    print(f"[1] Usuario 'admin' verificado: ID={admin.id}, Rol={admin.role}, Nombre={admin.full_name}")
    
    cajero = db.query(models.User).filter_by(username="cajero").first()
    assert cajero is not None, "El usuario cajero no fue creado"
    assert cajero.role == "CAJERO", f"Rol incorrecto: {cajero.role}"
    assert models.verify_password("1234", cajero.password_hash), "La verificación de password falló para cajero"
    print(f"[2] Usuario 'cajero' verificado: ID={cajero.id}, Rol={cajero.role}, Nombre={cajero.full_name}")
    
    # Verificar rechazo de contraseña incorrecta
    assert not models.verify_password("wrong_password", admin.password_hash), "Falló la protección contra contraseñas incorrectas"
    print("[3] Validación criptográfica de seguridad superada exitosamente.")
    
    db.close()
    
    # 2. Inicializar QApplication para pruebas de UI
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    # 3. Probar LoginDialog
    from ui.login_dialog import LoginDialog
    login_dlg = LoginDialog(auto_login=False)
    login_dlg.txt_user.setText("admin")
    login_dlg.txt_pass.setText("admin")
    login_dlg.intentar_login()
    assert login_dlg.authenticated_user is not None, "Login falló con credenciales correctas"
    assert login_dlg.authenticated_user["username"] == "admin"
    print(f"[4] LoginDialog autenticó correctamente al usuario: {login_dlg.authenticated_user}")
    
    # 4. Probar instanciación del Panel Administrativo (AdminWindow)
    from ui.admin_window import AdminWindow
    admin_win = AdminWindow(current_user=login_dlg.authenticated_user)
    assert admin_win.windowTitle() == "Supermercado Central - Panel Administrativo & Gerencial"
    assert admin_win.current_user["role"] == "ADMIN"
    print("[5] AdminWindow inicializada con éxito y KPIs calculados.")
    
    # 5. Probar instanciación del POS con usuario logueado
    from ui.main_window import MainWindow
    pos_win = MainWindow(current_user=login_dlg.authenticated_user)
    assert pos_win.current_user["username"] == "admin"
    assert pos_win.session_id is not None
    print(f"[6] MainWindow (POS) inicializada con sesión de caja #{pos_win.session_id}")
    
    # 6. Limpieza
    admin_win.close()
    pos_win.close()
    login_dlg.close()
    
    print("\n======================================================================")
    print("  >>> TODOS LOS TESTS DE AUTENTICACIÓN Y PANEL ADMIN PASARON AL 100% <<<")
    print("======================================================================")

if __name__ == "__main__":
    test_auth_and_admin_panel()
