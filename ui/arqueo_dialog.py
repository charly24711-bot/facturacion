from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QHBoxLayout, QMessageBox, QLabel, QGroupBox, QGridLayout, QTextEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import SessionLocal
import models
from decimal import Decimal
import datetime

class ArqueoDialog(QDialog):
    def __init__(self, session_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Arqueo Ciego y Reporte Z")
        self.resize(500, 500)
        
        self.session_id = session_id
        
        # Diccionarios para almacenar los QLineEdit de las declaraciones
        self.inputs_efectivo = {}
        self.inputs_digitales = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        lbl_title = QLabel("DECLARACIÓN DE VALORES (ARQUEO CIEGO)")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        main_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel("Ingrese la cantidad de dinero contada físicamente en la caja.")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_desc)
        
        # Grupo Efectivo
        grp_efectivo = QGroupBox("Billetes y Monedas (Efectivo)")
        layout_efec = QFormLayout(grp_efectivo)
        
        monedas = ["PYG", "USD", "BRL", "ARS"]
        for m in monedas:
            txt = QLineEdit("0")
            self.inputs_efectivo[m] = txt
            layout_efec.addRow(f"Efectivo {m}:", txt)
        main_layout.addWidget(grp_efectivo)
        
        # Grupo Digitales
        grp_digital = QGroupBox("Vouchers y Transferencias")
        layout_digi = QFormLayout(grp_digital)
        
        # Simplificación: Asumimos que Tarjetas entran en PYG y PIX en BRL
        digis = [("Tarjeta Crédito", "PYG"), ("Tarjeta Débito", "PYG"), ("PIX", "BRL"), ("Transferencia Bancaria", "PYG")]
        for met, mon in digis:
            txt = QLineEdit("0")
            self.inputs_digitales[(met, mon)] = txt
            layout_digi.addRow(f"{met} ({mon}):", txt)
        main_layout.addWidget(grp_digital)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_cierre = QPushButton("EJECUTAR CIERRE Z")
        btn_cierre.setStyleSheet("background-color: darkred; color: white; font-weight: bold; padding: 15px;")
        btn_cierre.clicked.connect(self.procesar_cierre)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_cierre)
        main_layout.addLayout(btn_layout)

    def procesar_cierre(self):
        # Advertencia final
        reply = QMessageBox.warning(self, "Confirmación Irreversible", 
                                    "Al ejecutar el Cierre Z no podrás modificar la declaración.\n¿Continuar?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        db = SessionLocal()
        try:
            # 1. Recolectar lo declarado
            declaraciones = {}
            for m, txt in self.inputs_efectivo.items():
                val = txt.text().replace(',', '').strip()
                val = val if val else "0"
                declaraciones[('Efectivo', m)] = Decimal(val)
                
            for (met, m), txt in self.inputs_digitales.items():
                val = txt.text().replace(',', '').strip()
                val = val if val else "0"
                declaraciones[(met, m)] = Decimal(val)
                
            # 2. Calcular Teórico
            session = db.query(models.CashSession).filter_by(id=self.session_id).first()
            if not session:
                raise Exception("Sesión inválida")
                
            pagos = db.query(models.Payment).filter_by(session_id=self.session_id).all()
            
            teoricos = {}
            for p in pagos:
                key = (p.cob_metodo, p.cob_mndori)
                teoricos[key] = teoricos.get(key, Decimal("0")) + p.cob_monto
                
            # Factoring de Movimientos de Caja (Fondo Inicial y Sangrías)
            movimientos = db.query(models.CashMovement).filter_by(session_id=self.session_id).all()
            for m in movimientos:
                key = ('Efectivo', m.moneda)
                if m.tipo in ('FONDO_INICIAL', 'INGRESO'):
                    teoricos[key] = teoricos.get(key, Decimal("0")) + m.monto
                elif m.tipo in ('RETIRO_SANGRIA', 'EGRESO'):
                    teoricos[key] = teoricos.get(key, Decimal("0")) - m.monto
                
            # 3. Comparar y crear Auditoría
            reporte_txt = f"=== REPORTE Z - SESIÓN {session.id} ===\n\n"
            if movimientos:
                reporte_txt += "--- MOVIMIENTOS DE CAJA (FONDOS / SANGRÍAS) ---\n"
                for m in movimientos:
                    signo = "+" if m.tipo in ('FONDO_INICIAL', 'INGRESO') else "-"
                    reporte_txt += f"  [{m.tipo}] {signo}{m.monto:,.2f} {m.moneda} ({m.concepto})\n"
                reporte_txt += "------------------------------------------------\n\n"
            
            # Obtener todas las keys combinadas
            todas_keys = set(declaraciones.keys()).union(set(teoricos.keys()))
            
            for met, mon in todas_keys:
                dec = declaraciones.get((met, mon), Decimal("0"))
                teo = teoricos.get((met, mon), Decimal("0"))
                dif = dec - teo
                
                # Guardar Auditoria
                audit = models.CashAudit(
                    session_id=session.id,
                    moneda=mon,
                    metodo=met,
                    monto_declarado=dec,
                    monto_teorico=teo,
                    diferencia=dif
                )
                db.add(audit)
                
                if teo > 0 or dec > 0:
                    reporte_txt += f"[{met} - {mon}]\n"
                    reporte_txt += f"  Teórico:   {teo:,.2f}\n"
                    reporte_txt += f"  Declarado: {dec:,.2f}\n"
                    reporte_txt += f"  Diferencia: {dif:,.2f}\n\n"
                    
            # 4. Cerrar Sesión
            session.status = 'CLOSED'
            session.closed_at = datetime.datetime.utcnow()
            
            db.commit()
            
            # 5. Mostrar Reporte Z en pantalla
            msg = QMessageBox(self)
            msg.setWindowTitle("Reporte Z Finalizado")
            msg.setText("Cierre Z ejecutado correctamente.\nSe ha cerrado la sesión actual.")
            msg.setDetailedText(reporte_txt)
            msg.exec()
            
            self.accept()
            
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Error al cerrar la caja: {e}")
        finally:
            db.close()
