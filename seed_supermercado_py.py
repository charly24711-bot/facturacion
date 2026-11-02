"""
seed_supermercado_py.py
========================
Catálogo Semilla de Productos de Supermercado para Paraguay (Triple Frontera).
Carga masiva curada con marcas reales líderes del mercado paraguayo:
  - Lácteos (Trébol, Chortitzer, Los Colonos)
  - Yerbas y Té (Kurupí, Pajarito, Campesino, Colón)
  - Bebidas y Cervezas (Pilsen, Brahma, Pulp, Coca-Cola, Dasani)
  - Almacén y Granos (Tío Nico, Federal, Florencia, Miraflores, Azpa)
  - Limpieza y Cuidado Personal (Cavallaro, Activo, Zorro, Plusbelle)
  - Carnicería, Verdulería y Panadería (Balanza Fraccionada con EAN-13 prefijo 20/21)

Todas las tasas de IVA están calibradas según la Ley 6380/19 de Paraguay (10%, 5% Canasta Básica y Exentas).
Precios de venta y costos expresados en Guaraníes (PYG) con precisión Decimal estricta.
"""

import sys
import datetime
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from decimal import Decimal
from database import SessionLocal
import models

# Catálogo maestro paraguayo
CATALOGO_PARAGUAY = [
    # ── LÁCTEOS Y DERIVADOS (IVA 5% Canasta Básica) ─────────────────────────
    {
        "codigo": "784001001",
        "descri": "Leche Trébol Entera UHT 1L (Tetra)",
        "barcode": "7840010010012",
        "costo": Decimal("5200"),
        "precio": Decimal("6800"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("120"),
        "stock_min": Decimal("20"),
        "dias_venc": 90
    },
    {
        "codigo": "784001002",
        "descri": "Leche Trébol Descremada 0% UHT 1L",
        "barcode": "7840010010029",
        "costo": Decimal("5400"),
        "precio": Decimal("7200"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("80"),
        "stock_min": Decimal("15"),
        "dias_venc": 90
    },
    {
        "codigo": "784001003",
        "descri": "Leche Los Colonos Entera Pasteurizada 1L",
        "barcode": "7840010020011",
        "costo": Decimal("4900"),
        "precio": Decimal("6300"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("60"),
        "stock_min": Decimal("10"),
        "dias_venc": 20
    },
    {
        "codigo": "784001004",
        "descri": "Yogur Trébol con Pulpa de Frutilla 1Kg",
        "barcode": "7840010010036",
        "costo": Decimal("8500"),
        "precio": Decimal("11500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("45"),
        "stock_min": Decimal("8"),
        "dias_venc": 30
    },
    {
        "codigo": "784001005",
        "descri": "Manteca Chortitzer con Sal 200g",
        "barcode": "7840010030010",
        "costo": Decimal("9200"),
        "precio": Decimal("12800"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("50"),
        "stock_min": Decimal("10"),
        "dias_venc": 60
    },
    {
        "codigo": "784001006",
        "descri": "Dulce de Leche Los Colonos Familiar 400g",
        "barcode": "7840010020028",
        "costo": Decimal("8000"),
        "precio": Decimal("10900"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("35"),
        "stock_min": Decimal("6"),
        "dias_venc": 120
    },

    # ── YERBA MATE (IVA 5% Canasta Básica) ──────────────────────────────────
    {
        "codigo": "784002001",
        "descri": "Yerba Mate Kurupí Menta y Boldo 500g",
        "barcode": "7840020010019",
        "costo": Decimal("13500"),
        "precio": Decimal("18500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("150"),
        "stock_min": Decimal("25"),
        "dias_venc": 365
    },
    {
        "codigo": "784002002",
        "descri": "Yerba Mate Kurupí Clásica con Palo 500g",
        "barcode": "7840020010026",
        "costo": Decimal("12000"),
        "precio": Decimal("16500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("90"),
        "stock_min": Decimal("15"),
        "dias_venc": 365
    },
    {
        "codigo": "784002003",
        "descri": "Yerba Mate Pajarito Compuesta Selección Especial 500g",
        "barcode": "7840020020018",
        "costo": Decimal("14000"),
        "precio": Decimal("19000"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("100"),
        "stock_min": Decimal("20"),
        "dias_venc": 365
    },
    {
        "codigo": "784002004",
        "descri": "Yerba Mate Campesino Menta y Limón 500g",
        "barcode": "7840020030017",
        "costo": Decimal("13000"),
        "precio": Decimal("17500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("85"),
        "stock_min": Decimal("15"),
        "dias_venc": 365
    },
    {
        "codigo": "784002005",
        "descri": "Yerba Mate Colón Tradicional 1Kg",
        "barcode": "7840020040016",
        "costo": Decimal("21000"),
        "precio": Decimal("28500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("70"),
        "stock_min": Decimal("12"),
        "dias_venc": 365
    },

    # ── ALMACÉN Y GRANOS (IVA 5% / 10%) ────────────────────────────────────
    {
        "codigo": "784003001",
        "descri": "Arroz Tío Nico Tipo 1 Premium 1Kg",
        "barcode": "7840030010016",
        "costo": Decimal("5800"),
        "precio": Decimal("7900"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("200"),
        "stock_min": Decimal("30"),
        "dias_venc": 300
    },
    {
        "codigo": "784003002",
        "descri": "Arroz Tío Nico Tipo 1 Bolsa 5Kg",
        "barcode": "7840030010054",
        "costo": Decimal("27500"),
        "precio": Decimal("36500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("90"),
        "stock_min": Decimal("15"),
        "dias_venc": 300
    },
    {
        "codigo": "784003003",
        "descri": "Fideo Federal Tallarín Nro 3 400g",
        "barcode": "7840030020015",
        "costo": Decimal("3200"),
        "precio": Decimal("4600"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("180"),
        "stock_min": Decimal("25"),
        "dias_venc": 240
    },
    {
        "codigo": "784003004",
        "descri": "Fideo Anita Nido Cinta Ancha 500g",
        "barcode": "7840030020022",
        "costo": Decimal("4800"),
        "precio": Decimal("6700"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("120"),
        "stock_min": Decimal("20"),
        "dias_venc": 240
    },
    {
        "codigo": "784003005",
        "descri": "Harina de Trigo Florencia 000 1Kg",
        "barcode": "7840030030014",
        "costo": Decimal("4100"),
        "precio": Decimal("5800"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("160"),
        "stock_min": Decimal("25"),
        "dias_venc": 180
    },
    {
        "codigo": "784003006",
        "descri": "Harina de Trigo Florencia Leudante 1Kg",
        "barcode": "7840030030021",
        "costo": Decimal("5200"),
        "precio": Decimal("7300"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("80"),
        "stock_min": Decimal("15"),
        "dias_venc": 180
    },
    {
        "codigo": "784003007",
        "descri": "Aceite de Soja Miraflores Pet 900ml",
        "barcode": "7840030040013",
        "costo": Decimal("8200"),
        "precio": Decimal("11200"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("140"),
        "stock_min": Decimal("20"),
        "dias_venc": 365
    },
    {
        "codigo": "784003008",
        "descri": "Aceite de Girasol Primor Pet 1.5L",
        "barcode": "7840030040020",
        "costo": Decimal("15000"),
        "precio": Decimal("20500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("75"),
        "stock_min": Decimal("12"),
        "dias_venc": 365
    },
    {
        "codigo": "784003009",
        "descri": "Azúcar Blanco Refinado Azpa 1Kg",
        "barcode": "7840030050012",
        "costo": Decimal("4800"),
        "precio": Decimal("6500"),
        "iva": Decimal("5"),
        "fraccionado": False,
        "stock": Decimal("220"),
        "stock_min": Decimal("30"),
        "dias_venc": 365
    },
    {
        "codigo": "784003010",
        "descri": "Sal Fina Yodada Lobos 500g",
        "barcode": "7840030060011",
        "costo": Decimal("1500"),
        "precio": Decimal("2500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("150"),
        "stock_min": Decimal("20"),
        "dias_venc": 720
    },
    {
        "codigo": "784003011",
        "descri": "Extracto de Tomate Mallo Lata 70g",
        "barcode": "7840030070010",
        "costo": Decimal("1800"),
        "precio": Decimal("2800"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("200"),
        "stock_min": Decimal("25"),
        "dias_venc": 365
    },
    {
        "codigo": "784003012",
        "descri": "Atún Desmenuzado en Aceite Robinson Crusoe 170g",
        "barcode": "7840030080019",
        "costo": Decimal("6500"),
        "precio": Decimal("9200"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("110"),
        "stock_min": Decimal("15"),
        "dias_venc": 720
    },

    # ── BEBIDAS, GASEOSAS Y CERVEZAS (IVA 10%) ─────────────────────────────
    {
        "codigo": "784004001",
        "descri": "Gaseosa Pulp Pomelo Retornable 1.5L",
        "barcode": "7840040010013",
        "costo": Decimal("5500"),
        "precio": Decimal("7500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("100"),
        "stock_min": Decimal("20"),
        "dias_venc": 180
    },
    {
        "codigo": "784004002",
        "descri": "Gaseosa Pulp Naranja Botella Pet 2L",
        "barcode": "7840040010020",
        "costo": Decimal("7200"),
        "precio": Decimal("9800"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("85"),
        "stock_min": Decimal("15"),
        "dias_venc": 180
    },
    {
        "codigo": "784004003",
        "descri": "Gaseosa Coca-Cola Sabor Original Pet 2L",
        "barcode": "7840040020012",
        "costo": Decimal("10500"),
        "precio": Decimal("14000"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("160"),
        "stock_min": Decimal("30"),
        "dias_venc": 180
    },
    {
        "codigo": "784004004",
        "descri": "Gaseosa Coca-Cola Sin Azúcar Pet 500ml",
        "barcode": "7840040020029",
        "costo": Decimal("4000"),
        "precio": Decimal("5500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("120"),
        "stock_min": Decimal("20"),
        "dias_venc": 180
    },
    {
        "codigo": "784004005",
        "descri": "Agua Mineral Sin Gas Dasani 2L",
        "barcode": "7840040030011",
        "costo": Decimal("3500"),
        "precio": Decimal("5000"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("140"),
        "stock_min": Decimal("25"),
        "dias_venc": 365
    },
    {
        "codigo": "784004006",
        "descri": "Cerveza Pilsen Botella 940ml (La Rubia)",
        "barcode": "7840040040010",
        "costo": Decimal("7800"),
        "precio": Decimal("10500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("250"),
        "stock_min": Decimal("40"),
        "dias_venc": 180
    },
    {
        "codigo": "784004007",
        "descri": "Cerveza Pilsen Lata 354ml Pack x6",
        "barcode": "7840040040027",
        "costo": Decimal("26000"),
        "precio": Decimal("34000"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("90"),
        "stock_min": Decimal("15"),
        "dias_venc": 180
    },
    {
        "codigo": "784004008",
        "descri": "Cerveza Munich Chopp Lata 473ml",
        "barcode": "7840040050019",
        "costo": Decimal("4600"),
        "precio": Decimal("6500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("130"),
        "stock_min": Decimal("20"),
        "dias_venc": 180
    },
    {
        "codigo": "784004009",
        "descri": "Cerveza Brahma Chopp Botella 940ml",
        "barcode": "7840040060018",
        "costo": Decimal("8200"),
        "precio": Decimal("11000"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("180"),
        "stock_min": Decimal("30"),
        "dias_venc": 180
    },
    {
        "codigo": "784004010",
        "descri": "Caña Paraguaya Tres Leones Etiqueta Azul 1L",
        "barcode": "7840040070017",
        "costo": Decimal("21000"),
        "precio": Decimal("28000"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("40"),
        "stock_min": Decimal("8"),
        "dias_venc": 1800
    },

    # ── LIMPIEZA Y HOGAR (IVA 10%) ──────────────────────────────────────────
    {
        "codigo": "784005001",
        "descri": "Jabón Cavallaro de Coco Puro en Barra 200g",
        "barcode": "7840050010010",
        "costo": Decimal("2800"),
        "precio": Decimal("4200"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("300"),
        "stock_min": Decimal("50"),
        "dias_venc": 720
    },
    {
        "codigo": "784005002",
        "descri": "Jabón en Polvo Zorro Matic Multiacción 800g",
        "barcode": "7840050020019",
        "costo": Decimal("9500"),
        "precio": Decimal("13500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("85"),
        "stock_min": Decimal("15"),
        "dias_venc": 720
    },
    {
        "codigo": "784005003",
        "descri": "Lavandina Desinfectante Activo Concentrada 1L",
        "barcode": "7840050030018",
        "costo": Decimal("3200"),
        "precio": Decimal("4800"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("140"),
        "stock_min": Decimal("25"),
        "dias_venc": 365
    },
    {
        "codigo": "784005004",
        "descri": "Detergente Lavavajillas Zorro Limón 500ml",
        "barcode": "7840050020026",
        "costo": Decimal("3800"),
        "precio": Decimal("5500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("110"),
        "stock_min": Decimal("20"),
        "dias_venc": 720
    },
    {
        "codigo": "784005005",
        "descri": "Papel Higiénico Campanita Doble Hoja Pack x4",
        "barcode": "7840050040017",
        "costo": Decimal("7500"),
        "precio": Decimal("10500"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("130"),
        "stock_min": Decimal("20"),
        "dias_venc": 1800
    },

    # ── FRUTERÍA Y VERDULERÍA (Balanza Pesable EAN-13 Prefijo 20, IVA 5%) ───
    {
        "codigo": "000101",
        "descri": "Tomate Santa Cruz de Primera (Kg)",
        "barcode": "2000101000008",
        "costo": Decimal("6500"),
        "precio": Decimal("9800"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("150.000"),
        "stock_min": Decimal("20.000"),
        "dias_venc": 7
    },
    {
        "codigo": "000102",
        "descri": "Cebolla Colorada Nacional (Kg)",
        "barcode": "2000102000007",
        "costo": Decimal("4200"),
        "precio": Decimal("6500"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("180.000"),
        "stock_min": Decimal("25.000"),
        "dias_venc": 14
    },
    {
        "codigo": "000103",
        "descri": "Papa Negra Especial (Kg)",
        "barcode": "2000103000006",
        "costo": Decimal("4800"),
        "precio": Decimal("6900"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("220.000"),
        "stock_min": Decimal("30.000"),
        "dias_venc": 20
    },
    {
        "codigo": "000104",
        "descri": "Zanahoria Seleccionada (Kg)",
        "barcode": "2000104000005",
        "costo": Decimal("3500"),
        "precio": Decimal("5200"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("120.000"),
        "stock_min": Decimal("15.000"),
        "dias_venc": 12
    },
    {
        "codigo": "000105",
        "descri": "Banana Nanica Dulce de Oro (Kg)",
        "barcode": "2000105000004",
        "costo": Decimal("3800"),
        "precio": Decimal("5800"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("160.000"),
        "stock_min": Decimal("20.000"),
        "dias_venc": 6
    },
    {
        "codigo": "000106",
        "descri": "Manzana Roja Importada (Kg)",
        "barcode": "2000106000003",
        "costo": Decimal("11000"),
        "precio": Decimal("15500"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("90.000"),
        "stock_min": Decimal("15.000"),
        "dias_venc": 15
    },

    # ── CARNICERÍA Y QUESERÍA (Balanza Pesable EAN-13 Prefijo 21, IVA 5%) ───
    {
        "codigo": "000201",
        "descri": "Costilla Vacuna de Primera p/ Asado (Kg)",
        "barcode": "2100201000004",
        "costo": Decimal("28000"),
        "precio": Decimal("38500"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("250.000"),
        "stock_min": Decimal("30.000"),
        "dias_venc": 8
    },
    {
        "codigo": "000202",
        "descri": "Vacío Vacuno Selección Frigorífico (Kg)",
        "barcode": "2100202000003",
        "costo": Decimal("34000"),
        "precio": Decimal("46000"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("140.000"),
        "stock_min": Decimal("20.000"),
        "dias_venc": 8
    },
    {
        "codigo": "000203",
        "descri": "Tapa Cuadril Premium p/ Picanha (Kg)",
        "barcode": "2100203000002",
        "costo": Decimal("48000"),
        "precio": Decimal("64000"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("80.000"),
        "stock_min": Decimal("15.000"),
        "dias_venc": 8
    },
    {
        "codigo": "000204",
        "descri": "Carne Molida Especial Vacuna (Kg)",
        "barcode": "2100204000001",
        "costo": Decimal("26000"),
        "precio": Decimal("35000"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("110.000"),
        "stock_min": Decimal("15.000"),
        "dias_venc": 4
    },
    {
        "codigo": "000205",
        "descri": "Pechuga de Pollo Fresca sin Hueso (Kg)",
        "barcode": "2100205000000",
        "costo": Decimal("18500"),
        "precio": Decimal("24500"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("130.000"),
        "stock_min": Decimal("20.000"),
        "dias_venc": 6
    },
    {
        "codigo": "000206",
        "descri": "Queso Paraguay Artesanal Tradicional (Kg)",
        "barcode": "2100206000009",
        "costo": Decimal("27000"),
        "precio": Decimal("36000"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("95.000"),
        "stock_min": Decimal("15.000"),
        "dias_venc": 18
    },
    {
        "codigo": "000207",
        "descri": "Queso Muzzarella en Barra Trébol (Kg)",
        "barcode": "2100207000008",
        "costo": Decimal("36000"),
        "precio": Decimal("48500"),
        "iva": Decimal("10"),
        "fraccionado": True,
        "stock": Decimal("85.000"),
        "stock_min": Decimal("12.000"),
        "dias_venc": 45
    },

    # ── PANADERÍA (IVA 10% / 5%) ────────────────────────────────────────────
    {
        "codigo": "000301",
        "descri": "Pan Felipe Tradicional Horneado del Día (Kg)",
        "barcode": "2000301000000",
        "costo": Decimal("6000"),
        "precio": Decimal("9000"),
        "iva": Decimal("5"),
        "fraccionado": True,
        "stock": Decimal("75.000"),
        "stock_min": Decimal("10.000"),
        "dias_venc": 2
    },
    {
        "codigo": "784006001",
        "descri": "Chipa Tradicional Almidón Mestizo x3 un.",
        "barcode": "7840060010015",
        "costo": Decimal("7000"),
        "precio": Decimal("10000"),
        "iva": Decimal("10"),
        "fraccionado": False,
        "stock": Decimal("50"),
        "stock_min": Decimal("10"),
        "dias_venc": 3
    }
]

def sembrar_catalogo_supermercado():
    print("=" * 70)
    print("  >>> INYECTANDO CATÁLOGO REAL DE SUPERMERCADO - PARAGUAY <<<")
    print("=" * 70)

    db = SessionLocal()
    insertados = 0
    actualizados = 0

    try:
        now_dt = datetime.datetime.now()

        for item in CATALOGO_PARAGUAY:
            cod = item["codigo"]
            prod = db.query(models.Product).filter_by(art_codigo=cod).first()

            if not prod:
                prod = models.Product(
                    art_codigo=cod,
                    art_descri=item["descri"],
                    art_cbarra=item["barcode"],
                    art_costo=item["costo"],
                    art_preven=item["precio"],
                    art_stkini=item["stock"],
                    art_stkmin=item["stock_min"],
                    art_impu=item["iva"],
                    is_fractional=item["fraccionado"],
                    is_active=True
                )
                db.add(prod)
                db.flush()
                insertados += 1
                accion = "[NUEVO]"
            else:
                prod.art_descri = item["descri"]
                prod.art_cbarra = item["barcode"]
                prod.art_costo = item["costo"]
                prod.art_preven = item["precio"]
                prod.art_stkmin = item["stock_min"]
                prod.art_impu = item["iva"]
                prod.is_fractional = item["fraccionado"]
                prod.is_active = True
                actualizados += 1
                accion = "[ACTUALIZADO]"

            # Crear o actualizar lote de trazabilidad FEFO si no existe
            lote_existente = db.query(models.ProductBatch).filter_by(product_id=prod.id).first()
            if not lote_existente:
                venc = now_dt + datetime.timedelta(days=item["dias_venc"])
                nuevo_lote = models.ProductBatch(
                    product_id=prod.id,
                    lote=f"LOT-{cod}-{venc.strftime('%y%m')}",
                    fecha_vencimiento=venc,
                    stock_actual=item["stock"]
                )
                db.add(nuevo_lote)

            tipo_iva = f"IVA {int(item['iva'])}%" if item['iva'] > 0 else "Exenta"
            frac_tag = "(Balanza Kg)" if item["fraccionado"] else "(Unidad)"
            print(f"{accion} {cod} | {item['descri'][:35]:<35} | Gs. {item['precio']:>7,.0f} | {tipo_iva} {frac_tag}")

        db.commit()
        print("-" * 70)
        print(f"Total productos procesados: {len(CATALOGO_PARAGUAY)}")
        print(f"* Nuevos productos inyectados: {insertados}")
        print(f"* Productos actualizados: {actualizados}")
        print("[OK] Base de datos 'stock_control.db' enriquecida con éxito.")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error sembrando catálogo: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sembrar_catalogo_supermercado()
