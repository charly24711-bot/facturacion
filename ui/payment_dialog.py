from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QHBoxLayout, QMessageBox, QLabel, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database import SessionLocal
import models
from utils.formatting import aplicar_formato_moneda, parsear_monto
from decimal import Decimal
import math

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))
from ruc_validator.ruc_validator import calcular_dv_ruc, formatear_ruc, validar_ruc, obtener_contribuyente

class PaymentDialog(QDialog):
    def __init__(self, totals, client=None, parent=None):
        super().__init__(parent)
        self.client = client
        self.selected_client = client
        self.setWindowTitle("Cobro Split Multimoneda y Facturación [F11]")
        self.resize(750, 700)
        
        self.total_adeudado_pyg = Decimal(str(totals.get('PYG', 0.0)))
        self.payment_successful = False
        self.payments_list = []
        
        # Cargar Tasas Activas
        self.tasas = self.cargar_tasas()
        
        self.setup_ui()
        self.actualizar_saldos()
        
    def cargar_tasas(self):
        db = SessionLocal()
        rates_db = db.query(models.CurrencyRate).filter_by(is_active=True).all()
        db.close()
        
        tasas = {
            'PYG': {'buy': Decimal("1.0"), 'sell': Decimal("1.0")}
        }
        for r in rates_db:
            tasas[r.currency_code] = {
                'buy': r.buy_rate,
                'sell': r.sell_rate
            }
        return tasas

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- CABECERA ---
        lbl_title = QLabel("TOTAL A COBRAR")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        main_layout.addWidget(lbl_title)
        
        self.lbl_total_pyg = QLabel(f"Gs. {self.total_adeudado_pyg:,.0f}")
        self.lbl_total_pyg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_total_pyg.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        self.lbl_total_pyg.setStyleSheet("color: #0d47a1;")
        main_layout.addWidget(self.lbl_total_pyg)
        
        # --- PANEL CLIENTE / FACTURA LEGAL CON IVA ---
        group_cliente = QGroupBox("Datos del Cliente / Factura con RUC e IVA")
        layout_cli = QGridLayout(group_cliente)
        layout_cli.setSpacing(6)
        
        layout_cli.addWidget(QLabel("RUC / C.I.:"), 0, 0)
        self.txt_cliente_ruc = QLineEdit()
        self.txt_cliente_ruc.setPlaceholderText("Ej: 80001234 o C.I. (Enter para consultar)...")
        self.txt_cliente_ruc.returnPressed.connect(self.consultar_ruc_cliente)
        self.txt_cliente_ruc.editingFinished.connect(self.consultar_ruc_cliente)
        layout_cli.addWidget(self.txt_cliente_ruc, 0, 1)
        
        btn_buscar_cli = QPushButton("🔍 Buscar [F8]")
        btn_buscar_cli.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 4px 8px;")
        btn_buscar_cli.setAutoDefault(False)
        btn_buscar_cli.clicked.connect(self.abrir_busqueda_cliente)
        layout_cli.addWidget(btn_buscar_cli, 0, 2)
        
        btn_cf = QPushButton("👤 Consumidor Final")
        btn_cf.setStyleSheet("background-color: #607d8b; color: white; font-weight: bold; padding: 4px 8px;")
        btn_cf.setAutoDefault(False)
        btn_cf.clicked.connect(self.set_consumidor_final)
        layout_cli.addWidget(btn_cf, 0, 3)
        
        layout_cli.addWidget(QLabel("Razón Social / Nombre:"), 1, 0)
        self.txt_cliente_nombre = QLineEdit()
        self.txt_cliente_nombre.setPlaceholderText("Nombre del cliente o razón social...")
        layout_cli.addWidget(self.txt_cliente_nombre, 1, 1, 1, 2)
        
        self.lbl_cliente_status = QLabel("[Consumidor Final]")
        self.lbl_cliente_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
        layout_cli.addWidget(self.lbl_cliente_status, 1, 3)
        
        main_layout.addWidget(group_cliente)
        
        # Inicializar datos del cliente provisto
        self.inicializar_datos_cliente()
        
        # --- PANEL DE INGRESO DE PAGOS ---
        group_ingreso = QGroupBox("Añadir Pago Parcial")
        layout_ingreso = QHBoxLayout(group_ingreso)
        
        self.combo_moneda = QComboBox()
        self.combo_moneda.addItems(["PYG", "USD", "BRL", "ARS"])
        self.combo_moneda.currentTextChanged.connect(self.mostrar_cotizacion_actual)
        
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(["Efectivo", "Tarjeta Crédito", "Tarjeta Débito", "PIX", "Transferencia Bancaria", "Cuenta Corriente"])
        
        self.txt_monto = QLineEdit()
        self.txt_monto.setPlaceholderText("Monto entregado")
        self.txt_monto.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.txt_monto.textChanged.connect(lambda text: aplicar_formato_moneda(text, self.combo_moneda.currentText(), self.txt_monto))
        self.txt_monto.returnPressed.connect(self.agregar_pago)
        self.txt_cliente_nombre.returnPressed.connect(self.txt_monto.setFocus)
        
        self.lbl_cotizacion_act = QLabel("Tasa: 1.0")
        
        btn_add = QPushButton("Agregar Pago")
        btn_add.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_add.setAutoDefault(False)
        btn_add.clicked.connect(self.agregar_pago)
        
        layout_ingreso.addWidget(QLabel("Moneda:"))
        layout_ingreso.addWidget(self.combo_moneda)
        layout_ingreso.addWidget(self.lbl_cotizacion_act)
        layout_ingreso.addWidget(QLabel("Método:"))
        layout_ingreso.addWidget(self.combo_metodo)
        layout_ingreso.addWidget(QLabel("Monto:"))
        layout_ingreso.addWidget(self.txt_monto)
        layout_ingreso.addWidget(btn_add)
        
        main_layout.addWidget(group_ingreso)
        
        # --- GRILLA DE PAGOS ---
        self.table_pagos = QTableWidget(0, 5)
        self.table_pagos.setHorizontalHeaderLabels(["Moneda", "Método", "Monto Origen", "Cotización (Compra)", "Subtotal (PYG)"])
        self.table_pagos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_pagos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table_pagos)
        
        btn_eliminar_pago = QPushButton("Eliminar Pago Seleccionado")
        btn_eliminar_pago.setAutoDefault(False)
        btn_eliminar_pago.clicked.connect(self.eliminar_pago)
        main_layout.addWidget(btn_eliminar_pago, alignment=Qt.AlignmentFlag.AlignRight)
        
        # --- PANEL DE SALDOS Y VUELTO ---
        group_saldos = QGroupBox("Estado de Cuenta")
        layout_saldos = QGridLayout(group_saldos)
        
        font_saldos = QFont("Arial", 14, QFont.Weight.Bold)
        
        layout_saldos.addWidget(QLabel("Total Recibido (PYG):"), 0, 0)
        self.lbl_recibido = QLabel("0")
        self.lbl_recibido.setFont(font_saldos)
        layout_saldos.addWidget(self.lbl_recibido, 0, 1)
        
        layout_saldos.addWidget(QLabel("Faltante (PYG):"), 1, 0)
        self.lbl_faltante = QLabel("0")
        self.lbl_faltante.setFont(font_saldos)
        self.lbl_faltante.setStyleSheet("color: red;")
        layout_saldos.addWidget(self.lbl_faltante, 1, 1)
        
        layout_saldos.addWidget(QLabel("VUELTO (PYG):"), 2, 0)
        self.lbl_vuelto_pyg = QLabel("0")
        self.lbl_vuelto_pyg.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.lbl_vuelto_pyg.setStyleSheet("color: green;")
        layout_saldos.addWidget(self.lbl_vuelto_pyg, 2, 1)
        
        # Calculadora de Vuelto Cruzado
        layout_saldos.addWidget(QLabel("Moneda para Vuelto:"), 3, 0)
        self.combo_vuelto_moneda = QComboBox()
        self.combo_vuelto_moneda.addItems(["PYG", "USD", "BRL", "ARS"])
        self.combo_vuelto_moneda.currentTextChanged.connect(self.actualizar_saldos)
        layout_saldos.addWidget(self.combo_vuelto_moneda, 3, 1)
        
        layout_saldos.addWidget(QLabel("VUELTO A ENTREGAR:"), 4, 0)
        self.lbl_vuelto_final = QLabel("0")
        self.lbl_vuelto_final.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.lbl_vuelto_final.setStyleSheet("color: darkgreen; background-color: #e8f5e9; padding: 5px;")
        layout_saldos.addWidget(self.lbl_vuelto_final, 4, 1)
        
        main_layout.addWidget(group_saldos)
        
        # --- BOTONES DE ACCIÓN ---
        btn_layout = QHBoxLayout()
        self.btn_cobrar = QPushButton("Confirmar Factura [Enter]")
        self.btn_cobrar.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 15px; font-size: 16px;")
        self.btn_cobrar.setAutoDefault(True)
        self.btn_cobrar.setDefault(False)
        self.btn_cobrar.clicked.connect(self.procesar_cobro)
        self.btn_cobrar.setEnabled(False)
        
        btn_cancelar = QPushButton("Cancelar [Esc]")
        btn_cancelar.setStyleSheet("padding: 15px; font-size: 16px;")
        btn_cancelar.setAutoDefault(False)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_cobrar)
        main_layout.addLayout(btn_layout)
        
        self.mostrar_cotizacion_actual(self.combo_moneda.currentText())

    def mostrar_cotizacion_actual(self, moneda):
        tasa_compra = self.tasas.get(moneda, {}).get('buy', Decimal("1.0"))
        self.lbl_cotizacion_act.setText(f"Tasa: {tasa_compra:,.2f}")


    # format_monto removido en favor de utils.formatting.aplicar_formato_moneda

    def agregar_pago(self):
        try:
            moneda = self.combo_moneda.currentText()
            monto_str = parsear_monto(self.txt_monto.text(), moneda)
            if not monto_str or monto_str == "0": return
            
            monto_origen = Decimal(monto_str)
            if monto_origen <= 0: return
            
            moneda = self.combo_moneda.currentText()
            metodo = self.combo_metodo.currentText()
            tasa_compra = self.tasas.get(moneda, {}).get('buy', Decimal("1.0"))
            
            monto_pyg = (monto_origen * tasa_compra).quantize(Decimal("1"))
            
            row = self.table_pagos.rowCount()
            self.table_pagos.insertRow(row)
            
            self.table_pagos.setItem(row, 0, QTableWidgetItem(moneda))
            self.table_pagos.setItem(row, 1, QTableWidgetItem(metodo))
            self.table_pagos.setItem(row, 2, QTableWidgetItem(f"{monto_origen:,.2f}".replace(".00", "")))
            self.table_pagos.setItem(row, 3, QTableWidgetItem(f"{tasa_compra:,.2f}".replace(".00", "")))
            self.table_pagos.setItem(row, 4, QTableWidgetItem(f"{monto_pyg:,.0f}"))
            
            self.txt_monto.clear()
            self.actualizar_saldos()
            if self.btn_cobrar.isEnabled():
                self.btn_cobrar.setFocus()
            else:
                self.txt_monto.setFocus()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", "Monto inválido.")
            
    def eliminar_pago(self):
        current_row = self.table_pagos.currentRow()
        if current_row >= 0:
            self.table_pagos.removeRow(current_row)
            self.actualizar_saldos()

    def actualizar_saldos(self):
        total_recibido_pyg = Decimal("0")
        for row in range(self.table_pagos.rowCount()):
            item_pyg = self.table_pagos.item(row, 4)
            if item_pyg:
                total_recibido_pyg += Decimal(item_pyg.text().replace(',', ''))
                
        self.lbl_recibido.setText(f"{total_recibido_pyg:,.0f}")
        
        faltante = self.total_adeudado_pyg - total_recibido_pyg
        if faltante > 0:
            self.lbl_faltante.setText(f"{faltante:,.0f}")
            self.lbl_vuelto_pyg.setText("0")
            self.lbl_vuelto_final.setText("0")
            self.btn_cobrar.setEnabled(False)
            self.btn_cobrar.setDefault(False)
        else:
            self.lbl_faltante.setText("0")
            vuelto_pyg = abs(faltante)
            self.lbl_vuelto_pyg.setText(f"{vuelto_pyg:,.0f}")
            self.btn_cobrar.setEnabled(True)
            self.btn_cobrar.setDefault(True)
            
            # Vuelto Cruzado
            moneda_vuelto = self.combo_vuelto_moneda.currentText()
            tasa_venta = self.tasas.get(moneda_vuelto, {}).get('sell', Decimal("1.0"))
            
            if moneda_vuelto == "PYG":
                vuelto_final = vuelto_pyg
                self.lbl_vuelto_final.setText(f"Gs. {vuelto_final:,.0f}")
            else:
                # Redondeo hacia abajo a 2 decimales para evitar pérdidas
                vuelto_final = math.floor((vuelto_pyg / tasa_venta) * 100) / 100.0
                self.lbl_vuelto_final.setText(f"{vuelto_final:,.2f} {moneda_vuelto}")

    def inicializar_datos_cliente(self):
        if self.client and self.client.cli_codigo != "000001":
            self.txt_cliente_ruc.setText(self.client.cli_ruc or "")
            self.txt_cliente_nombre.setText(self.client.cli_nombre or "")
            self.lbl_cliente_status.setText("[Cliente Registrado]")
            self.lbl_cliente_status.setStyleSheet("color: #1565c0; font-weight: bold;")
        else:
            self.set_consumidor_final()

    def set_consumidor_final(self):
        self.txt_cliente_ruc.setText("")
        self.txt_cliente_nombre.setText("CONSUMIDOR FINAL")
        self.lbl_cliente_status.setText("[Consumidor Final - Sin RUC]")
        self.lbl_cliente_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
        self.selected_client = None

    def consultar_ruc_cliente(self):
        texto = self.txt_cliente_ruc.text().strip()
        if not texto:
            self.set_consumidor_final()
            self.txt_monto.setFocus()
            return

        ruc_normalizado = formatear_ruc(texto)
        if ruc_normalizado:
            self.txt_cliente_ruc.setText(ruc_normalizado)
            
        base_ruc = ruc_normalizado.split('-')[0] if ruc_normalizado else texto.split('-')[0]
        
        db = SessionLocal()
        try:
            # 1. Buscar si ya existe como Cliente registrado
            cli = db.query(models.Client).filter(
                (models.Client.cli_ruc == ruc_normalizado) |
                (models.Client.cli_ruc == base_ruc)
            ).first()
            
            if cli:
                self.txt_cliente_nombre.setText(cli.cli_nombre)
                self.lbl_cliente_status.setText("[Cliente Registrado]")
                self.lbl_cliente_status.setStyleSheet("color: #1565c0; font-weight: bold;")
                self.selected_client = cli
                self.txt_monto.setFocus()
                return
                
            # 2. Buscar en el Padrón Oficial DNIT (Local u Online con auto-caching)
            contrib = obtener_contribuyente(db, base_ruc, auto_cache=True)
            if contrib:
                self.txt_cliente_nombre.setText(contrib['razon_social'])
                tag_origen = "[DNIT]" if contrib.get('origen') == 'LOCAL' else "[DNIT Online]"
                self.lbl_cliente_status.setText(f"{tag_origen} Padrón Verificado")
                self.lbl_cliente_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
                self.txt_monto.setFocus()
                return
                
            # 3. No es contribuyente en DNIT pero C.I. válida (Persona física sin RUC)
            self.lbl_cliente_status.setText("[Sin RUC en DNIT - Ingrese Nombre]")
            self.lbl_cliente_status.setStyleSheet("color: #e65100; font-weight: bold;")
            if not self.txt_cliente_nombre.text() or self.txt_cliente_nombre.text() == "CONSUMIDOR FINAL":
                self.txt_cliente_nombre.clear()
                self.txt_cliente_nombre.setFocus()
            else:
                self.txt_monto.setFocus()
        finally:
            db.close()

    def abrir_busqueda_cliente(self):
        from ui.client_search_dialog import ClientSearchDialog
        dlg = ClientSearchDialog(self)
        if dlg.exec() and dlg.selected_client:
            self.selected_client = dlg.selected_client
            self.txt_cliente_ruc.setText(dlg.selected_client.cli_ruc or "")
            self.txt_cliente_nombre.setText(dlg.selected_client.cli_nombre or "")
            self.lbl_cliente_status.setText("[Cliente Seleccionado]")
            self.lbl_cliente_status.setStyleSheet("color: #1565c0; font-weight: bold;")
            self.txt_monto.setFocus()

    def resolver_cliente_final(self):
        db = SessionLocal()
        try:
            ruc_in = self.txt_cliente_ruc.text().strip()
            nom_in = self.txt_cliente_nombre.text().strip()
            
            # Caso Consumidor Final
            if (not ruc_in or ruc_in == "44444401-7") and (not nom_in or nom_in.upper() == "CONSUMIDOR FINAL"):
                cf = db.query(models.Client).filter_by(cli_codigo="000001").first()
                if not cf:
                    cf = models.Client(cli_codigo="000001", cli_nombre="CONSUMIDOR FINAL", cli_ruc="44444401-7")
                    db.add(cf)
                    db.commit()
                    db.refresh(cf)
                self.selected_client = cf
                return
                
            # Caso Cliente con RUC o Nombre específico
            existente = None
            if ruc_in:
                existente = db.query(models.Client).filter(
                    (models.Client.cli_ruc == ruc_in) | 
                    (models.Client.cli_ruc == ruc_in.split('-')[0])
                ).first()
            if not existente and nom_in and nom_in.upper() != "CONSUMIDOR FINAL":
                existente = db.query(models.Client).filter_by(cli_nombre=nom_in).first()
                
            if existente:
                self.selected_client = existente
            else:
                # Generar nuevo código correlativo de 6 dígitos
                codes = db.query(models.Client.cli_codigo).all()
                max_val = 0
                for (code,) in codes:
                    if code and str(code).strip().isdigit():
                        max_val = max(max_val, int(code.strip()))
                next_code = str(max_val + 1).zfill(6)
                
                nuevo = models.Client(
                    cli_codigo=next_code,
                    cli_nombre=nom_in or "CLIENTE OCASIONAL",
                    cli_ruc=ruc_in or "44444401-7"
                )
                db.add(nuevo)
                db.commit()
                db.refresh(nuevo)
                self.selected_client = nuevo
        finally:
            db.close()

    def procesar_cobro(self):
        self.payments_list = []
        for row in range(self.table_pagos.rowCount()):
            moneda = self.table_pagos.item(row, 0).text()
            metodo = self.table_pagos.item(row, 1).text()
            monto_origen = Decimal(self.table_pagos.item(row, 2).text().replace(',', ''))
            monto_pyg = Decimal(self.table_pagos.item(row, 4).text().replace(',', ''))
            
            self.payments_list.append({
                'moneda': moneda,
                'metodo': metodo,
                'monto_origen': monto_origen,
                'monto_pyg': monto_pyg
            })
            
        self.resolver_cliente_final()
        
        total_recibido = sum([p['monto_pyg'] for p in self.payments_list])
        faltante = self.total_adeudado_pyg - total_recibido
        self.vuelto_devuelto_pyg = abs(faltante) if faltante < 0 else Decimal('0')
        
        self.payment_successful = True
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_F8:
            self.abrir_busqueda_cliente()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Si el foco está en el campo de monto, procesar agregar pago
            if self.txt_monto.hasFocus():
                self.agregar_pago()
                event.accept()
                return
            # Si el foco está en el RUC, consultar RUC
            elif self.txt_cliente_ruc.hasFocus():
                self.consultar_ruc_cliente()
                event.accept()
                return
            # Si la factura ya está saldada y el botón de cobrar está activo, confirmar venta
            elif self.btn_cobrar.isEnabled():
                self.procesar_cobro()
                event.accept()
                return
            else:
                event.accept()
                return
        else:
            super().keyPressEvent(event)
