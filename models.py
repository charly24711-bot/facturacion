from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Numeric, event
from sqlalchemy.orm import relationship, declared_attr
from database import Base
import datetime
import uuid
import json

class SyncableModel:
    @declared_attr
    def uuid(cls):
        return Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)

    @declared_attr
    def synced(cls):
        return Column(Boolean, default=False)

    @declared_attr
    def synced_at(cls):
        return Column(DateTime, nullable=True)

class SyncOutbox(Base):
    __tablename__ = 'sync_outbox'
    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String(50), nullable=False)
    entity_uuid = Column(String(36), nullable=False)
    action = Column(String(10), nullable=False) # INSERT or UPDATE
    payload_json = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    synced = Column(Boolean, default=False)


class Currency(Base):
    __tablename__ = 'currencies'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, index=True)
    name = Column(String(50))
    symbol = Column(String(5))
    decimals = Column(Integer, default=2)
    is_base = Column(Boolean, default=False)

class CurrencyRate(Base):
    __tablename__ = 'currency_rates'
    id = Column(Integer, primary_key=True, index=True)
    currency_code = Column(String(3), ForeignKey('currencies.code'))
    buy_rate = Column(Numeric(asdecimal=True), nullable=False)
    sell_rate = Column(Numeric(asdecimal=True), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

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
    art_costo = Column(Numeric(asdecimal=True), default=0.0) 
    art_preven = Column(Numeric(asdecimal=True), default=0.0) 
    art_codmnd = Column(String(2)) 
    art_impu = Column(Numeric(asdecimal=True), default=10.0) 
    art_stkmin = Column(Numeric(asdecimal=True), default=10)
    art_stkmax = Column(Numeric(asdecimal=True), default=200)
    art_stkini = Column(Numeric(asdecimal=True), default=0) 
    
    # Nuevos campos de Supermercado
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=True)
    uom = Column(String(20), default="Un") # Unidad de medida
    is_fractional = Column(Boolean, default=False)
    location = Column(String(100))
    is_active = Column(Boolean, default=True)
    image_path = Column(String(255), nullable=True)
    
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
    factor_conversion = Column(Numeric(asdecimal=True), default=1.0) # Si es caja de 6, factor=6
    
    product = relationship("Product", back_populates="barcodes")

class ProductBatch(Base):
    """Lotes y Vencimientos"""
    __tablename__ = 'product_batches'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    lote = Column(String(50))
    fecha_vencimiento = Column(DateTime)
    stock_actual = Column(Numeric(asdecimal=True), default=0.0)
    
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
    cli_limite = Column(Numeric(asdecimal=True), default=0.0) 
    price_list_id = Column(Integer, ForeignKey('price_lists.id'), nullable=True)
    
    price_list = relationship("PriceList")
    transactions = relationship("CustomerTransaction", back_populates="client") 

class CustomerTransaction(SyncableModel, Base):
    """Transacciones de la cuenta corriente del cliente"""
    __tablename__ = 'customer_transactions'
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    tipo = Column(String(10), nullable=False) # CHARGE (deuda por compra), PAYMENT (pago/recibo)
    monto = Column(Numeric(asdecimal=True), nullable=False)
    referencia = Column(String(100)) # Nro de Factura o Recibo
    
    client = relationship("Client", back_populates="transactions")

class Invoice(SyncableModel, Base):
    """Cabecera de Factura/Venta basado en aventa.dbf"""
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True, index=True)
    ven_tipo = Column(String(2), default='FA') # FA=Factura, NC=Nota de Credito
    ven_numero = Column(Integer, unique=True, index=True) # VEN_NUMERO
    ven_fecha = Column(DateTime, default=datetime.datetime.utcnow) # VEN_FECHA
    ven_codcli = Column(String(6), ForeignKey('clients.cli_codigo')) # VEN_CODCLI
    ven_total = Column(Numeric(asdecimal=True), default=0.0) # VEN_TOTAL
    ven_codmnd = Column(String(2)) # VEN_CODMND
    ven_estado = Column(String(1), default='A') # VEN_ESTADO (A=Activo, N=Anulado)
    
    client = relationship("Client")
    items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")

class InvoiceItem(SyncableModel, Base):
    """Detalle de Factura/Venta basado en avenitem.dbf"""
    __tablename__ = 'invoice_items'
    id = Column(Integer, primary_key=True, index=True)
    vit_numero = Column(Integer, ForeignKey('invoices.ven_numero')) # VIT_NUMERO
    vit_articu = Column(String(6), ForeignKey('products.art_codigo')) # VIT_ARTICU
    vit_canti = Column(Numeric(asdecimal=True), nullable=False) # VIT_CANTI
    vit_precio = Column(Numeric(asdecimal=True), nullable=False) # VIT_PRECIO
    
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")

