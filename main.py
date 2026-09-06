import sys
from PyQt6.QtWidgets import QApplication
import database
from ui.admin_window import AdminWindow
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Estilo global Fusion moderno
    app.setStyle("Fusion")
    
    # Inicializar tablas y usuarios por defecto (admin / admin y cajero / 1234)
    database.init_users()
    
    # Auto-login rápido como admin para acortar tiempos durante el desarrollo
    active_user = {
        "id": 1,
        "username": "admin",
        "full_name": "Administrador General",
        "role": "ADMIN"
    }
    
    # Si se especifica el parámetro '--pos' inicia directo en Caja, sino en el Panel Administrativo
    if "--pos" in sys.argv:
        window = MainWindow(current_user=active_user)
    else:
        window = AdminWindow(current_user=active_user)
        
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
