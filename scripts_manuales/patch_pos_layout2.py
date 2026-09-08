import sys

def main():
    file_path = r"c:\ENTORNO LOCAL\Control\ui\main_window.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_str = "        # SECCION 1: ATRIBUTOS FINANCIEROS Y FISCALES (Grid Central)"
    end_str = "        main_bottom_layout.addLayout(fin_grid)"

    start_idx = content.find(start_str)
    end_idx = content.find(end_str)

    if start_idx == -1 or end_idx == -1:
        print("Could not find block.")
        return
        
    end_idx += len(end_str)

    new_block = """        # SECCION 1: ATRIBUTOS FINANCIEROS Y FISCALES (Layout Estético Tipo Ticket)
        fin_layout = QHBoxLayout()
        fin_layout.setSpacing(40)
        
        # Columna 1: Impuestos
        col1 = QFormLayout()
        col1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_iva_5 = QLabel("0")
        self.lbl_iva_5.setProperty("is_value", True)
        self.lbl_iva_10 = QLabel("0")
        self.lbl_iva_10.setProperty("is_value", True)
        self.lbl_total_iva = QLabel("0")
        self.lbl_total_iva.setProperty("is_value", True)
        
        col1.addRow("Iva 5%:", self.lbl_iva_5)
        col1.addRow("Iva 10%:", self.lbl_iva_10)
        col1.addRow("Total Iva:", self.lbl_total_iva)
        
        # Variables ocultas que el código necesita para no crashear
        self.lbl_subtotal = QLabel("0")
        self.lbl_recargo = QLabel("0")
        self.lbl_iv_incl = QLabel("0")
        self.lbl_total_iva_2 = QLabel("0")
        self.lbl_nota_debito = QLabel("0")
        
        # Columna 2: Liquidación
        col2 = QFormLayout()
        col2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_descuento = QLabel("0")
        self.lbl_descuento.setProperty("is_value", True)
        self.lbl_vuelto = QLabel("0")
        self.lbl_vuelto.setProperty("is_value", True)
        self.lbl_total_gral = QLabel("0")
        self.lbl_total_gral.setProperty("is_value", True)
        self.lbl_total_gral.setStyleSheet("font-size: 32px; color: #ffeb3b; padding: 10px 20px; min-width: 200px;")
        
        col2.addRow("Descuento:", self.lbl_descuento)
        col2.addRow("Vuelto:", self.lbl_vuelto)
        col2.addRow("TOTAL GRAL:", self.lbl_total_gral)
        
        fin_layout.addLayout(col1)
        fin_layout.addLayout(col2)
        
        main_bottom_layout.addLayout(fin_layout)"""

    new_content = content[:start_idx] + new_block + content[end_idx:]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("UI applied successfully.")

if __name__ == "__main__":
    main()
