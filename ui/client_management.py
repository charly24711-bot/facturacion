import sys
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QFormLayout, 
                             QHeaderView, QMessageBox, QGroupBox, QSplitter, QComboBox, QLabel)
from PyQt6.QtCore import Qt
from database import SessionLocal
import models
from decimal import Decimal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))
from ruc_validator.ruc_validator import calcular_dv_ruc, formatear_ruc, validar_ruc, obtener_contribuyente

class ClientManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Clientes (ABM)")
        self.resize(920, 520)
        
        self.current_client_id = None
        
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- PANEL IZQUIERDO: Buscador y Lista ---
        left_widget = QGroupBox("Lista de Clientes")
        left_layout = QVBoxLayout(left_widget)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por código, nombre o RUC...")
        self.txt_search.textChanged.connect(self.load_clients)
        left_layout.addWidget(self.txt_search)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "RUC"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.table)
        
        # --- PANEL DERECHO: Ficha de Cliente ---
        right_widget = QGroupBox("Ficha de Cliente")
        right_layout = QVBoxLayout(right_widget)
        
        form_layout = QFormLayout()
        
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setReadOnly(True)
        self.txt_codigo.setStyleSheet("background-color: #e9ecef; color: #495057; font-weight: bold; border: 1px solid #ced4da;")
        self.txt_codigo.setPlaceholderText("Autogenerado...")
        
        # Campo RUC con botón de consulta y cálculo automático de DV
        self.txt_ruc = QLineEdit()
        self.txt_ruc.setPlaceholderText("Ej. 80001234 o 4455667")
        self.txt_ruc.editingFinished.connect(self.on_ruc_changed)
        
        ruc_layout = QHBoxLayout()
        ruc_layout.addWidget(self.txt_ruc)
        self.btn_buscar_dnit = QPushButton("🔍 Consultar DNIT")
        self.btn_buscar_dnit.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold; padding: 4px 8px;")
        self.btn_buscar_dnit.clicked.connect(self.on_ruc_changed)
        ruc_layout.addWidget(self.btn_buscar_dnit)
        
        self.lbl_ruc_status = QLabel("")
        self.lbl_ruc_status.setStyleSheet("font-size: 11px; color: green; font-style: italic;")

        self.txt_nombre = QLineEdit()
        self.txt_ci = QLineEdit()
        self.txt_ci.setPlaceholderText("Cédula de Identidad...")
        self.txt_ci.editingFinished.connect(self.on_ci_changed)
        
        self.txt_direcc = QLineEdit()
        self.txt_telefo = QLineEdit()
        self.txt_limite = QLineEdit("0")
        self.txt_limite.textChanged.connect(lambda t, le=self.txt_limite: self.auto_format_thousands(t, le))
        
        self.cmb_price_list = QComboBox()
        self.cmb_price_list.addItem("— Sin Lista Especial —", None)
        self._load_price_lists()
        
        form_layout.addRow("Código (*):", self.txt_codigo)
        form_layout.addRow("RUC (*):", ruc_layout)
        form_layout.addRow("", self.lbl_ruc_status)
        form_layout.addRow("Nombre (*):", self.txt_nombre)
        form_layout.addRow("Cédula (CI):", self.txt_ci)
        form_layout.addRow("Dirección:", self.txt_direcc)
        form_layout.addRow("Teléfono:", self.txt_telefo)
        form_layout.addRow("Límite de Crédito (Gs):", self.txt_limite)
        form_layout.addRow("Lista de Precios:", self.cmb_price_list)
        
        right_layout.addLayout(form_layout)
        
        # Botones de Acción
        btn_layout = QHBoxLayout()
        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self.clear_form)
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.save_client)
        
        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.setStyleSheet("background-color: darkred; color: white;")
        btn_eliminar.clicked.connect(self.delete_client)
        
        btn_layout.addWidget(btn_nuevo)
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_eliminar)
        
        right_layout.addStretch()
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        
        main_layout.addWidget(splitter)
        
        self.load_clients()
        self.clear_form()
        
    def get_next_client_code(self):
        """Genera el siguiente código numérico de 6 dígitos correlativo (ej. 000002)."""
        db = SessionLocal()
        try:
            codes = db.query(models.Client.cli_codigo).all()
            max_val = 0
            for (code,) in codes:
                if code and str(code).strip().isdigit():
                    max_val = max(max_val, int(code.strip()))
            return str(max_val + 1).zfill(6)
        except Exception:
            return "000001"
        finally:
            db.close()
        
    def _load_price_lists(self):
        db = SessionLocal()
        lists = db.query(models.PriceList).all()
        for lst in lists:
            self.cmb_price_list.addItem(lst.pl_nombre, lst.id)
        db.close()

    def load_clients(self):
        query_text = self.txt_search.text().lower()
        db = SessionLocal()
        
        clients = db.query(models.Client).filter(
            (models.Client.cli_nombre.ilike(f"%{query_text}%")) |
            (models.Client.cli_codigo.ilike(f"%{query_text}%")) |
            (models.Client.cli_ruc.ilike(f"%{query_text}%"))
        ).limit(100).all()
        
        self.table.setRowCount(0)
        for row, cli in enumerate(clients):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(cli.cli_codigo))
            self.table.setItem(row, 1, QTableWidgetItem(cli.cli_nombre))
            self.table.setItem(row, 2, QTableWidgetItem(cli.cli_ruc or ""))
            
            # Guardar el ID oculto
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, cli.id)
            
        db.close()
        
    def on_selection_changed(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        client_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        db = SessionLocal()
        cli = db.query(models.Client).filter_by(id=client_id).first()
        if cli:
            self.current_client_id = cli.id
            self.txt_codigo.setText(cli.cli_codigo)
            self.txt_codigo.setReadOnly(True)
            self.txt_codigo.setStyleSheet("background-color: #e9ecef; color: #495057; font-weight: bold; border: 1px solid #ced4da;")
            self.txt_nombre.setText(cli.cli_nombre or "")
            self.txt_ruc.setText(cli.cli_ruc or "")
            self.txt_ci.setText(cli.cli_ci or "")
            self.txt_direcc.setText(cli.cli_direcc or "")
            self.txt_telefo.setText(cli.cli_telefo or "")
            self.txt_limite.setText(f"{int(cli.cli_limite or 0):,}")
            
            self.lbl_ruc_status.setText("")
            idx = self.cmb_price_list.findData(cli.price_list_id)
            if idx >= 0:
                self.cmb_price_list.setCurrentIndex(idx)
            else:
                self.cmb_price_list.setCurrentIndex(0)
        db.close()
        
    def on_ruc_changed(self):
        ruc_raw = self.txt_ruc.text().strip()
        if not ruc_raw:
            self.lbl_ruc_status.setText("")
            return
            
        ruc_formateado = formatear_ruc(ruc_raw)
        self.txt_ruc.setText(ruc_formateado)
        
        base = ruc_formateado.split('-')[0]
        dv = ruc_formateado.split('-')[1]
        
        # Si la CI está vacía y es RUC de persona física
        if not self.txt_ci.text().strip() and len(base) <= 8 and not base.startswith("800"):
            self.txt_ci.setText(base)
            
        # Buscar en Padrón DNIT local u online
        db = SessionLocal()
        contribuyente = obtener_contribuyente(db, base, auto_cache=True)
        db.close()
        
        if contribuyente:
            origen_tag = "[DNIT]" if contribuyente.get('origen') == 'LOCAL' else "[DNIT Online]"
            self.lbl_ruc_status.setText(f"{origen_tag} {contribuyente['razon_social']}")
            self.lbl_ruc_status.setStyleSheet("font-size: 11px; color: green; font-weight: bold;")
            # Si el campo nombre está vacío o se está creando nuevo, autocompletar nombre
            if not self.txt_nombre.text().strip():
                self.txt_nombre.setText(contribuyente['razon_social'])
        else:
            self.lbl_ruc_status.setText(f"[OK] DV calculado: -{dv}")
            self.lbl_ruc_status.setStyleSheet("font-size: 11px; color: #6c757d; font-style: italic;")

    def on_ci_changed(self):
        ci_raw = self.txt_ci.text().strip()
        if not ci_raw or not ci_raw.isdigit():
            return
            
        # Si no hay RUC cargado, generar sugerencia de RUC con DV
        if not self.txt_ruc.text().strip():
            dv = calcular_dv_ruc(ci_raw)
            self.txt_ruc.setText(f"{ci_raw}-{dv}")
            self.on_ruc_changed()

    def clear_form(self):
        self.current_client_id = None
        self.table.clearSelection()
        next_code = self.get_next_client_code()
        self.txt_codigo.setText(next_code)
        self.txt_codigo.setReadOnly(True)
        self.txt_codigo.setStyleSheet("background-color: #e9ecef; color: #495057; font-weight: bold; border: 1px solid #ced4da;")
        self.txt_nombre.clear()
        self.txt_ruc.clear()
        self.txt_ci.clear()
        self.txt_direcc.clear()
        self.txt_telefo.clear()
        self.txt_limite.setText("0")
        self.lbl_ruc_status.setText("")
        self.cmb_price_list.setCurrentIndex(0)
        self.txt_ruc.setFocus()
        
    def save_client(self):
        codigo = self.txt_codigo.text().strip()
        nombre = self.txt_nombre.text().strip()
        
        if not codigo or not nombre:
            QMessageBox.warning(self, "Error", "El Código y el Nombre son obligatorios.")
            return
            
        db = SessionLocal()
        try:
            if self.current_client_id:
                # Actualizar
                cli = db.query(models.Client).filter_by(id=self.current_client_id).first()
                if not cli:
                    raise Exception("No se encontró el cliente.")
            else:
                # Verificar que el código no exista; si existe, obtener el siguiente
                existente = db.query(models.Client).filter_by(cli_codigo=codigo).first()
                if existente:
                    codigo = self.get_next_client_code()
                # Crear nuevo
                cli = models.Client()
                cli.cli_codigo = codigo
                db.add(cli)
                
            cli.cli_nombre = nombre
            cli.cli_ruc = self.txt_ruc.text().strip()
            cli.cli_ci = self.txt_ci.text().strip()
            cli.cli_direcc = self.txt_direcc.text().strip()
            cli.cli_telefo = self.txt_telefo.text().strip()
            
            limite_clean = str(self.txt_limite.text()).replace(',', '').replace('.', '').strip()
            cli.cli_limite = Decimal(limite_clean or '0')
            cli.price_list_id = self.cmb_price_list.currentData()
            
            db.commit()
            QMessageBox.information(self, "Éxito", f"Cliente {cli.cli_codigo} guardado correctamente.")
            self.load_clients()
            self.clear_form()
        except ValueError:
            db.rollback()
            QMessageBox.warning(self, "Error", "Verifique que el límite de crédito sea un número válido.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            db.close()
            
    def delete_client(self):
        if not self.current_client_id:
            return
            
        reply = QMessageBox.question(self, 'Confirmar', '¿Seguro que desea eliminar este cliente?', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db = SessionLocal()
            try:
                cli = db.query(models.Client).filter_by(id=self.current_client_id).first()
                if cli:
                    db.delete(cli)
                    db.commit()
                    self.clear_form()
                    self.load_clients()
                    QMessageBox.information(self, "Éxito", "Cliente eliminado.")
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", "No se pudo eliminar el cliente. Es posible que tenga facturas asociadas.")
            finally:
                db.close()
        
    def auto_format_thousands(self, text, line_edit):
        """Format number with commas dynamically while typing."""
        line_edit.blockSignals(True)
        cursor_pos = line_edit.cursorPosition()
        
        # Guardar longitud original para ajustar cursor
        old_len = len(text)
        
        # Eliminar todo excepto dígitos
        clean_text = ''.join(c for c in text if c.isdigit())
        
        if clean_text:
            try:
                # Formatear con comas
                formatted = f"{int(clean_text):,}"
                line_edit.setText(formatted)
                
                # Ajustar posición del cursor
                new_len = len(formatted)
                new_cursor_pos = cursor_pos + (new_len - old_len)
                line_edit.setCursorPosition(max(0, new_cursor_pos))
            except ValueError:
                pass
        else:
            line_edit.setText("")
            
        line_edit.blockSignals(False)
