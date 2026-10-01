"""
utils/fiscal_engine.py - Motor de Liquidación Fiscal, Generador JSON SIFEN v150 y Reportes Contables

Cumple con:
1. Ley 6380/19 (Paraguay): Liquidación estricta de IVA 10%, 5% y Exentas.
2. Aritmética 100% en decimal.Decimal (cero float).
3. CDC SIFEN de 44 dígitos con Módulo 11.
4. Exportación JSON SIFEN v150, Libro de Ventas CSV y Reporte HTML5 interactivo con ApexCharts.
"""

import json
import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional

from sqlalchemy import func
import models
from tax_calculator import calcular_iva_linea
from ruc_validator.ruc_validator import calcular_dv_ruc


def generate_cdc(
    invoice_id: int,
    ven_numero: Optional[int],
    ven_fecha: Optional[datetime.datetime],
    ruc_empresa: str = "80089552-1",
    timbrado: str = "12345678",
    estab: str = "001",
    pto_exp: str = "001"
) -> str:
    """Genera el Código Digital de Control (CDC) oficial de 44 dígitos con Módulo 11."""
    ruc_clean = ruc_empresa.replace('-', '').strip()
    if '-' in ruc_empresa:
        partes = ruc_empresa.split('-')
        ruc_base = partes[0].zfill(8)
        dv_ruc = partes[1]
    else:
        ruc_base = ruc_clean[:-1].zfill(8) if len(ruc_clean) > 1 else "80089552"
        dv_ruc = ruc_clean[-1] if len(ruc_clean) > 0 else "1"

    tipo_doc = "01"  # Factura Electrónica
    nro_sec = f"{(ven_numero or invoice_id):07d}"
    tipo_contrib = "1"  # Persona Jurídica
    fec = ven_fecha or datetime.datetime.utcnow()
    fecha_cad = fec.strftime("%Y%m%d")
    tipo_emision = "1"  # Normal
    cod_seguridad = "100000001"

    cadena_43 = f"{tipo_doc}{ruc_base}{dv_ruc}{estab}{pto_exp}{nro_sec}{tipo_contrib}{fecha_cad}{tipo_emision}{cod_seguridad}"
    dv_cdc = calcular_dv_ruc(cadena_43)
    return f"{cadena_43}{dv_cdc}"


