import re

def main():
    file_path = r"c:\ENTORNO LOCAL\Control\ui\main_window.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the start and end of the block to replace
    start_str = "        bottom_panel_layout = QHBoxLayout()"
    end_str = "        main_layout.addLayout(bottom_panel_layout, stretch=1)"

    start_idx = content.find(start_str)
    end_idx = content.find(end_str)

    if start_idx == -1 or end_idx == -1:
        print("Could not find start or end string.")
        return

    new_block = """        bottom_panel_layout = QHBoxLayout()
        
        # CONTENEDOR PRINCIPAL TEXTURIZADO
        main_bottom_widget = QWidget()
        main_bottom_widget.setStyleSheet(\"\"\"
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d7b57a, stop:0.5 #c89d5c, stop:1 #e2c695);
                border: 2px solid #8b5a2b;
                border-radius: 5px;
            }
            QLabel {
                background: transparent;
                border: none;
                font-family: Arial;
                font-weight: bold;
                font-size: 14px;
                color: #000080;
            }
            QLabel[is_value="true"] {
                color: white;
                background-color: #800080;
                border: 1px solid #4a004a;
                padding: 2px;
                font-size: 16px;
            }
        \"\"\")
        main_bottom_layout = QHBoxLayout(main_bottom_widget)
        main_bottom_layout.setContentsMargins(10, 10, 10, 10)
        main_bottom_layout.setSpacing(20)

        # SECCION 1: ATRIBUTOS FINANCIEROS Y FISCALES (Grid Central)
        fin_grid = QGridLayout()
        fin_grid.setHorizontalSpacing(15)
        fin_grid.setVerticalSpacing(5)

        # Fila 0: Sub-Total
        fin_grid.addWidget(QLabel("Sub-Total:"), 0, 2)
        self.lbl_subtotal = QLabel("0")
        self.lbl_subtotal.setProperty("is_value", True)
        self.lbl_subtotal.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_subtotal, 0, 3)

        # Fila 1: Iva 5%, Recargo, T. Descuento Items
        lbl_iva5 = QLabel("Iva 5%:")
        lbl_iva5.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_iva5, 1, 0)
        self.lbl_iva_5 = QLabel("0")
        self.lbl_iva_5.setProperty("is_value", True)
        self.lbl_iva_5.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_iva_5, 1, 1)

        lbl_recargo = QLabel("Recargo:")
        lbl_recargo.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_recargo, 1, 2)
        self.lbl_recargo = QLabel("0")
        self.lbl_recargo.setProperty("is_value", True)
        self.lbl_recargo.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_recargo, 1, 3)

        fin_grid.addWidget(QLabel("T. Descuento Items"), 1, 4)

        # Fila 2: Iva 10%, Iva, Iv. Incl
        lbl_iva10 = QLabel("Iva 10%:")
        lbl_iva10.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_iva10, 2, 0)
        self.lbl_iva_10 = QLabel("0")
        self.lbl_iva_10.setProperty("is_value", True)
        self.lbl_iva_10.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_iva_10, 2, 1)

        lbl_iva_tot = QLabel("Iva:")
        lbl_iva_tot.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_iva_tot, 2, 2)
        self.lbl_total_iva = QLabel("0")
        self.lbl_total_iva.setProperty("is_value", True)
        self.lbl_total_iva.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_total_iva, 2, 3)

        fin_grid.addWidget(QLabel("Iv. Incl."), 2, 4)
        self.lbl_iv_incl = QLabel("0")
        self.lbl_iv_incl.setProperty("is_value", True)
        self.lbl_iv_incl.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_iv_incl, 2, 5)

        # Fila 3: Total Iva, Descuento
        lbl_tot_iva_lbl = QLabel("Total Iva:")
        lbl_tot_iva_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_tot_iva_lbl, 3, 0)
        self.lbl_total_iva_2 = QLabel("0")  # Repeated just for layout match
        self.lbl_total_iva_2.setProperty("is_value", True)
        self.lbl_total_iva_2.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_total_iva_2, 3, 1)

        lbl_desc = QLabel("Descuento:")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_desc, 3, 2)
        self.lbl_descuento = QLabel("0")
        self.lbl_descuento.setProperty("is_value", True)
        self.lbl_descuento.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_descuento, 3, 3)

        # Fila 4: Nota Debito
        lbl_nota = QLabel("Nota Debito:")
        lbl_nota.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_nota, 4, 2)
        self.lbl_nota_debito = QLabel("0")
        self.lbl_nota_debito.setProperty("is_value", True)
        self.lbl_nota_debito.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_nota_debito, 4, 3)

        # Fila 5: Total Gral.
        lbl_tot_gral = QLabel("Total Gral.:")
        lbl_tot_gral.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(lbl_tot_gral, 5, 2)
        self.lbl_total_gral = QLabel("0")
        self.lbl_total_gral.setProperty("is_value", True)
        self.lbl_total_gral.setAlignment(Qt.AlignmentFlag.AlignRight)
        fin_grid.addWidget(self.lbl_total_gral, 5, 3)
        
        main_bottom_layout.addLayout(fin_grid)
        
        # Botonera Central Inferior
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(5)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("background-color: #e0e0e0; color: #000080; font-weight: bold; padding: 5px; font-size: 14px; border: 1px solid #777;")
        btn_guardar.clicked.connect(self.procesar_factura)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("background-color: #e0e0e0; color: #000080; font-weight: bold; padding: 5px; font-size: 14px; border: 1px solid #777;")
        btn_cancelar.clicked.connect(self.cancelar_venta_actual)
        
        btn_salir = QPushButton("Salir")
        btn_salir.setStyleSheet("background-color: #e0e0e0; color: #000080; font-weight: bold; padding: 5px; font-size: 14px; border: 1px solid #777;")
        btn_salir.clicked.connect(self.close)
        
        btn_row.addWidget(btn_guardar)
        btn_row.addWidget(btn_cancelar)
        btn_row.addWidget(btn_salir)
        
        lbl_shortcut = QLabel("[ Ctrl+W ]")
        lbl_shortcut.setStyleSheet("color: #000000; font-size: 11px;")
        lbl_shortcut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_layout.addLayout(btn_row)
        btn_layout.addWidget(lbl_shortcut)
        btn_layout.addStretch()
        
        main_bottom_layout.addLayout(btn_layout)
        
        # SECCION MONEDAS Y EXTRAS
        extra_layout = QVBoxLayout()
        
        # Panel Monedas
        monedas_grid = QGridLayout()
        self.lbl_usd = QLabel("0.00")
        self.lbl_brl = QLabel("0.00")
        self.lbl_ars = QLabel("0.00")
        self.lbl_pyg = QLabel("0")
        
        for lbl in [self.lbl_usd, self.lbl_brl, self.lbl_ars, self.lbl_pyg]:
            lbl.setProperty("is_value", True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            
        monedas_grid.addWidget(QLabel("USD"), 0, 0)
        monedas_grid.addWidget(self.lbl_usd, 0, 1)
        monedas_grid.addWidget(QLabel("BRL"), 1, 0)
        monedas_grid.addWidget(self.lbl_brl, 1, 1)
        monedas_grid.addWidget(QLabel("ARS"), 2, 0)
        monedas_grid.addWidget(self.lbl_ars, 2, 1)
        monedas_grid.addWidget(QLabel("PYG"), 3, 0)
        monedas_grid.addWidget(self.lbl_pyg, 3, 1)
        
        extra_layout.addLayout(monedas_grid)
        
        # Agregar Boton de Sangria y Cargar Presup
        misc_btn_layout = QHBoxLayout()
        btn_sangria = QPushButton("Sangría")
        btn_sangria.clicked.connect(self.open_caja_movimiento)
        btn_presup = QPushButton("Presup.")
        btn_presup.clicked.connect(self.abrir_buscar_presupuesto)
        misc_btn_layout.addWidget(btn_sangria)
        misc_btn_layout.addWidget(btn_presup)
        
        extra_layout.addLayout(misc_btn_layout)
        
        main_bottom_layout.addLayout(extra_layout)
        
        # Variables de compatibilidad para evitar crashes en otras funciones
        self.lbl_gravada_10 = QLabel("0")
        self.lbl_gravada_5 = QLabel("0")
        self.lbl_exenta = QLabel("0")
        self.btn_presupuesto = btn_presup
        
        bottom_panel_layout.addWidget(main_bottom_widget)
"""

    new_content = content[:start_idx] + new_block + content[end_idx:]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("Patch applied successfully.")

if __name__ == "__main__":
    main()