class Payment(SyncableModel, Base):
    """Cobranza basada en cobranza.dbf"""
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    cob_numero = Column(Integer, unique=True, index=True) # COB_NUMERO
    cob_fecha = Column(DateTime, default=datetime.datetime.utcnow) # COB_FECHA
    cob_monto = Column(Numeric(asdecimal=True), nullable=False) # COB_MONTO
    cob_vennro = Column(Integer, ForeignKey('invoices.ven_numero')) # COB_VENNRO
    cob_mndori = Column(String(3)) # COB_MNDORI (USD, BRL, ARS, PYG)
    cob_metodo = Column(String(20), default='Efectivo') # Efectivo, Tarjeta, PIX
    cob_monto_pyg = Column(Numeric(asdecimal=True), default=0.0) # Monto equivalente en PYG
    session_id = Column(Integer, ForeignKey('cash_sessions.id'), nullable=True)
    
    invoice = relationship("Invoice", back_populates="payments")
    session = relationship("CashSession", back_populates="payments")


class CashSession(SyncableModel, Base):
    __tablename__ = 'cash_sessions'
    id = Column(Integer, primary_key=True, index=True)
    opened_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    status = Column(String(10), default='OPEN') # OPEN, CLOSED
    user_id = Column(Integer, default=1) # Hardcoded for now
    
    payments = relationship("Payment", back_populates="session")
    audits = relationship("CashAudit", back_populates="session")

class CashAudit(SyncableModel, Base):
    __tablename__ = 'cash_audits'
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('cash_sessions.id'))
    moneda = Column(String(3)) # PYG, USD, BRL, ARS
    metodo = Column(String(20)) # Efectivo, Tarjeta, PIX
    monto_declarado = Column(Numeric(asdecimal=True), default=0.0)
    monto_teorico = Column(Numeric(asdecimal=True), default=0.0)
    diferencia = Column(Numeric(asdecimal=True), default=0.0)
    
    session = relationship("CashSession", back_populates="audits")


class Supplier(SyncableModel, Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True, index=True)
    sup_codigo = Column(String(50), unique=True, index=True)
    sup_nombre = Column(String(150), nullable=False)
    sup_ruc = Column(String(50))
    sup_telefo = Column(String(100))
    
    purchases = relationship("Purchase", back_populates="supplier")

class Purchase(SyncableModel, Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True, index=True)
    com_fecha = Column(DateTime, default=datetime.datetime.utcnow)
    com_provee = Column(Integer, ForeignKey('suppliers.id'))
    com_nrofac = Column(String(50))
    com_timbra = Column(String(50))
    com_total = Column(Numeric(asdecimal=True), default=0.0)
    
    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase")

class PurchaseItem(SyncableModel, Base):
    __tablename__ = 'purchase_items'
    id = Column(Integer, primary_key=True, index=True)
    cit_compra_id = Column(Integer, ForeignKey('purchases.id'))
    cit_articu = Column(String(50), ForeignKey('products.art_codigo'))
    cit_canti = Column(Numeric(asdecimal=True, precision=10, scale=3))
    cit_precio = Column(Numeric(asdecimal=True), default=0.0)
    
    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")



class ProductPromo(SyncableModel, Base):
    """Precio promocional temporal con vigencia"""
    __tablename__ = 'product_promos'
    id = Column(Integer, primary_key=True, index=True)
    pro_articu = Column(String(6), ForeignKey('products.art_codigo'), nullable=False)
    pro_precio = Column(Numeric(asdecimal=True), nullable=False)
    pro_desde = Column(DateTime, nullable=False)
    pro_hasta = Column(DateTime, nullable=False)
    pro_descri = Column(String(100))
    is_active = Column(Boolean, default=True)
    product = relationship("Product")

class PriceTier(Base):
    """Escalas de precio por volumen (cantidad minima -> precio especial)"""
    __tablename__ = 'price_tiers'
    id = Column(Integer, primary_key=True, index=True)
    pt_articu = Column(String(6), ForeignKey('products.art_codigo'), nullable=False)
    pt_qty_min = Column(Integer, nullable=False)
    pt_precio = Column(Numeric(asdecimal=True), nullable=False)
    pt_descri = Column(String(80))
    is_active = Column(Boolean, default=True)
    product = relationship("Product")

class PriceList(Base):
    """Lista de precios (Minorista / Mayorista / Distribuidor)"""
    __tablename__ = 'price_lists'
    id = Column(Integer, primary_key=True, index=True)
    pl_nombre = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False)
    items = relationship("PriceListItem", back_populates="price_list")

