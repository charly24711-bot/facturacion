from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QGridLayout, QCompleter, QAbstractItemView, QInputDialog
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QColor, QFont

from database import SessionLocal
import models
import datetime


class CustomerAccountsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏦 Cuenta Corriente (Fiado y Cobranzas)")
        self.resize(900, 600)
        self.current_client_id = None
        self.setup_ui()

    def setup_ui(self):
        main = QVBoxLayout(self)

        # ── Buscador de Cliente ────────────────────────────────────────────
        grp_cli = QGroupBox("Buscar Cliente")
        cli_layout = QHBoxLayout()

        self.txt_cli = QLineEdit()
        self.txt_cli.setPlaceholderText("Buscar por nombre, código o RUC [Enter]")
        self.txt_cli.returnPressed.connect(self.buscar_cliente)

        self._cmodel = QStringListModel()
        comp = QCompleter(self._cmodel, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.activated.connect(self._auto_buscar)
        self.txt_cli.setCompleter(comp)
        self._load_clients_completer()

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.clicked.connect(self.buscar_cliente)

        cli_layout.addWidget(self.txt_cli, stretch=1)
        cli_layout.addWidget(btn_buscar)
        grp_cli.setLayout(cli_layout)
        main.addWidget(grp_cli)

        # ── Resumen de Cuenta ──────────────────────────────────────────────
        grp_resumen = QGroupBox("Estado de Cuenta")
        resumen_layout = QGridLayout()

        self.lbl_nombre = QLabel("Cliente: —")
        self.lbl_nombre.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.lbl_limite = QLabel("Límite de Crédito: ₲ 0")
        
        self.lbl_saldo = QLabel("SALDO ACTUAL: ₲ 0")
        self.lbl_saldo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2980b9;")

        btn_cobrar = QPushButton("💰 Registrar Pago (Recibo)")
        btn_cobrar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        btn_cobrar.clicked.connect(self.registrar_pago)

        resumen_layout.addWidget(self.lbl_nombre, 0, 0)
        resumen_layout.addWidget(self.lbl_limite, 0, 1)
        resumen_layout.addWidget(self.lbl_saldo, 1, 0)
        resumen_layout.addWidget(btn_cobrar, 1, 1, Qt.AlignmentFlag.AlignRight)

        grp_resumen.setLayout(resumen_layout)
        main.addWidget(grp_resumen)

        # ── Extracto ───────────────────────────────────────────────────────
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Fecha", "Operación", "Referencia", "Monto (₲)", "Saldo Acum. (₲)"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        main.addWidget(self.table, stretch=1)

    # ── Helpers ────────────────────────────────────────────────────────────
    def _load_clients_completer(self):
        db = SessionLocal()
        clientes = db.query(models.Client).all()
        self._cmodel.setStringList([f"{c.cli_codigo} - {c.cli_nombre}" for c in clientes])
        db.close()

    def _auto_buscar(self):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.buscar_cliente)

    def buscar_cliente(self):
        q = self.txt_cli.text().strip()
        if not q:
            return
        codigo = q.split(" - ")[0].strip() if " - " in q else q
        db = SessionLocal()
        cli = db.query(models.Client).filter(
            (models.Client.cli_codigo == codigo) |
            (models.Client.cli_nombre.ilike(f"%{codigo}%")) |
            (models.Client.cli_ruc == codigo)
        ).first()

        if cli:
            self.current_client_id = cli.id
            self.lbl_nombre.setText(f"Cliente: {cli.cli_nombre} ({cli.cli_codigo})")
            self.lbl_limite.setText(f"Límite de Crédito: ₲ {float(cli.cli_limite):,.0f}")
            self.load_extracto()
        else:
            self.current_client_id = None
            self.lbl_nombre.setText("Cliente: — No encontrado —")
            self.lbl_limite.setText("Límite de Crédito: ₲ 0")
            self.lbl_saldo.setText("SALDO ACTUAL: ₲ 0")
            self.table.setRowCount(0)
        db.close()

    def load_extracto(self):
        if not self.current_client_id:
            return
        self.table.setRowCount(0)
        db = SessionLocal()
        
        # Traer transacciones en orden cronológico
        trx = (db.query(models.CustomerTransaction)
                 .filter_by(client_id=self.current_client_id)
                 .order_by(models.CustomerTransaction.fecha.asc())
                 .all())
        
        saldo_acumulado = 0.0
        
        for t in trx:
            monto = float(t.monto)
            if t.tipo == 'CHARGE':
                # Cargo suma a la deuda
                saldo_acumulado += monto
                operacion = "📈 Venta a Crédito"
                color = QColor("#c0392b") # Rojo
                monto_str = f"+ {monto:,.0f}"
            else:
                # Pago resta a la deuda
                saldo_acumulado -= monto
                operacion = "💰 Recibo de Pago"
                color = QColor("#27ae60") # Verde
                monto_str = f"- {monto:,.0f}"

            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(t.fecha.strftime("%d/%m/%Y %H:%M")))
            self.table.setItem(row, 1, QTableWidgetItem(operacion))
            self.table.setItem(row, 2, QTableWidgetItem(t.referencia or ""))
            
            i_monto = QTableWidgetItem(monto_str)
            i_monto.setForeground(color)
            f = i_monto.font()
            f.setBold(True)
            i_monto.setFont(f)
            self.table.setItem(row, 3, i_monto)
            
            self.table.setItem(row, 4, QTableWidgetItem(f"{saldo_acumulado:,.0f}"))
            
        self.lbl_saldo.setText(f"SALDO ACTUAL: ₲ {saldo_acumulado:,.0f}")
        
        if saldo_acumulado > 0:
            self.lbl_saldo.setStyleSheet("font-size: 16px; font-weight: bold; color: #c0392b;") # Debe
        else:
            self.lbl_saldo.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;") # A favor o cero

        # Hacer scroll hasta el final
        if self.table.rowCount() > 0:
            self.table.scrollToBottom()

        db.close()

    def registrar_pago(self):
        if not self.current_client_id:
            QMessageBox.warning(self, "Error", "Seleccione un cliente primero.")
            return
            
        monto_str, ok = QInputDialog.getText(
            self, "Registrar Pago", 
            "Ingrese el monto entregado por el cliente (₲):"
        )
        if ok and monto_str:
            try:
                monto = float(monto_str.replace(",", "").replace(".", ""))
                if monto <= 0:
                    raise ValueError
            except:
                QMessageBox.warning(self, "Error", "Monto inválido.")
                return
                
            db = SessionLocal()
            pago = models.CustomerTransaction(
                client_id=self.current_client_id,
                tipo='PAYMENT',
                monto=monto,
                referencia="Pago en caja"
            )
            db.add(pago)
            db.commit()
            db.close()
            
            QMessageBox.information(self, "Éxito", f"Pago de ₲ {monto:,.0f} registrado correctamente.")
            self.load_extracto()
