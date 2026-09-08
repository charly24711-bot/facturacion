from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QCheckBox, QPushButton, QLabel, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_manager import ConfigManager

class ConfiguracionEntornoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configuración de Entorno (Perfiles)")
        self.resize(600, 450)
        
        self.setup_ui()
        self.load_current_config()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- PERFILES RÁPIDOS ---
        grp_perfiles = QGroupBox("Perfiles Rápidos (Presets)")
        h_perfiles = QHBoxLayout()
        
        btn_minimarket = QPushButton("🏪 Minimarket Básico")
        btn_minimarket.setToolTip("Desactiva multimoneda, canales de precio, presupuestos y lotes.")
        btn_minimarket.clicked.connect(lambda: self.apply_preset(multicurrency=False, price_channels=False, fifo=False, budgets=False, strict_cash=False))
        
        btn_frontera = QPushButton("🌍 Minimarket Frontera")
        btn_frontera.setToolTip("Igual a Minimarket pero con panel multimoneda.")
        btn_frontera.clicked.connect(lambda: self.apply_preset(multicurrency=True, price_channels=False, fifo=False, budgets=False, strict_cash=False))
        
        btn_super = QPushButton("🛒 Supermercado Completo")
        btn_super.setToolTip("Activa todos los módulos del ERP.")
        btn_super.clicked.connect(lambda: self.apply_preset(multicurrency=True, price_channels=True, fifo=True, budgets=True, strict_cash=True))
        
        h_perfiles.addWidget(btn_minimarket)
        h_perfiles.addWidget(btn_frontera)
        h_perfiles.addWidget(btn_super)
        grp_perfiles.setLayout(h_perfiles)
        main_layout.addWidget(grp_perfiles)
        
        # --- MÓDULO POS / CAJA ---
        grp_pos = QGroupBox("Módulo POS / Caja")
        v_pos = QVBoxLayout()
        self.chk_multicurrency = QCheckBox("Habilitar Panel Multimoneda (PYG, USD, BRL, ARS)")
        self.chk_price_channels = QCheckBox("Habilitar Canales de Precio (Mayorista / Minorista)")
        self.chk_budgets = QCheckBox("Habilitar Presupuestos y Cotizaciones")
        self.chk_strict_cash = QCheckBox("Auditoría Z Rigurosa (Obliga a arqueo de caja para salir)")
        
        v_pos.addWidget(self.chk_multicurrency)
        v_pos.addWidget(self.chk_price_channels)
        v_pos.addWidget(self.chk_budgets)
        v_pos.addWidget(self.chk_strict_cash)
        grp_pos.setLayout(v_pos)
        main_layout.addWidget(grp_pos)
        
        # --- MÓDULO INVENTARIO Y BACK-OFFICE ---
        grp_inv = QGroupBox("Módulo Inventario y Compras")
        v_inv = QVBoxLayout()
        self.chk_fifo = QCheckBox("Control de Lotes FIFO y Fechas de Vencimiento obligatorios")
        
        v_inv.addWidget(self.chk_fifo)
        grp_inv.setLayout(v_inv)
        main_layout.addWidget(grp_inv)
        
        # --- BOTONES GUARDAR/CANCELAR ---
        h_buttons = QHBoxLayout()
        btn_save = QPushButton("💾 Guardar Configuración")
        btn_save.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 10px;")
        btn_save.clicked.connect(self.save_config)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        h_buttons.addStretch()
        h_buttons.addWidget(btn_cancel)
        h_buttons.addWidget(btn_save)
        
        main_layout.addStretch()
        main_layout.addLayout(h_buttons)
        
    def load_current_config(self):
        # Cargar de ConfigManager (en memoria)
        self.chk_multicurrency.setChecked(ConfigManager.is_enabled("ui_show_multicurrency"))
        self.chk_price_channels.setChecked(ConfigManager.is_enabled("ui_show_price_channels"))
        self.chk_fifo.setChecked(ConfigManager.is_enabled("mod_inventory_fifo"))
        self.chk_budgets.setChecked(ConfigManager.is_enabled("mod_budgets"))
        self.chk_strict_cash.setChecked(ConfigManager.is_enabled("pos_strict_cash"))
        
    def apply_preset(self, multicurrency, price_channels, fifo, budgets, strict_cash):
        self.chk_multicurrency.setChecked(multicurrency)
        self.chk_price_channels.setChecked(price_channels)
        self.chk_fifo.setChecked(fifo)
        self.chk_budgets.setChecked(budgets)
        self.chk_strict_cash.setChecked(strict_cash)
        QMessageBox.information(self, "Perfil Cargado", "Se han aplicado los checks del perfil seleccionado. Recuerda guardar.")
        
    def save_config(self):
        ConfigManager.set_enabled("ui_show_multicurrency", self.chk_multicurrency.isChecked())
        ConfigManager.set_enabled("ui_show_price_channels", self.chk_price_channels.isChecked())
        ConfigManager.set_enabled("mod_inventory_fifo", self.chk_fifo.isChecked())
        ConfigManager.set_enabled("mod_budgets", self.chk_budgets.isChecked())
        ConfigManager.set_enabled("pos_strict_cash", self.chk_strict_cash.isChecked())
        
        # Persistir a BD
        try:
            ConfigManager.save_to_db()
            QMessageBox.information(self, "Éxito", "Configuración guardada exitosamente.\n\nEs necesario reiniciar el sistema (o cerrar y volver a abrir la caja) para que todos los cambios hagan efecto.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar la configuración: {e}")
