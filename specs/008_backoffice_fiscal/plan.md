# PLAN-008: Plan de Implementación - Back-Office Fiscal y SIFEN

## Fase 1: Motor de Liquidación y Generador SIFEN (`utils/fiscal_engine.py`)
1. **`FiscalEngine`**:
   - `get_period_summary(session, start_date, end_date) -> dict`: Agregación de ventas, cálculo de base gravada 10%, base 5%, exentas y totales de IVA.
   - `get_invoices_detail(session, start_date, end_date, query_filter=None) -> list[dict]`: Lista detallada de facturas con CDC generado, cliente, RUC y montos.
   - `generate_sifen_json(session, start_date, end_date, company_settings=None) -> dict`: Generación del documento electrónico SIFEN v150.
   - `generate_sales_book_csv(session, start_date, end_date) -> str`: Generación de Libro de Ventas en formato CSV / Excel.
   - `generate_html_report(session, start_date, end_date) -> str`: Plantilla HTML5 con ApexCharts integrada para visualización interactiva.

## Fase 2: Interfaz Gráfica del Back-Office Fiscal (`ui/backoffice_fiscal_dialog.py`)
1. **`BackofficeFiscalDialog`**:
   - Selector de período rápido (Hoy, Esta Semana, Este Mes, Personalizado con `QDateEdit`).
   - Tarjetas KPI con diseño Dark Mode:
     - 💳 Total Facturado
     - 📊 Base Gravada 10% & IVA 10%
     - 🏷️ Base Gravada 5% & IVA 5%
     - 🛡️ Ventas Exentas
     - 🧾 Total Comprobantes
   - Barra de búsqueda y filtrado de comprobantes KuDE.
   - Tabla de comprobantes (`QTableView` / `QTableWidget` de consulta) con columnas: Nro, Fecha, RUC, Cliente, Gravada 10%, Gravada 5%, Exenta, Total, CDC.
   - Botones de acción:
     - 📄 *Exportar JSON SIFEN v150*
     - 📊 *Ver Reporte Gráfico (ApexCharts)*
     - 📑 *Exportar Libro de Ventas (CSV)*

## Fase 3: Integración en Menús del POS
1. Agregar opción en el menú `Utilidades` y en el Panel Admin de [`ui/main_window.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/main_window.py) / [`ui/admin_window.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/admin_window.py).

## Fase 4: Suite de Pruebas Automatizadas (`tests/test_backoffice_fiscal.py`)
1. Test de liquidación de impuestos multitasas con `Decimal`.
2. Test de consistencia en el balance de sumas fiscales (`Base + IVA == Total`).
3. Test de estructura del JSON SIFEN v150.
4. Test de generación de Libro de Ventas CSV y reporte HTML5.

## Fase 5: Memoria Operativa (`MEMORY.md`)
1. Actualización de `MEMORY.md` y cierre del flujo multiagente.
