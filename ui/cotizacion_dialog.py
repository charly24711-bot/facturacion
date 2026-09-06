from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from database import SessionLocal
import models
import datetime
from decimal import Decimal, InvalidOperation

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
        
        usd_val = rates.get('USD', Decimal('7500'))
        brl_val = rates.get('BRL', Decimal('1500'))
        ars_val = rates.get('ARS', Decimal('10'))
        
        self.txt_usd.setText(f"{Decimal(str(usd_val)):.0f}")
        self.txt_brl.setText(f"{Decimal(str(brl_val)):.0f}")
        self.txt_ars.setText(f"{Decimal(str(ars_val)):.0f}")

    def guardar_cotizacion(self):
        try:
            usd = Decimal(self.txt_usd.text().strip().replace(',', '.'))
            brl = Decimal(self.txt_brl.text().strip().replace(',', '.'))
            ars = Decimal(self.txt_ars.text().strip().replace(',', '.'))
            
            db = SessionLocal()
            
            # Asegurar que las monedas base existan en la tabla currencies
            for cur_code, cur_name, cur_sym, cur_dec, cur_base in [
                ("PYG", "Guaraní", "Gs", 0, True),
                ("USD", "Dólar Americano", "US$", 2, False),
                ("BRL", "Real Brasileño", "R$", 2, False),
                ("ARS", "Peso Argentino", "$", 2, False),
            ]:
                if not db.query(models.Currency).filter_by(code=cur_code).first():
                    db.add(models.Currency(
                        code=cur_code, name=cur_name, symbol=cur_sym, decimals=cur_dec, is_base=cur_base
                    ))
            db.flush()
            
            for code, rate in [("USD", usd), ("BRL", brl), ("ARS", ars)]:
                # Chequear si cambió respecto a la actual
                current = db.query(models.CurrencyRate).filter_by(currency_code=code, is_active=True).first()
                if not current or Decimal(str(current.buy_rate)) != rate:
                    # Desactivar anterior (registro inmutable, nunca UPDATE destructivo de cotización)
                    if current:
                        current.is_active = False
                    
                    # Insertar nuevo registro
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
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Error", "Por favor ingresa valores numéricos válidos.")