class PriceListItem(Base):
    """Precio de un producto en una lista especifica"""
    __tablename__ = 'price_list_items'
    id = Column(Integer, primary_key=True, index=True)
    pli_list_id = Column(Integer, ForeignKey('price_lists.id'), nullable=False)
    pli_articu = Column(String(6), ForeignKey('products.art_codigo'), nullable=False)
    pli_precio = Column(Numeric(asdecimal=True), nullable=False)
    price_list = relationship("PriceList", back_populates="items")
    product = relationship("Product")

class CompanySettings(Base):
    __tablename__ = 'company_settings'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    ruc = Column(String(30))
    direccion = Column(String(150))
    telefono = Column(String(50))
    tipo_negocio = Column(String(50), default="Comercio") # Comercio, Restaurante, Servicios

class Remission(SyncableModel, Base):
    """Nota de Remisión (F7)"""
    __tablename__ = 'remissions'
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    codcli = Column(String(6), ForeignKey('clients.cli_codigo'))
    total_pyg = Column(Numeric(asdecimal=True), default=0.0)
    estado = Column(String(1), default='A') # A=Activo, N=Anulado
    
    client = relationship("Client")
    items = relationship("RemissionItem", back_populates="remission")

class RemissionItem(SyncableModel, Base):
    __tablename__ = 'remission_items'
    id = Column(Integer, primary_key=True, index=True)
    remission_id = Column(Integer, ForeignKey('remissions.id'))
    articu = Column(String(6), ForeignKey('products.art_codigo'))
    canti = Column(Numeric(asdecimal=True), nullable=False)
    precio = Column(Numeric(asdecimal=True), nullable=False)
    
    remission = relationship("Remission", back_populates="items")
    product = relationship("Product")


def _model_to_dict(obj):
    d = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)
        if isinstance(val, datetime.datetime):
            d[column.name] = val.isoformat()
        elif isinstance(val, (int, float, str, bool, type(None))):
            d[column.name] = val
        else:
            d[column.name] = str(val) # For Decimal and others
    return d

def queue_sync_event(mapper, connection, target, action):
    # Avoid infinite loop if we are syncing or something
    if isinstance(target, SyncOutbox):
        return
        
    if not hasattr(target, 'uuid'):
        return
        
    payload = _model_to_dict(target)
    
    # We must execute an insert into sync_outbox using the connection
    outbox_table = SyncOutbox.__table__
    connection.execute(
        outbox_table.insert(),
        {
            "entity_name": target.__class__.__name__,
            "entity_uuid": target.uuid,
            "action": action,
            "payload_json": json.dumps(payload),
            "created_at": datetime.datetime.utcnow(),
            "synced": False
        }
    )

@event.listens_for(Invoice, 'after_insert')
@event.listens_for(InvoiceItem, 'after_insert')
@event.listens_for(Payment, 'after_insert')
@event.listens_for(Remission, 'after_insert')
@event.listens_for(RemissionItem, 'after_insert')
def receive_after_insert(mapper, connection, target):
    queue_sync_event(mapper, connection, target, 'INSERT')

@event.listens_for(Invoice, 'after_update')
@event.listens_for(InvoiceItem, 'after_update')
@event.listens_for(Payment, 'after_update')
@event.listens_for(Remission, 'after_update')
@event.listens_for(RemissionItem, 'after_update')
def receive_after_update(mapper, connection, target):
    # Only queue update if we are not just marking it as synced
    # (In a real scenario, we'd check if other fields changed)
    queue_sync_event(mapper, connection, target, 'UPDATE')

@event.listens_for(CashSession, 'after_insert')
@event.listens_for(CashAudit, 'after_insert')
def receive_after_insert_cash(mapper, connection, target):
    queue_sync_event(mapper, connection, target, 'INSERT')

@event.listens_for(CashSession, 'after_update')
@event.listens_for(CashAudit, 'after_update')
def receive_after_update_cash(mapper, connection, target):
    queue_sync_event(mapper, connection, target, 'UPDATE')


@event.listens_for(Supplier, 'after_insert')
@event.listens_for(Purchase, 'after_insert')
@event.listens_for(PurchaseItem, 'after_insert')
def receive_after_insert_purchases(mapper, connection, target):
    queue_sync_event(mapper, connection, target, 'INSERT')

@event.listens_for(Supplier, 'after_update')
@event.listens_for(Purchase, 'after_update')
@event.listens_for(PurchaseItem, 'after_update')
def receive_after_update_purchases(mapper, connection, target):
    queue_sync_event(mapper, connection, target, 'UPDATE')

