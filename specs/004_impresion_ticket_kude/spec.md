# SPEC-004: EMISIÓN Y FORMATO DE TICKETS TÉRMICOS FISCALES (KUDE / SIFEN 80MM)

**Estado:** Aprobado / Implementado  
**Versión:** 1.0.0  
**Fecha:** Octubre 2026

---

## 1. PROPÓSITO Y ALCANCE
Estandarizar el diseño, composición y emisión del Comprobante Fiscal en papel térmico de 80 mm (KuDE - Documento Tributario Electrónico de SIFEN / DNIT Paraguay), incorporando el Código de Control (CDC) de 44 dígitos, Código QR de consulta ciudadana en e-Kuatia, liquidación exacta de IVA (10%, 5% y Exentas) y desglose de vouchers de terminales de cobro POS.

---

## 2. REQUERIMIENTOS FUNCIONALES

### RF-01: Estructura Estándar de 80 mm (40 Columnas)
- Ancho monoespaciado fijo de 40 caracteres con encabezado comercial: Razón Social, RUC, Timbrado, Fecha de Inicio de Vigencia, Sucursal y Punto de Expedición.
- Número legal de comprobante en formato `EEE-PPP-NNNNNNN` (Establecimiento, Punto, Secuencia de 7 dígitos).

### RF-02: Grilla de Artículos y Liquidación Impositiva DNIT
- Cada línea de artículo debe exhibir:
  * Línea 1: Código PLU/EAN + Descripción.
  * Línea 2: Tasa IVA (10%, 5%, 0%), Cantidad con hasta 3 decimales (balanzas), Precio Unitario, Descuento y Subtotal en PYG.
- Liquidación dinámica de Gravadas 10%, IVA 10% (`/11`), Gravadas 5%, IVA 5% (`/21`), Exentas y Total IVA.

### RF-03: Desglose de Medios de Pago y Vouchers POS
- Exhibir montos pagados en moneda local (PYG) y equivalentes en moneda extranjera (USD, BRL, ARS).
- Si el cobro se procesó con tarjeta electrónica vía POS integrado (SPEC-002), imprimir en el ticket:
  * Marca de tarjeta (Visa, Mastercard, etc.).
  * Código de Autorización (`Auth: XXXXXX`).
  * Número de Comprobante / Voucher (`Voucher: TXXXX`).

### RF-04: Código de Control (CDC) y Código QR Oficial
- Generación del CDC oficial de 44 dígitos concatenando: Tipo Documento (2), RUC Emisor (8), DV RUC (1), Establecimiento (3), Punto Expedición (3), Número Factura (7), Tipo Contribuyente (1), Fecha Emisión AAAAMMDD (8), Tipo Emisión (1), Código Seguridad (9), y DV CDC Módulo 11 (1).
- Generación de Código QR con URL oficial para validación en el portal `https://ekuatia.set.gov.py/consultas-sifen/qr`.

---

## 3. REQUERIMIENTOS NO FUNCIONALES

### RNF-01: Formato Autónomo Offline
- El ticket y el CDC deben generarse instantáneamente de forma matemática en memoria sin requerir conexión a internet.

### RNF-02: Compatibilidad de Impresoras
- Soporte para impresión directa vía `QPrinter` / spooler del sistema operativo y copia en texto plano (ESC/POS compatible).
