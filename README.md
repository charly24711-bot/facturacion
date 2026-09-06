# 🛒 Supermercado Central - Suite Comercial 360° (POS & Back-Office ERP)

[![CI POS Supermercado](https://github.com/charly24711-bot/facturacion/actions/workflows/ci.yml/badge.svg)](https://github.com/charly24711-bot/facturacion/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Database](https://img.shields.io/badge/DB-SQLite%20%7C%20SQLAlchemy-lightgrey.svg)](https://www.sqlalchemy.org/)
[![Normativa Fiscal](https://img.shields.io/badge/Fiscal-DNIT%20%7C%20SIFEN%20(Paraguay)-orange.svg)](https://www.dnit.gov.py/)
[![Regla Financiera](https://img.shields.io/badge/Aritm%C3%A9tica-Decimal%20Puro%20(Cero%20Float)-critical.svg)](#reglas-financieras-y-de-redondeo)

Sistema integral de Punto de Venta (POS) y Gestión Administrativa / Back-Office desarrollado específicamente para supermercados y comercios de retail en la **Triple Frontera** (Paraguay - Brasil - Argentina), bajo normativas de la **DNIT** (Ley 6380/19) y facturación electrónica **SIFEN**.

---

## 🌟 Características Principales

### 1. Punto de Venta Front-Office (POS de Alto Rendimiento)
- **Grilla de Venta Reactiva (`QTableView` + `QAbstractTableModel`):** Cero retrasos (lag) con escaneo continuo y soporte para miles de transacciones diarias.
- **Motor de Canales de Precios en Vivo:** Selector desplegable en cabecera con resolución jerárquica: `Promoción Vigente > Escala por Volumen (Tier) > Canal Activo > Lista del Cliente > Minorista Base`.
- **Visor Lateral Multimedia:** Tarjeta gráfica con foto del artículo, código, descripción, precio y stock físico en tiempo real.
- **Buscador con Miniaturas (`[F2] / [F4]`):** Búsqueda rápida por nombre o código con fotos y navegación por teclado.
- **Integración con Balanzas In-Store:** Decodificación instantánea de códigos de barras EAN-13 con prefijos `20` y `21` (`PP CCCCC PPPP D`) para artículos fraccionables (peso en kg o monto incrustado).
- **Ergonomía de Caja Operativa:**
  - `[Supr] / Delete`: Quitar ítem seleccionado con recálculo automático de IVA y totales.
  - `[F9]`: Cancelar venta en curso y vaciar carrito rápidamente.
  - `[F7]`: Movimientos de Caja (Fondo de apertura y Sangría de efectivo a tesorería) con ticket térmico de comprobante.
  - `[F12]`: Pausa / Bloqueo seguro de terminal con PIN del cajero, cronómetro en vivo y numpad táctil.

### 2. Tesorería Multidivisa Triple Frontera
- **Cobro Split Multimoneda (`[F11]`):** Permite liquidar una misma factura combinando pagos en **Guaraníes (PYG)**, **Dólares (USD)**, **Reales / PIX (BRL)** y **Pesos (ARS)**.
- **Cálculo de Vuelto Cruzado:** Si el cliente paga en dólares o reales, el sistema calcula el vuelto en la moneda deseada (ej: PYG o USD) sin pérdidas por redondeo.
- **Arqueo Ciego de Fin de Turno (`[F10]`):** Comparación estricta entre el efectivo teórico del sistema ($\text{Ventas} + \text{Fondo Inicial} - \text{Sangrías}$) y el monto físico declarado por el cajero, registrando faltantes o sobrantes de forma inmutable en `models.CashAudit`.

### 3. Back-Office Administrativo y Gerencial (`AdminWindow`)
- **Dashboard Analítico en Vivo:** Fila de 5 KPIs (Ventas del Día, Comprobantes, Ticket Promedio, IVA Liquidado, Stock Crítico FIFO), monitor de terminales abiertas y Top 5 de artículos más vendidos.
- **Gestión Visual de Usuarios y Cajeros (`[F2]`):** Control de roles (`ADMIN`, `GERENTE`, `CAJERO`), cifrado seguro SHA-256 y protección de la cuenta maestra.
- **Mermas, Roturas y Ajustes de Inventario (`[F4]`):** Registro de bajas de mercadería por vencimiento, rotura o consumo interno con deducción atómica de stock físico `art_stkini`.
- **Exportador Tributario Oficial Hechauka / Marangatú DNIT (`[F6]`):** Generación automática de los Libros de Ventas (Tipo 2) y Compras (Tipo 1) en formato CSV/TXT delimitado por `;` listo para importar al portal DNIT.
- **Impresor Masivo de Etiquetas de Góndola (`[F3]`):**
  - Generador vectorial propio para **EAN-13** y **Code-128**.
  - Formatos: Pliegos A4 adhesivos (24 y 14 etiquetas) y rollos térmicos continuos (60x30 mm y 50x25 mm).
  - Precios destacados en Guaraníes (`₲ 15.000`) y secundarios en Dólares (`US$ 2.00`).
  - Previsualización en tiempo real y exportación directa a **PDF**.

---

## ⚖️ Reglas Financieras y de Redondeo

1. **Cero Float (`decimal.Decimal`):** Queda terminantemente prohibido el uso del tipo nativo `float` para montos, precios, subtotales o inventario. Toda operación matemática se procesa mediante `Decimal` con cuantización estricta.
2. **Moneda Base:** Guaraní (`PYG`) sin decimales (`Decimal('1')`).
3. **Monedas Secundarias:** `USD`, `BRL`, `ARS` siempre con 2 decimales (`Decimal('0.01')`).
4. **Fórmulas de IVA Oficiales DNIT (Ley 6380/19):**
   - **IVA 10%:** `total / 11`
   - **IVA 5%:** `total / 21`
   - **Exentas:** `total` (IVA = 0)

---

## 📂 Estructura del Repositorio

```text
├── .github/workflows/
│   └── ci.yml                     # Pipeline CI (Windows & Linux matrix)
├── ui/
│   ├── main_window.py             # Terminal POS de Cobro (Front-Office)
│   ├── admin_window.py            # Panel Administrativo ERP (Back-Office)
│   ├── payment_dialog.py          # Cobro Split Multidivisa y RUC
│   ├── barcode_renderer.py        # Motor vectorial EAN-13 y Code-128
│   ├── shelf_labels_dialog.py     # Impresión de etiquetas de góndola y PDF
│   ├── lock_screen_dialog.py      # Pantalla de bloqueo con PIN y teclado táctil
│   ├── stock_adjustment_dialog.py # Registro de mermas y ajustes de inventario
│   ├── hechauka_export_dialog.py  # Exportador oficial DNIT Hechauka/Marangatú
│   ├── users_management_dialog.py # ABM visual de usuarios y cajeros
│   ├── caja_movimiento_dialog.py  # Fondo inicial y sangría de caja
│   └── ...
├── models.py                      # Modelos SQLAlchemy y arquitectura Syncable
├── database.py                    # Conexión SQLite y resolución de rutas de imágenes
├── requirements.txt               # Dependencias del proyecto
├── DOCS/
│   ├── BITACORA.md                # Registro cronológico detallado de cambios
│   ├── FLUJO_OPERATIVO.md         # Manual de procedimientos de caja y auditoría
│   └── GLOSARIO.md                # Glosario tributario y comercial de frontera
└── test_*.py                      # Batería de 11 suites de pruebas automatizadas
```

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
- Python 3.11, 3.12 o superior.
- Git instalado.

### 1. Clonar el Repositorio
```bash
git clone https://github.com/charly24711-bot/facturacion.git
cd facturacion
```

### 2. Crear Entorno Virtual e Instalar Dependencias
```bash
python -m venv venv
# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# En Linux / Mac:
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Ejecutar la Aplicación

- **Modo Panel Administrativo (Back-Office por defecto):**
  ```bash
  python main.py
  ```
  *(Credenciales de desarrollo: Usuario `admin`, Contraseña `admin`)*

- **Modo Terminal de Caja POS (Front-Office directo):**
  ```bash
  python main.py --pos
  ```

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto cuenta con una cobertura integral de **75+ pruebas automatizadas** que se ejecutan localmente o en el pipeline de GitHub Actions ante cada push:

```bash
# 1. Suites de las 3 Fases Comerciales + Flujo E2E:
python -m pytest test_fase1_pos_ergonomia.py test_fase2_backoffice.py test_fase3_gondola_seguridad.py test_flujo_completo_pos.py -v

# 2. Batería de Stress Masivo 360° (50 compras, 300 lotes, 25 NC, arqueo ciego):
python test_stress_integral_360.py

# 3. Pruebas Fiscales y Facturación KuDE con RUC:
python test_cobro_ruc_ticket.py
python test_ruc_integration.py
python test_flujo_presupuesto.py

# 4. Pruebas de Autenticación y Panel ERP:
python test_auth_admin.py
python test_riguroso_panel_admin.py
```

---

## 📄 Licencia

Este desarrollo está estructurado como software comercial privado de alto estándar para implementación en cadenas minoristas y supermercados.