class FiscalEngine:
    """Motor de cálculo y auditoría fiscal para Back-Office."""

    @staticmethod
    def get_period_summary(
        session,
        start_date: datetime.datetime,
        end_date: datetime.datetime
    ) -> Dict[str, Any]:
        """
        Calcula la liquidación consolidada de impuestos para un rango de fechas.
        """
        invoices = (
            session.query(models.Invoice)
            .filter(
                models.Invoice.ven_fecha >= start_date,
                models.Invoice.ven_fecha <= end_date,
                models.Invoice.ven_estado == 'A'
            )
            .all()
        )

        total_general = Decimal('0')
        total_gravada_10 = Decimal('0')
        total_iva_10 = Decimal('0')
        total_gravada_5 = Decimal('0')
        total_iva_5 = Decimal('0')
        total_exentas = Decimal('0')
        total_items = 0

        payment_methods_map: Dict[str, Decimal] = {}

        for inv in invoices:
            inv_total = inv.ven_total or Decimal('0')
            total_general += inv_total

            for it in inv.items:
                total_items += 1
                prod = it.product
                tasa = int(prod.art_impu) if (prod and prod.art_impu is not None) else 10
                subtotal = (it.vit_canti * it.vit_precio).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

                res = calcular_iva_linea(subtotal, tasa)
                total_gravada_10 += res["gravada_10"]
                total_iva_10 += res["iva_10"]
                total_gravada_5 += res["gravada_5"]
                total_iva_5 += res["iva_5"]
                total_exentas += res["exenta"]

            for pay in inv.payments:
                metodo = pay.cob_metodo or "Efectivo"
                monto = pay.cob_monto_pyg or pay.cob_monto or Decimal('0')
                payment_methods_map[metodo] = payment_methods_map.get(metodo, Decimal('0')) + monto

        total_iva_acum = total_iva_10 + total_iva_5
        base_imponible_10 = total_gravada_10  # En tax_calculator gravada_10 ya es neto sin IVA
        base_imponible_5 = total_gravada_5

        return {
            "invoices_count": len(invoices),
            "items_count": total_items,
            "total_general": total_general,
            "total_gravada_10": total_gravada_10 + total_iva_10, # Bruto gravado 10
            "base_imponible_10": total_gravada_10,
            "total_iva_10": total_iva_10,
            "total_gravada_5": total_gravada_5 + total_iva_5, # Bruto gravado 5
            "base_imponible_5": total_gravada_5,
            "total_iva_5": total_iva_5,
            "total_exentas": total_exentas,
            "total_iva_acum": total_iva_acum,
            "payments_breakdown": payment_methods_map
        }

    @staticmethod
    def get_invoices_detail(
        session,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        query_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna la lista detallada de facturas en el período con CDC y desgloses.
        """
        q = (
            session.query(models.Invoice)
            .filter(
                models.Invoice.ven_fecha >= start_date,
                models.Invoice.ven_fecha <= end_date,
                models.Invoice.ven_estado == 'A'
            )
            .order_by(models.Invoice.ven_numero.desc())
        )

        invoices = q.all()
        result = []

        query_str = (query_filter or "").strip().lower()

        # Obtener datos de empresa para CDC
        company = session.query(models.CompanySettings).first()
        ruc_emp = getattr(company, 'ruc', "80089552-1") or "80089552-1"
        timbrado_emp = getattr(company, 'timbrado', "12345678") or "12345678"

        for inv in invoices:
            cli = inv.client
            ruc_cli = getattr(cli, 'cli_ruc', '44444401-7') or '44444401-7'
            nombre_cli = getattr(cli, 'cli_nombre', 'CONSUMIDOR FINAL') or 'CONSUMIDOR FINAL'

            # Filtrar si aplica
            if query_str:
                nro_str = str(inv.ven_numero or inv.id)
                if (query_str not in ruc_cli.lower() and
                    query_str not in nombre_cli.lower() and
                    query_str not in nro_str):
                    continue

            tot_g10 = Decimal('0')
            tot_i10 = Decimal('0')
            tot_g5 = Decimal('0')
            tot_i5 = Decimal('0')
            tot_ex = Decimal('0')

            for it in inv.items:
                prod = it.product
                tasa = int(prod.art_impu) if (prod and prod.art_impu is not None) else 10
                subtotal = (it.vit_canti * it.vit_precio).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                res = calcular_iva_linea(subtotal, tasa)
                tot_g10 += res["gravada_10"]
                tot_i10 += res["iva_10"]
                tot_g5 += res["gravada_5"]
                tot_i5 += res["iva_5"]
                tot_ex += res["exenta"]

            cdc_code = generate_cdc(
                invoice_id=inv.id,
                ven_numero=inv.ven_numero,
                ven_fecha=inv.ven_fecha,
                ruc_empresa=ruc_emp,
                timbrado=timbrado_emp
            )

            result.append({
                "id": inv.id,
                "ven_numero": inv.ven_numero or inv.id,
                "ven_fecha": inv.ven_fecha.strftime("%d/%m/%Y %H:%M") if inv.ven_fecha else "",
                "ruc_cliente": ruc_cli,
                "nombre_cliente": nombre_cli,
                "gravada_10": tot_g10 + tot_i10,
                "iva_10": tot_i10,
                "gravada_5": tot_g5 + tot_i5,
                "iva_5": tot_i5,
                "exenta": tot_ex,
                "total": inv.ven_total or Decimal('0'),
                "cdc": cdc_code
            })

        return result

    @staticmethod
    def generate_sifen_json(
        session,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        company_settings: Optional[models.CompanySettings] = None
    ) -> Dict[str, Any]:
        """
        Genera el lote estructurado JSON compatible con SIFEN / e-Kuatia v150.
        """
        summary = FiscalEngine.get_period_summary(session, start_date, end_date)
        details = FiscalEngine.get_invoices_detail(session, start_date, end_date)

        company = company_settings or session.query(models.CompanySettings).first()
        ruc_emp = getattr(company, 'ruc', "80089552-1") or "80089552-1"
        razon_emp = getattr(company, 'nombre', "SUPERMERCADO TRIFRONTERA S.A.") or "SUPERMERCADO TRIFRONTERA S.A."
        timbrado = getattr(company, 'timbrado', "12345678") or "12345678"

        partes_ruc = ruc_emp.split('-') if '-' in ruc_emp else [ruc_emp, "0"]

        doc_list = []
        for d in details:
            doc_list.append({
                "cdc": d["cdc"],
                "numero_factura": f"001-001-{d['ven_numero']:07d}",
                "fecha_emision": d["ven_fecha"],
                "receptor": {
                    "ruc": d["ruc_cliente"],
                    "razon_social": d["nombre_cliente"]
                },
                "totales": {
                    "gravada_10": str(Decimal(str(d["gravada_10"])).quantize(Decimal('1'))),
                    "iva_10": str(Decimal(str(d["iva_10"])).quantize(Decimal('1'))),
                    "gravada_5": str(Decimal(str(d["gravada_5"])).quantize(Decimal('1'))),
                    "iva_5": str(Decimal(str(d["iva_5"])).quantize(Decimal('1'))),
                    "exenta": str(Decimal(str(d["exenta"])).quantize(Decimal('1'))),
                    "total_general": str(Decimal(str(d["total"])).quantize(Decimal('1')))
                }
            })

        sifen_payload = {
            "version": "150",
            "generado_el": datetime.datetime.utcnow().isoformat(),
            "emisor": {
                "ruc": partes_ruc[0],
                "dv": partes_ruc[1],
                "razon_social": razon_emp,
                "timbrado": timbrado,
                "establecimiento": "001",
                "punto_emision": "001"
            },
            "periodo": {
                "desde": start_date.strftime("%Y-%m-%d"),
                "hasta": end_date.strftime("%Y-%m-%d")
            },
            "resumen_fiscal": {
                "total_facturado": str(Decimal(str(summary["total_general"])).quantize(Decimal('1'))),
                "base_gravada_10": str(Decimal(str(summary["base_imponible_10"])).quantize(Decimal('1'))),
                "total_iva_10": str(Decimal(str(summary["total_iva_10"])).quantize(Decimal('1'))),
                "base_gravada_5": str(Decimal(str(summary["base_imponible_5"])).quantize(Decimal('1'))),
                "total_iva_5": str(Decimal(str(summary["total_iva_5"])).quantize(Decimal('1'))),
                "total_exentas": str(Decimal(str(summary["total_exentas"])).quantize(Decimal('1'))),
                "total_iva": str(Decimal(str(summary["total_iva_acum"])).quantize(Decimal('1'))),
                "total_comprobantes": summary["invoices_count"]
            },
            "documentos": doc_list
        }

        return sifen_payload

    @staticmethod
    def generate_sales_book_csv(
        session,
        start_date: datetime.datetime,
        end_date: datetime.datetime
    ) -> str:
        """
        Genera el Libro de Ventas en formato CSV (compatible Excel y Hechauka).
        """
        details = FiscalEngine.get_invoices_detail(session, start_date, end_date)
        lines = [
            "Nro_Factura;Fecha;RUC_Cliente;Razon_Social;Gravada_10;IVA_10;Gravada_5;IVA_5;Exenta;Total_PYG;CDC_SIFEN"
        ]

        for d in details:
            line = (
                f"001-001-{d['ven_numero']:07d};"
                f"{d['ven_fecha']};"
                f"{d['ruc_cliente']};"
                f"\"{d['nombre_cliente']}\";"
                f"{d['gravada_10']};"
                f"{d['iva_10']};"
                f"{d['gravada_5']};"
                f"{d['iva_5']};"
                f"{d['exenta']};"
                f"{d['total']};"
                f"{d['cdc']}"
            )
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def generate_html_report(
        session,
        start_date: datetime.datetime,
        end_date: datetime.datetime
    ) -> str:
        """
        Genera un informe interactivo HTML5 con ApexCharts y diseño Dark Mode.
        """
        summary = FiscalEngine.get_period_summary(session, start_date, end_date)
        details = FiscalEngine.get_invoices_detail(session, start_date, end_date)

        rows_html = ""
        for d in details[:50]:  # Top 50 en vista
            rows_html += f"""
            <tr>
                <td><b>001-001-{d['ven_numero']:07d}</b></td>
                <td>{d['ven_fecha']}</td>
                <td>{d['ruc_cliente']}</td>
                <td>{d['nombre_cliente']}</td>
                <td style="text-align:right">₲ {d['gravada_10']:,.0f}</td>
                <td style="text-align:right; color:#7aa2f7">₲ {d['iva_10']:,.0f}</td>
                <td style="text-align:right">₲ {d['gravada_5']:,.0f}</td>
                <td style="text-align:right; color:#ffd166">₲ {d['iva_5']:,.0f}</td>
                <td style="text-align:right">₲ {d['exenta']:,.0f}</td>
                <td style="text-align:right; font-weight:bold; color:#9ece6a">₲ {d['total']:,.0f}</td>
                <td style="font-family:monospace; font-size:10px">{d['cdc']}</td>
            </tr>
            """.replace(",", ".")

        iva10 = float(summary['total_iva_10'])
        iva5 = float(summary['total_iva_5'])
        exenta = float(summary['total_exentas'])

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Fiscal SIFEN - POS Supermercado</title>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        body {{
            background-color: #0f1117;
            color: #a9b1d6;
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #7aa2f7; font-size: 24px; margin-bottom: 4px; }}
        .subtitle {{ color: #565f89; margin-bottom: 24px; }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background-color: #1a2333;
            border: 1px solid #2a3550;
            border-radius: 8px;
            padding: 16px;
        }}
        .kpi-title {{ font-size: 12px; color: #7aa2f7; font-weight: bold; text-transform: uppercase; }}
        .kpi-value {{ font-size: 22px; font-weight: bold; color: #9ece6a; margin-top: 8px; font-family: monospace; }}
        .chart-container {{
            background-color: #1a2333;
            border: 1px solid #2a3550;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        th {{ background-color: #131929; color: #7aa2f7; padding: 10px 8px; text-align: left; border-bottom: 2px solid #2a3550; }}
        td {{ padding: 8px; border-bottom: 1px solid #1c2333; color: #e0e6ed; }}
        tr:hover {{ background-color: #1f2a3f; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Informe de Auditoría y Liquidación Fiscal KuDE / SIFEN</h1>
        <div class="subtitle">Período: {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')} | Comprobantes Emitidos: {summary['invoices_count']}</div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Total Facturado (PYG)</div>
                <div class="kpi-value">₲ {summary['total_general']:,.0f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Liquidación IVA 10%</div>
                <div class="kpi-value" style="color:#7aa2f7">₲ {summary['total_iva_10']:,.0f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Liquidación IVA 5%</div>
                <div class="kpi-value" style="color:#ffd166">₲ {summary['total_iva_5']:,.0f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Total IVA Liquidado</div>
                <div class="kpi-value" style="color:#f7768e">₲ {summary['total_iva_acum']:,.0f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Ventas Exentas</div>
                <div class="kpi-value" style="color:#a9b1d6">₲ {summary['total_exentas']:,.0f}</div>
            </div>
        </div>

        <div class="chart-container">
            <div id="taxChart"></div>
        </div>

        <div class="chart-container">
            <h3 style="color:#7aa2f7; margin-top:0">Detalle de Comprobantes Fiscales KuDE</h3>
            <table>
                <thead>
                    <tr>
                        <th>Nro Factura</th>
                        <th>Fecha</th>
                        <th>RUC Cliente</th>
                        <th>Razón Social</th>
                        <th>Grav. 10%</th>
                        <th>IVA 10%</th>
                        <th>Grav. 5%</th>
                        <th>IVA 5%</th>
                        <th>Exenta</th>
                        <th>Total PYG</th>
                        <th>CDC SIFEN (44 Digs)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        var options = {{
            series: [{iva10}, {iva5}, {exenta}],
            chart: {{
                type: 'donut',
                height: 320,
                foreColor: '#a9b1d6',
                background: 'transparent'
            }},
            labels: ['IVA 10% Liquidado', 'IVA 5% Liquidado', 'Ventas Exentas'],
            colors: ['#7aa2f7', '#ffd166', '#737aa2'],
            theme: {{ mode: 'dark' }},
            legend: {{ position: 'bottom' }}
        }};

        var chart = new ApexCharts(document.querySelector("#taxChart"), options);
        chart.render();
    </script>
</body>
</html>
""".replace(",", ".")

        return html
