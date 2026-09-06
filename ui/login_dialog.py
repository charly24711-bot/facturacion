import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QMessageBox, QFrame, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap
import database
import models

class LoginDialog(QDialog):
    """
    Diálogo de autenticación de usuarios.
    Permite acceso segregado por rol:
    - ROL 'ADMIN'/'GERENTE': Acceso a Panel Administrativo o POS.
    - ROL 'CAJERO': Acceso directo y exclusivo a POS.
    """
    def __init__(self, parent=None, auto_login=True, default_module='ADMIN'):
        super().__init__(parent)
        self.setWindowTitle("Acceso al Sistema - Supermercado Triple Frontera")
        self.setFixedSize(440, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.authenticated_user = None
        self.target_module = default_module # 'ADMIN' or 'POS'
        self.auto_login_requested = auto_login
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        
        # Header / Branding
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        lbl_brand = QLabel("SUPERMERCADO TRIPLE FRONTERA")
        lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_brand.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        lbl_brand.setStyleSheet("color: #1a237e; letter-spacing: 1px;")
        
        lbl_sub = QLabel("Control de Acceso y Gestión Integral")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setFont(QFont("Arial", 9))
        lbl_sub.setStyleSheet("color: #555555;")
        
        header_layout.addWidget(lbl_brand)
        header_layout.addWidget(lbl_sub)
        layout.addLayout(header_layout)
        
        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #e0e0e0; margin: 4px 0;")
        layout.addWidget(sep)
        
        # Formulario
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        lbl_user = QLabel("Usuario:")
        lbl_user.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.txt_user = QLineEdit("admin")
        self.txt_user.setPlaceholderText("Nombre de usuario")
        self.txt_user.setFont(QFont("Arial", 11))
        self.txt_user.setStyleSheet("""
            QLineEdit {
                border: 1px solid #b0bec5;
                border-radius: 5px;
                padding: 8px 10px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border: 2px solid #1976d2;
                background-color: #ffffff;
            }
        """)
        
        lbl_pass = QLabel("Contraseña / PIN:")
        lbl_pass.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.txt_pass = QLineEdit("admin")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Contraseña o PIN de caja")
        self.txt_pass.setFont(QFont("Arial", 11))
        self.txt_pass.setStyleSheet("""
            QLineEdit {
                border: 1px solid #b0bec5;
                border-radius: 5px;
                padding: 8px 10px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border: 2px solid #1976d2;
                background-color: #ffffff;
            }
        """)
        
        form_layout.addWidget(lbl_user)
        form_layout.addWidget(self.txt_user)
        form_layout.addWidget(lbl_pass)
        form_layout.addWidget(self.txt_pass)
        layout.addLayout(form_layout)
        
        # Selección de destino
        lbl_dest = QLabel("Ingresar a:")
        lbl_dest.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        lbl_dest.setStyleSheet("color: #424242; margin-top: 4px;")
        layout.addWidget(lbl_dest)
        
        dest_layout = QHBoxLayout()
        self.rb_admin = QRadioButton("🏢 Panel Admin")
        self.rb_admin.setFont(QFont("Arial", 10))
        self.rb_admin.setChecked(self.target_module == 'ADMIN')
        
        self.rb_pos = QRadioButton("🛒 Caja POS")
        self.rb_pos.setFont(QFont("Arial", 10))
        self.rb_pos.setChecked(self.target_module == 'POS')
        
        self.group_dest = QButtonGroup(self)
        self.group_dest.addButton(self.rb_admin, 1)
        self.group_dest.addButton(self.rb_pos, 2)
        
        dest_layout.addWidget(self.rb_admin)
        dest_layout.addWidget(self.rb_pos)
        layout.addLayout(dest_layout)
        
        # Checkbox auto-login
        self.chk_autologin = QCheckBox("Modo rápido (Auto-Login automático activado)")
        self.chk_autologin.setChecked(self.auto_login_requested)
        self.chk_autologin.setFont(QFont("Arial", 9))
        self.chk_autologin.setStyleSheet("color: #2e7d32; font-weight: bold;")
        layout.addWidget(self.chk_autologin)
        
        # Mensaje de error / estado
        self.lbl_error = QLabel("")
        self.lbl_error.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.lbl_error.setStyleSheet("color: #d32f2f;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_error)
        
        # Botones de acción
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        self.btn_login = QPushButton("🔐 Iniciar Sesión")
        self.btn_login.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.btn_login.clicked.connect(self.intentar_login)
        
        self.btn_salir = QPushButton("Salir")
        self.btn_salir.setFont(QFont("Arial", 9))
        self.btn_salir.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #333333;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #bdbdbd;
            }
        """)
        self.btn_salir.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_salir)
        layout.addLayout(btn_layout)
        
        # Conexiones ENTER
        self.txt_user.returnPressed.connect(self.txt_pass.setFocus)
        self.txt_pass.returnPressed.connect(self.intentar_login)
        
    def intentar_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text().strip()
        
        if not username:
            self.lbl_error.setText("Ingrese su nombre de usuario.")
            self.txt_user.setFocus()
            return
            
        db = database.get_db()
        try:
            user = db.query(models.User).filter_by(username=username, is_active=True).first()
            if not user:
                self.lbl_error.setText("Usuario inexistente o inactivo.")
                return
                
            if not models.verify_password(password, user.password_hash):
                self.lbl_error.setText("Contraseña incorrecta.")
                self.txt_pass.selectAll()
                self.txt_pass.setFocus()
                return
                
            # Usuario autenticado exitosamente
            self.authenticated_user = {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role
            }
            
            # Determinar módulo destino
            if self.rb_pos.isChecked() or user.role == 'CAJERO':
                self.target_module = 'POS'
            else:
                self.target_module = 'ADMIN'
                
            self.accept()
        except Exception as e:
            self.lbl_error.setText(f"Error al conectar con la base de datos: {e}")
        finally:
            db.close()
