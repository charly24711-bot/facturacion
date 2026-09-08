from PyQt6.QtWidgets import QApplication, QSplashScreen, QProgressBar, QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor
from PyQt6.QtCore import Qt, QTimer
import sys
import time
import os
import database
from ui.admin_window import AdminWindow
from ui.main_window import MainWindow

class ProfessionalSplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.progress = 0
        
    def drawContents(self, painter):
        super().drawContents(painter)
        # Dibujar rectangulo inferior oscuro para el texto
        rect = self.rect()
        painter.fillRect(0, rect.height() - 90, rect.width(), 90, QColor(20, 25, 45, 230))
        
        # Título del sistema
        painter.setPen(QColor(255, 255, 255))
        font_title = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.drawText(15, rect.height() - 65, "TRIFRONTERA STOCK - ERP & POS")
        
        # Subtítulo / Licencia
        painter.setPen(QColor(180, 180, 180))
        font_sub = QFont("Arial", 9)
        painter.setFont(font_sub)
        painter.drawText(15, rect.height() - 45, "Versión 2.4.1 (Build 2026) | Licenciado para uso comercial")
        painter.drawText(15, rect.height() - 25, "Cargando módulos y base de datos...")
        
        # Barra de progreso simulada
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillRect(0, rect.height() - 5, rect.width(), 5, QColor(40, 40, 40))
        painter.fillRect(0, rect.height() - 5, int(rect.width() * (self.progress / 100.0)), 5, QColor(46, 204, 113))

    def update_progress(self, value):
        self.progress = value
        self.repaint()

def main():
    app = QApplication(sys.argv)
    
    # Estilo global Fusion moderno
    app.setStyle("Fusion")
    
    # Configurar el Logo e Icono de la Aplicación
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
    splash = None
    if os.path.exists(logo_path):
        app.setWindowIcon(QIcon(logo_path))
        
        # Crear imagen con algo de padding blanco si es necesario
        pixmap = QPixmap(logo_path).scaled(550, 450, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Crear base de pixmap con tamaño fijo para que la caja de texto quede bien
        base_pixmap = QPixmap(550, 500)
        base_pixmap.fill(Qt.GlobalColor.white)
        painter = QPainter(base_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        splash = ProfessionalSplashScreen(base_pixmap)
        splash.show()
        app.processEvents()
        
        # Simular carga de módulos CRM / ERP
        for i in range(1, 101):
            splash.update_progress(i)
            app.processEvents()
            time.sleep(0.015)

    # Inicializar tablas y usuarios por defecto (admin / admin y cajero / 1234)
    database.init_users()
    
    from ui.login_dialog import LoginDialog
    from PyQt6.QtWidgets import QDialog

    # Cerrar splash screen antes de mostrar el login
    if splash:
        splash.close()

    # Determinar módulo por defecto (si se usó acceso directo específico --pos)
    default_mod = 'POS' if "--pos" in sys.argv else 'ADMIN'
    
    # Abrir diálogo de Login unificado
    login = LoginDialog(auto_login=False, default_module=default_mod)
    if login.exec() == QDialog.DialogCode.Accepted:
        active_user = login.authenticated_user
        target = login.target_module
        
        # Iniciar la interfaz correspondiente
        if target == 'POS':
            window = MainWindow(current_user=active_user)
        else:
            window = AdminWindow(current_user=active_user)
            
        window.show()
        sys.exit(app.exec())
    else:
        # El usuario canceló el inicio de sesión
        sys.exit(0)
if __name__ == "__main__":
    main()
