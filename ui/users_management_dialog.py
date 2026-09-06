"""
ui/users_management_dialog.py
=============================
Gestión Visual de Usuarios y Cajeros.
Permite a ADMIN: crear, editar, activar/desactivar y resetear contraseña de usuarios.
Roles disponibles: ADMIN, GERENTE, CAJERO
"""

from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QComboBox, QCheckBox, QAbstractItemView, QFrame, QSplitter,
    QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from database import SessionLocal
import models


ROLE_COLORS = {
    'ADMIN':   QColor('#1565c0'),
    'GERENTE': QColor('#4a148c'),
    'CAJERO':  QColor('#2e7d32'),
}

ROLE_ICONS = {
    'ADMIN':   '🛡️',
    'GERENTE': '👔',
    'CAJERO':  '🏪',
}


class UsersManagementDialog(QDialog):
    """
    Pantalla Back-Office de Gestión de Usuarios.
    Solo accesible por role ADMIN.
    """
    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user or {'id': 1, 'username': 'admin', 'role': 'ADMIN'}
        self.selected_user_id = None
        self.setWindowTitle("👥 Gestión de Usuarios y Cajeros")
        self.resize(1000, 620)
        self.setMinimumSize(800, 500)
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)

        # Título
        lbl_title = QLabel("👥 GESTIÓN DE USUARIOS Y CAJEROS")
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #1a237e; padding: 4px 0 8px 0;")
        root.addWidget(lbl_title)

        # Splitter: tabla izq | formulario der
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        # ─── Panel Izquierdo: Tabla de usuarios ─────────────────────────────
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)

        toolbar = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar usuario...")
        self.txt_buscar.textChanged.connect(self.filtrar_tabla)
        toolbar.addWidget(self.txt_buscar, stretch=1)

        btn_nuevo = QPushButton("➕ Nuevo")
        btn_nuevo.setStyleSheet("background:#1565c0; color:white; font-weight:bold; padding:6px 12px; border-radius:4px;")
        btn_nuevo.clicked.connect(self.nuevo_usuario)
        toolbar.addWidget(btn_nuevo)

        left_layout.addLayout(toolbar)

        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["ID", "Usuario", "Nombre Completo", "Rol", "Estado"])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.selectionModel().selectionChanged.connect(self.on_user_selected)
        self.tabla.doubleClicked.connect(self.on_user_selected)
        self.tabla.setStyleSheet("""
            QTableWidget { gridline-color: #e2e8f0; font-size: 12px; }
            QHeaderView::section { background: #1a237e; color: white; font-weight: bold; padding: 5px; }
            QTableWidget::item:selected { background: #bbdefb; color: #0d47a1; }
        """)
        left_layout.addWidget(self.tabla, stretch=1)

        splitter.addWidget(left_widget)

        # ─── Panel Derecho: Formulario de edición ───────────────────────────
        right_widget = QGroupBox("✏️ Datos del Usuario")
        right_widget.setStyleSheet("""
            QGroupBox { font-weight: bold; font-size: 12px; border: 2px solid #1a237e;
                        border-radius: 6px; margin-top: 8px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #1a237e; }
        """)
        form = QGridLayout(right_widget)
        form.setSpacing(10)
        form.setContentsMargins(14, 14, 14, 14)

        lbl_s = lambda t: QLabel(t)

        form.addWidget(lbl_s("Usuario (login):"), 0, 0)
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("ej: cajero01")
        form.addWidget(self.txt_username, 0, 1)

        form.addWidget(lbl_s("Nombre Completo:"), 1, 0)
        self.txt_fullname = QLineEdit()
        form.addWidget(self.txt_fullname, 1, 1)

        form.addWidget(lbl_s("Contraseña:"), 2, 0)
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Dejar vacío para no cambiar")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addWidget(self.txt_password, 2, 1)

        form.addWidget(lbl_s("Confirmar Contraseña:"), 3, 0)
        self.txt_password2 = QLineEdit()
        self.txt_password2.setEchoMode(QLineEdit.EchoMode.Password)
        form.addWidget(self.txt_password2, 3, 1)

        form.addWidget(lbl_s("Rol:"), 4, 0)
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["🏪 CAJERO", "👔 GERENTE", "🛡️ ADMIN"])
        self.cmb_role.setStyleSheet("padding: 4px 6px; font-weight: bold;")
        form.addWidget(self.cmb_role, 4, 1)

        form.addWidget(lbl_s("Estado:"), 5, 0)
        self.chk_activo = QCheckBox("Usuario Activo")
        self.chk_activo.setChecked(True)
        form.addWidget(self.chk_activo, 5, 1)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: 1px solid #cbd5e1;")
        form.addWidget(sep, 6, 0, 1, 2)

        # Botones acción
        btn_guardar = QPushButton("💾 Guardar Usuario")
        btn_guardar.setStyleSheet("background:#2e7d32; color:white; font-weight:bold; padding:8px; border-radius:4px;")
        btn_guardar.clicked.connect(self.guardar_usuario)
        form.addWidget(btn_guardar, 7, 0, 1, 2)

        self.btn_toggle_activo = QPushButton("🔒 Desactivar")
        self.btn_toggle_activo.setStyleSheet("background:#c62828; color:white; font-weight:bold; padding:8px; border-radius:4px;")
        self.btn_toggle_activo.clicked.connect(self.toggle_activo)
        self.btn_toggle_activo.setEnabled(False)
        form.addWidget(self.btn_toggle_activo, 8, 0, 1, 2)

        self.btn_reset_pwd = QPushButton("🔑 Resetear Contraseña a '1234'")
        self.btn_reset_pwd.setStyleSheet("background:#e65100; color:white; font-weight:bold; padding:8px; border-radius:4px;")
        self.btn_reset_pwd.clicked.connect(self.resetear_password)
        self.btn_reset_pwd.setEnabled(False)
        form.addWidget(self.btn_reset_pwd, 9, 0, 1, 2)

        form.setRowStretch(10, 1)

        splitter.addWidget(right_widget)
        splitter.setSizes([560, 380])

        # Barra inferior
        bot = QHBoxLayout()
        bot.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet("padding: 7px 20px;")
        btn_cerrar.clicked.connect(self.accept)
        bot.addWidget(btn_cerrar)
        root.addLayout(bot)

    # ── Carga y filtrado ──────────────────────────────────────────────────────
    def load_users(self, filtro=""):
        db = SessionLocal()
        try:
            q = db.query(models.User)
            if filtro:
                q = q.filter(
                    models.User.username.ilike(f"%{filtro}%") |
                    models.User.full_name.ilike(f"%{filtro}%")
                )
            users = q.order_by(models.User.id).all()
            self.tabla.setRowCount(0)
            for row, u in enumerate(users):
                self.tabla.insertRow(row)
                self.tabla.setItem(row, 0, QTableWidgetItem(str(u.id)))
                self.tabla.setItem(row, 1, QTableWidgetItem(u.username))
                self.tabla.setItem(row, 2, QTableWidgetItem(u.full_name))

                role_text = f"{ROLE_ICONS.get(u.role, '')} {u.role}"
                item_role = QTableWidgetItem(role_text)
                item_role.setForeground(ROLE_COLORS.get(u.role, QColor('#333')))
                item_role.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.tabla.setItem(row, 3, item_role)

                estado = "✅ Activo" if u.is_active else "🔴 Inactivo"
                item_est = QTableWidgetItem(estado)
                item_est.setForeground(QColor('#2e7d32') if u.is_active else QColor('#c62828'))
                self.tabla.setItem(row, 4, item_est)
        finally:
            db.close()

    def filtrar_tabla(self, texto):
        self.load_users(filtro=texto)

    # ── Selección ────────────────────────────────────────────────────────────
    def on_user_selected(self, *args):
        rows = self.tabla.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        uid = int(self.tabla.item(row, 0).text())
        self.selected_user_id = uid

        db = SessionLocal()
        try:
            u = db.query(models.User).filter_by(id=uid).first()
            if u:
                self.txt_username.setText(u.username)
                self.txt_fullname.setText(u.full_name)
                self.txt_password.clear()
                self.txt_password2.clear()
                # Seleccionar rol
                role_map = {'CAJERO': 0, 'GERENTE': 1, 'ADMIN': 2}
                self.cmb_role.setCurrentIndex(role_map.get(u.role, 0))
                self.chk_activo.setChecked(u.is_active)
                self.btn_toggle_activo.setEnabled(True)
                self.btn_reset_pwd.setEnabled(True)
                lbl = "🔒 Desactivar" if u.is_active else "🔓 Activar"
                self.btn_toggle_activo.setText(lbl)
        finally:
            db.close()

    # ── Acciones ─────────────────────────────────────────────────────────────
    def nuevo_usuario(self):
        self.selected_user_id = None
        self.txt_username.clear()
        self.txt_fullname.clear()
        self.txt_password.clear()
        self.txt_password2.clear()
        self.cmb_role.setCurrentIndex(0)
        self.chk_activo.setChecked(True)
        self.btn_toggle_activo.setEnabled(False)
        self.btn_reset_pwd.setEnabled(False)
        self.txt_username.setFocus()

    def guardar_usuario(self):
        username = self.txt_username.text().strip()
        full_name = self.txt_fullname.text().strip()
        pwd = self.txt_password.text()
        pwd2 = self.txt_password2.text()
        role_text = self.cmb_role.currentText().split()[-1]  # extrae 'CAJERO' de '🏪 CAJERO'

        if not username or not full_name:
            QMessageBox.warning(self, "Datos incompletos", "Usuario y Nombre completo son requeridos.")
            return

        if self.selected_user_id is None and not pwd:
            QMessageBox.warning(self, "Contraseña requerida", "Ingrese una contraseña para el nuevo usuario.")
            return

        if pwd and pwd != pwd2:
            QMessageBox.warning(self, "Contraseñas no coinciden", "Las contraseñas no coinciden.")
            self.txt_password2.setFocus()
            return

        if pwd and len(pwd) < 4:
            QMessageBox.warning(self, "Contraseña muy corta", "La contraseña debe tener al menos 4 caracteres.")
            return

        db = SessionLocal()
        try:
            if self.selected_user_id:
                # Editar existente
                u = db.query(models.User).filter_by(id=self.selected_user_id).first()
                if not u:
                    raise ValueError("Usuario no encontrado.")
                # No permitir que el admin se degrade a sí mismo
                if u.username == 'admin' and role_text != 'ADMIN':
                    QMessageBox.warning(self, "Acción no permitida",
                                        "No puede cambiar el rol del usuario 'admin'.")
                    return
                u.username = username
                u.full_name = full_name
                u.role = role_text
                u.is_active = self.chk_activo.isChecked()
                if pwd:
                    u.password_hash = models.hash_password(pwd)
                db.commit()
                QMessageBox.information(self, "Guardado", f"Usuario '{username}' actualizado correctamente.")
            else:
                # Verificar unicidad
                existe = db.query(models.User).filter_by(username=username).first()
                if existe:
                    QMessageBox.warning(self, "Usuario duplicado",
                                        f"El usuario '{username}' ya existe.")
                    return
                nuevo = models.User(
                    username=username,
                    full_name=full_name,
                    password_hash=models.hash_password(pwd),
                    role=role_text,
                    is_active=self.chk_activo.isChecked()
                )
                db.add(nuevo)
                db.commit()
                QMessageBox.information(self, "Creado", f"Usuario '{username}' creado correctamente.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()

        self.load_users(filtro=self.txt_buscar.text())

    def toggle_activo(self):
        if not self.selected_user_id:
            return
        db = SessionLocal()
        try:
            u = db.query(models.User).filter_by(id=self.selected_user_id).first()
            if u.username == 'admin':
                QMessageBox.warning(self, "Protegido",
                                    "El usuario 'admin' no puede ser desactivado.")
                return
            u.is_active = not u.is_active
            db.commit()
            estado = "activado" if u.is_active else "desactivado"
            QMessageBox.information(self, "Estado actualizado",
                                    f"Usuario '{u.username}' {estado}.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()
        self.load_users(filtro=self.txt_buscar.text())

    def resetear_password(self):
        if not self.selected_user_id:
            return
        resp = QMessageBox.question(self, "Confirmar Reset",
                                    "¿Resetear la contraseña a '1234'?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        db = SessionLocal()
        try:
            u = db.query(models.User).filter_by(id=self.selected_user_id).first()
            u.password_hash = models.hash_password("1234")
            db.commit()
            QMessageBox.information(self, "Reset OK",
                                    f"Contraseña de '{u.username}' reseteada a '1234'.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()
