from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from database import SessionLocal
import models

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
        rates = {r.currency: r.rate_to_pyg for r in db.query(models.ExchangeRate).all()}
        db.close()
        
        self.txt_usd.setText(str(rates.get("USD", 7500.0)))
        self.txt_brl.setText(str(rates.get("BRL", 1500.0)))
        self.txt_ars.setText(str(rates.get("ARS", 10.0)))

    def guardar_cotizacion(self):
        try:
            usd = float(self.txt_usd.text())
            brl = float(self.txt_brl.text())
            ars = float(self.txt_ars.text())
            
            db = SessionLocal()
            
            # Actualizar o crear Dólar
            rate_usd = db.query(models.ExchangeRate).filter_by(currency="USD").first()
            if not rate_usd:
                rate_usd = models.ExchangeRate(currency="USD")
                db.add(rate_usd)
            rate_usd.rate_to_pyg = usd
            
            # Actualizar o crear Real
            rate_brl = db.query(models.ExchangeRate).filter_by(currency="BRL").first()
            if not rate_brl:
                rate_brl = models.ExchangeRate(currency="BRL")
                db.add(rate_brl)
            rate_brl.rate_to_pyg = brl
            
            # Actualizar o crear Peso
            rate_ars = db.query(models.ExchangeRate).filter_by(currency="ARS").first()
            if not rate_ars:
                rate_ars = models.ExchangeRate(currency="ARS")
                db.add(rate_ars)
            rate_ars.rate_to_pyg = ars
            
            db.commit()
            db.close()
            
            QMessageBox.information(self, "Éxito", "Cotizaciones guardadas correctamente en la base de datos.")
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor ingresa valores numéricos válidos.")
