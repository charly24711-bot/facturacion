from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QHBoxLayout, QMessageBox, QComboBox, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import SessionLocal
import models

class CompanySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de la Empresa")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("Datos del Membrete y Operativa")
        lbl_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(lbl_title)
        
        form_layout = QFormLayout()
        
        self.txt_nombre = QLineEdit()
        self.txt_ruc = QLineEdit()
        self.txt_direccion = QLineEdit()
        self.txt_telefono = QLineEdit()
        
        self.combo_rubro = QComboBox()
        self.combo_rubro.addItems(["Comercio", "Restaurante", "Servicios"])
        
        form_layout.addRow("Nombre / Razón Social:", self.txt_nombre)
        form_layout.addRow("R.U.C.:", self.txt_ruc)
        form_layout.addRow("Dirección:", self.txt_direccion)
        form_layout.addRow("Teléfono:", self.txt_telefono)
        form_layout.addRow("Rubro Operativo:", self.combo_rubro)
        
        layout.addLayout(form_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_guardar = QPushButton("Guardar Configuración")
        btn_guardar.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 5px;")
        btn_guardar.clicked.connect(self.guardar_datos)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        self.cargar_datos()
        
    def cargar_datos(self):
        db = SessionLocal()
        settings = db.query(models.CompanySettings).first()
        if settings:
            self.txt_nombre.setText(settings.nombre)
            self.txt_ruc.setText(settings.ruc)
            self.txt_direccion.setText(settings.direccion)
            self.txt_telefono.setText(settings.telefono)
            self.combo_rubro.setCurrentText(settings.tipo_negocio)
        db.close()
        
    def guardar_datos(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El Nombre de la Empresa es obligatorio.")
            return
            
        db = SessionLocal()
        try:
            settings = db.query(models.CompanySettings).first()
            if not settings:
                settings = models.CompanySettings()
                db.add(settings)
                
            settings.nombre = nombre
            settings.ruc = self.txt_ruc.text()
            settings.direccion = self.txt_direccion.text()
            settings.telefono = self.txt_telefono.text()
            settings.tipo_negocio = self.combo_rubro.currentText()
            
            db.commit()
            QMessageBox.information(self, "Éxito", "Configuración de Empresa guardada correctamente.\nEl sistema adaptará sus módulos según el rubro seleccionado (Próximamente).")
            self.accept()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()
