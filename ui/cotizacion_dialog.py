from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from database import SessionLocal
import models
import datetime

class CotizacionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cotización de Monedas (En Guaraníes)")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Cotización de monedas respecto al Guaraní (PYG)
        self.txt_usd = QLineEdit()
        self.txt_brl = QLineEdit()
        self.txt_ars = QLineEdit()
        
        form_layout.addRow("Dólar (USD):", self.txt_usd)
        form_layout.addRow("Real (BRL):", self.txt_brl)
        form_layout.addRow("Peso (ARS):", self.txt_ars)
        
        layout.addLayout(form_layout)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar_cotizacion)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        self.cargar_cotizaciones_actuales()

    def cargar_cotizaciones_actuales(self):
        db = SessionLocal()
        # Traer solo las activas
        rates = {r.currency_code: r.buy_rate for r in db.query(models.CurrencyRate).filter_by(is_active=True).all()}
        db.close()
        
        self.txt_usd.setText(f"{float(rates.get('USD', 7500.0)):.0f}")
        self.txt_brl.setText(f"{float(rates.get('BRL', 1500.0)):.0f}")
        self.txt_ars.setText(f"{float(rates.get('ARS', 10.0)):.0f}")

    def guardar_cotizacion(self):
        try:
            usd = float(self.txt_usd.text())
            brl = float(self.txt_brl.text())
            ars = float(self.txt_ars.text())
            
            db = SessionLocal()
            
            for code, rate in [("USD", usd), ("BRL", brl), ("ARS", ars)]:
                # Chequear si cambió respecto a la actual
                current = db.query(models.CurrencyRate).filter_by(currency_code=code, is_active=True).first()
                if not current or float(current.buy_rate) != rate:
                    # Desactivar anterior
                    if current:
                        current.is_active = False
                    
                    # Insertar nueva
                    new_rate = models.CurrencyRate(
                        currency_code=code,
                        buy_rate=rate,
                        sell_rate=rate,
                        created_at=datetime.datetime.now(),
                        is_active=True
                    )
                    db.add(new_rate)
            
            db.commit()
            db.close()
            
            QMessageBox.information(self, "Éxito", "Cotizaciones guardadas correctamente.")
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingresa valores numéricos válidos.")
