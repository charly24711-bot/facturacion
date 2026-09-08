import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QGroupBox, QComboBox

class ThemeDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo de Opciones Locales (PyQt6)")
        self.resize(700, 300)
        
        main_layout = QVBoxLayout(self)
        
        # Selector de Tema
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Selecciona el estilo a previsualizar:"))
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems([
            "1. Estilo 'Pegasus/Starsoft' (Retail Clásico)",
            "2. Estilo 'FlexTech/Sistec' (Moderno Plano)",
            "3. Estilo 'Alta Legibilidad' (Gris y Azul Alto Contraste)"
        ])
        self.cmb_theme.currentIndexChanged.connect(self.apply_theme)
        top_layout.addWidget(self.cmb_theme)
        main_layout.addLayout(top_layout)
        
        # Contenedor Inferior Simulado
        self.bottom_panel = QGroupBox("Panel Inferior POS")
        panel_layout = QHBoxLayout(self.bottom_panel)
        
        # Grilla central simulada
        grid = QGridLayout()
        grid.addWidget(QLabel("Sub-Total:"), 0, 0)
        self.lbl_sub = QLabel("150,000")
        self.lbl_sub.setProperty("is_value", True)
        grid.addWidget(self.lbl_sub, 0, 1)
        
        grid.addWidget(QLabel("IVA 5%:"), 1, 0)
        self.lbl_iva5 = QLabel("2,500")
        self.lbl_iva5.setProperty("is_value", True)
        grid.addWidget(self.lbl_iva5, 1, 1)
        
        grid.addWidget(QLabel("Total IVA:"), 2, 0)
        self.lbl_tiva = QLabel("15,000")
        self.lbl_tiva.setProperty("is_value", True)
        grid.addWidget(self.lbl_tiva, 2, 1)
        
        grid.addWidget(QLabel("Total Gral.:"), 3, 0)
        self.lbl_total = QLabel("165,000")
        self.lbl_total.setProperty("is_total", True)
        grid.addWidget(self.lbl_total, 3, 1)
        
        panel_layout.addLayout(grid)
        
        # Botonera
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        self.btn_guardar = QPushButton("Guardar Factura")
        self.btn_cancelar = QPushButton("Cancelar")
        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_cancelar)
        
        panel_layout.addLayout(btn_layout)
        main_layout.addWidget(self.bottom_panel)
        
        self.apply_theme(0)
        
    def apply_theme(self, index):
        if index == 0:
            # Pegasus / Retail Clasico
            self.bottom_panel.setStyleSheet("""
                QGroupBox { background-color: #f0f0f0; border: 2px solid #888; font-weight: bold; }
                QLabel { font-family: 'Arial'; font-size: 14px; color: black; font-weight: bold; }
                QLabel[is_value="true"] { background-color: white; border: 1px inset #aaa; padding: 2px; }
                QLabel[is_total="true"] { background-color: black; color: #00ff00; font-family: 'Consolas', 'Courier New'; font-size: 24px; padding: 4px; }
                QPushButton { background-color: #e0e0e0; border: 2px outset #ccc; padding: 10px; font-weight: bold; }
            """)
        elif index == 1:
            # FlexTech / Plano Moderno
            self.bottom_panel.setStyleSheet("""
                QGroupBox { background-color: white; border: 1px solid #ddd; font-weight: bold; }
                QLabel { font-family: 'Segoe UI', 'Arial'; font-size: 14px; color: #333; }
                QLabel[is_value="true"] { background-color: #f9f9f9; border-bottom: 2px solid #2196F3; padding: 4px; }
                QLabel[is_total="true"] { color: #d32f2f; font-size: 24px; font-weight: bold; border-bottom: 3px solid #d32f2f; }
                QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 10px; font-weight: bold; }
                QPushButton:hover { background-color: #1976D2; }
            """)
        elif index == 2:
            # Alta Legibilidad Alto Contraste
            self.bottom_panel.setStyleSheet("""
                QGroupBox { background-color: #e3f2fd; border: none; font-weight: bold; }
                QLabel { font-family: 'Arial'; font-size: 16px; color: #0d47a1; font-weight: bold; }
                QLabel[is_value="true"] { background-color: white; border: 1px solid #1565c0; padding: 4px; color: #000; }
                QLabel[is_total="true"] { background-color: #1565c0; color: white; font-size: 26px; padding: 8px; border-radius: 4px; }
                QPushButton { background-color: #ff9800; color: white; border: 1px solid #e65100; padding: 12px; font-weight: bold; font-size: 14px; border-radius: 5px; }
            """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ThemeDemo()
    window.show()
    sys.exit(app.exec())
