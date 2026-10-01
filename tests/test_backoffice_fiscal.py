"""
tests/test_backoffice_fiscal.py - Suite de Pruebas para Back-Office Fiscal y SIFEN (SPEC-008)
Valida:
1. Generador de CDC de 44 dígitos con algoritmo Módulo 11.
2. Liquidación tributaria de IVA 10%, 5% y Exentas en FiscalEngine.
3. Balance impositivo: Base + IVA == Total General.
4. Generación de JSON SIFEN v150 estructurado.
5. Generación de Libro de Ventas CSV y Reporte HTML5 con ApexCharts.
"""

import os
import sys
import pytest
import datetime
from decimal import Decimal

# Asegurar path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../.agents/skills')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import models
from utils.fiscal_engine import generate_cdc, FiscalEngine


@pytest.fixture
def fiscal_db():
    """Crea una base de datos SQLite en memoria con ventas de prueba multidivisa e impuestos."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Empresa
        company = models.CompanySettings(
            nombre="SUPERMERCADO TRIFRONTERA S.A.",
            ruc="80089552-1",
            timbrado="12345678"
        )
        session.add(company)

        # Clientes
        cli1 = models.Client(cli_codigo="000001", cli_nombre="JUAN PEREZ", cli_ruc="1234567-8")
        cli2 = models.Client(cli_codigo="000002", cli_nombre="DESPENSA SAN ROQUE", cli_ruc="80011223-4")
        session.add_all([cli1, cli2])

        # Productos con diferentes tasas de IVA
        prod_10 = models.Product(art_codigo="P10", art_descri="ARROZ 1KG", art_preven=Decimal('11000'), art_impu=Decimal('10'))
        prod_5 = models.Product(art_codigo="P05", art_descri="ACEITE 900ML", art_preven=Decimal('21000'), art_impu=Decimal('5'))
        prod_ex = models.Product(art_codigo="PEX", art_descri="LIBRO EDUCATIVO", art_preven=Decimal('50000'), art_impu=Decimal('0'))
        session.add_all([prod_10, prod_5, prod_ex])
        session.commit()

        # Factura 1: 1 item 10% (11.000) -> Gravada: 10.000, IVA 10%: 1.000
        inv1 = models.Invoice(
            ven_numero=1001,
            ven_fecha=datetime.datetime(2026, 10, 1, 10, 0, 0),
            ven_codcli="000001",
            ven_total=Decimal('11000'),
            ven_estado='A'
        )
        session.add(inv1)
        session.flush()

        it1 = models.InvoiceItem(
            vit_numero=1001,
            vit_articu="P10",
            vit_canti=Decimal('1.000'),
            vit_precio=Decimal('11000')
        )
        session.add(it1)

        pay1 = models.Payment(
            cob_numero=1001,
            cob_vennro=1001,
            cob_monto=Decimal('11000'),
            cob_metodo="Efectivo",
            cob_monto_pyg=Decimal('11000')
        )
        session.add(pay1)

        # Factura 2: 1 item 5% (21.000) + 1 item Exento (50.000) -> Total: 71.000
        # 5%: Gravada: 20.000, IVA: 1.000. Exento: 50.000
        inv2 = models.Invoice(
            ven_numero=1002,
            ven_fecha=datetime.datetime(2026, 10, 1, 11, 30, 0),
            ven_codcli="000002",
            ven_total=Decimal('71000'),
            ven_estado='A'
        )
        session.add(inv2)
        session.flush()

        it2_1 = models.InvoiceItem(
            vit_numero=1002,
            vit_articu="P05",
            vit_canti=Decimal('1.000'),
            vit_precio=Decimal('21000')
        )
        it2_2 = models.InvoiceItem(
            vit_numero=1002,
            vit_articu="PEX",
            vit_canti=Decimal('1.000'),
            vit_precio=Decimal('50000')
        )
        session.add_all([it2_1, it2_2])

        pay2 = models.Payment(
            cob_numero=1002,
            cob_vennro=1002,
            cob_monto=Decimal('71000'),
            cob_metodo="Tarjeta VISA",
            card_brand="VISA",
            cob_monto_pyg=Decimal('71000')
        )
        session.add(pay2)

        session.commit()
        yield session
    finally:
        session.close()


class TestBackofficeFiscal:

    def test_01_cdc_44_digits_generator(self):
        """Valida que el generador de CDC produzca 44 dígitos exactos con Módulo 11."""
        cdc = generate_cdc(
            invoice_id=1,
            ven_numero=1001,
            ven_fecha=datetime.datetime(2026, 10, 1, 10, 0, 0),
            ruc_empresa="80089552-1",
            timbrado="12345678"
        )
        assert len(cdc) == 44
        assert cdc.isdigit()
        assert cdc.startswith("01")  # Tipo Factura Electrónica
        assert "80089552" in cdc
        assert "20261001" in cdc

    def test_02_fiscal_period_summary_and_tax_balance(self, fiscal_db):
        """Verifica la liquidación impositiva exacta y el balance tributario Base + IVA == Total."""
        start = datetime.datetime(2026, 10, 1, 0, 0, 0)
        end = datetime.datetime(2026, 10, 1, 23, 59, 59)

        summary = FiscalEngine.get_period_summary(fiscal_db, start, end)

        assert summary["invoices_count"] == 2
        assert summary["items_count"] == 3

        # Total Facturado: 11.000 + 71.000 = 82.000
        assert summary["total_general"] == Decimal('82000')

        # IVA 10%: total 11.000 -> Gravada 10.000, IVA 1.000
        assert summary["total_gravada_10"] == Decimal('11000')
        assert summary["base_imponible_10"] == Decimal('10000')
        assert summary["total_iva_10"] == Decimal('1000')

        # IVA 5%: total 21.000 -> Gravada 20.000, IVA 1.000
        assert summary["total_gravada_5"] == Decimal('21000')
        assert summary["base_imponible_5"] == Decimal('20000')
        assert summary["total_iva_5"] == Decimal('1000')

        # Exentas: 50.000
        assert summary["total_exentas"] == Decimal('50000')

        # Total IVA Acumulado: 1.000 + 1.000 = 2.000
        assert summary["total_iva_acum"] == Decimal('2000')

        # Validación de Ecuación Contable Fundamental
        # Total = Base 10 + IVA 10 + Base 5 + IVA 5 + Exentas
        balance = (
            summary["base_imponible_10"] + summary["total_iva_10"] +
            summary["base_imponible_5"] + summary["total_iva_5"] +
            summary["total_exentas"]
        )
        assert balance == summary["total_general"]

        # Medios de pago desglosados
        assert summary["payments_breakdown"]["Efectivo"] == Decimal('11000')
        assert summary["payments_breakdown"]["Tarjeta VISA"] == Decimal('71000')

    def test_03_invoices_detail_and_search_filter(self, fiscal_db):
        """Verifica la obtención detallada de comprobantes y el filtrado por RUC/Cliente."""
        start = datetime.datetime(2026, 10, 1, 0, 0, 0)
        end = datetime.datetime(2026, 10, 1, 23, 59, 59)

        details = FiscalEngine.get_invoices_detail(fiscal_db, start, end)
        assert len(details) == 2

        # Filtrar por "ROQUE"
        filtered_roque = FiscalEngine.get_invoices_detail(fiscal_db, start, end, query_filter="ROQUE")
        assert len(filtered_roque) == 1
        assert filtered_roque[0]["ruc_cliente"] == "80011223-4"
        assert filtered_roque[0]["total"] == Decimal('71000')

    def test_04_sifen_json_v150_export(self, fiscal_db):
        """Valida la generación de la estructura JSON oficial SIFEN v150."""
        start = datetime.datetime(2026, 10, 1, 0, 0, 0)
        end = datetime.datetime(2026, 10, 1, 23, 59, 59)

        sifen_json = FiscalEngine.generate_sifen_json(fiscal_db, start, end)

        assert sifen_json["version"] == "150"
        assert sifen_json["emisor"]["ruc"] == "80089552"
        assert sifen_json["resumen_fiscal"]["total_facturado"] == "82000"
        assert sifen_json["resumen_fiscal"]["total_iva"] == "2000"
        assert len(sifen_json["documentos"]) == 2

        doc1 = sifen_json["documentos"][0]
        assert len(doc1["cdc"]) == 44
        assert "numero_factura" in doc1
        assert "receptor" in doc1

    def test_05_sales_book_csv_and_html_generation(self, fiscal_db):
        """Valida la generación del Libro de Ventas CSV y el reporte HTML con ApexCharts."""
        start = datetime.datetime(2026, 10, 1, 0, 0, 0)
        end = datetime.datetime(2026, 10, 1, 23, 59, 59)

        # 1. CSV
        csv_text = FiscalEngine.generate_sales_book_csv(fiscal_db, start, end)
        assert "Nro_Factura;Fecha;RUC_Cliente;Razon_Social" in csv_text
        assert "JUAN PEREZ" in csv_text
        assert "DESPENSA SAN ROQUE" in csv_text

        # 2. HTML
        html_text = FiscalEngine.generate_html_report(fiscal_db, start, end)
        assert "<!DOCTYPE html>" in html_text
        assert "apexcharts" in html_text.lower()
        assert "82.000" in html_text
        assert "SUPERMERCADO" in html_text or "KuDE" in html_text
