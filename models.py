from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    id = Column(Integer, primary_key=True, index=True)
    currency = Column(String(3), unique=True, index=True) # USD, BRL, ARS
    rate_to_pyg = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    
class Brand(Base):
    __tablename__ = 'brands'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    art_codigo = Column(String(6), unique=True, index=True) 
    art_descri = Column(String(100)) 
    art_cbarra = Column(String(20)) # Código principal
    art_costo = Column(Float, default=0.0) 
    art_preven = Column(Float, default=0.0) 
    art_codmnd = Column(String(2)) 
    art_impu = Column(Float, default=10.0) 
    art_stkmin = Column(Integer, default=10)
    art_stkmax = Column(Integer, default=200)
    art_stkini = Column(Integer, default=0) 
    
    # Nuevos campos de Supermercado
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=True)
    uom = Column(String(20), default="Un") # Unidad de medida
    is_fractional = Column(Boolean, default=False)
    location = Column(String(100))
    is_active = Column(Boolean, default=True)
    
    category = relationship("Category")
    brand = relationship("Brand")
    barcodes = relationship("ProductBarcode", back_populates="product", cascade="all, delete-orphan")
    batches = relationship("ProductBatch", back_populates="product", cascade="all, delete-orphan")

class ProductBarcode(Base):
    """Códigos de barra alternativos (Packs, Cajas)"""
    __tablename__ = 'product_barcodes'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    barcode = Column(String(50), index=True, unique=True)
    factor_conversion = Column(Float, default=1.0) # Si es caja de 6, factor=6
    
    product = relationship("Product", back_populates="barcodes")

class ProductBatch(Base):
    """Lotes y Vencimientos"""
    __tablename__ = 'product_batches'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    lote = Column(String(50))
    fecha_vencimiento = Column(DateTime)
    stock_actual = Column(Float, default=0.0)
    
    product = relationship("Product", back_populates="batches")

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, index=True)
    cli_codigo = Column(String(6), unique=True, index=True) 
    cli_nombre = Column(String(60), nullable=False) 
    cli_ruc = Column(String(30)) 
    cli_ci = Column(String(20)) 
    cli_direcc = Column(String(150)) 
    cli_telefo = Column(String(100)) 
    cli_limite = Column(Float, default=0.0) 

class Invoice(Base):
    """Cabecera de Factura/Venta basado en aventa.dbf"""
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True, index=True)
    ven_numero = Column(Integer, unique=True, index=True) # VEN_NUMERO
    ven_fecha = Column(DateTime, default=datetime.datetime.utcnow) # VEN_FECHA
    ven_codcli = Column(String(6), ForeignKey('clients.cli_codigo')) # VEN_CODCLI
    ven_total = Column(Float, default=0.0) # VEN_TOTAL
    ven_codmnd = Column(String(2)) # VEN_CODMND
    ven_estado = Column(String(1), default='A') # VEN_ESTADO (A=Activo, N=Anulado)
    
    client = relationship("Client")
    items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")

class InvoiceItem(Base):
    """Detalle de Factura/Venta basado en avenitem.dbf"""
    __tablename__ = 'invoice_items'
    id = Column(Integer, primary_key=True, index=True)
    vit_numero = Column(Integer, ForeignKey('invoices.ven_numero')) # VIT_NUMERO
    vit_articu = Column(String(6), ForeignKey('products.art_codigo')) # VIT_ARTICU
    vit_canti = Column(Float, nullable=False) # VIT_CANTI
    vit_precio = Column(Float, nullable=False) # VIT_PRECIO
    
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")

class Payment(Base):
    """Cobranza basada en cobranza.dbf"""
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    cob_numero = Column(Integer, unique=True, index=True) # COB_NUMERO
    cob_fecha = Column(DateTime, default=datetime.datetime.utcnow) # COB_FECHA
    cob_monto = Column(Float, nullable=False) # COB_MONTO
    cob_vennro = Column(Integer, ForeignKey('invoices.ven_numero')) # COB_VENNRO
    cob_mndori = Column(String(2)) # COB_MNDORI (Moneda en que se pagó: USD, BRL, ARS, PYG)
    
    invoice = relationship("Invoice", back_populates="payments")

class CompanySettings(Base):
    __tablename__ = 'company_settings'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    ruc = Column(String(30))
    direccion = Column(String(150))
    telefono = Column(String(50))
    tipo_negocio = Column(String(50), default="Comercio") # Comercio, Restaurante, Servicios

class Remission(Base):
    """Nota de Remisión (F7)"""
    __tablename__ = 'remissions'
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    codcli = Column(String(6), ForeignKey('clients.cli_codigo'))
    total_pyg = Column(Float, default=0.0)
    estado = Column(String(1), default='A') # A=Activo, N=Anulado
    
    client = relationship("Client")
    items = relationship("RemissionItem", back_populates="remission")

class RemissionItem(Base):
    __tablename__ = 'remission_items'
    id = Column(Integer, primary_key=True, index=True)
    remission_id = Column(Integer, ForeignKey('remissions.id'))
    articu = Column(String(6), ForeignKey('products.art_codigo'))
    canti = Column(Float, nullable=False)
    precio = Column(Float, nullable=False)
    
    remission = relationship("Remission", back_populates="items")
    product = relationship("Product")
