# PLAN-004: ARQUITECTURA TÉCNICA DEL GENERADOR DE TICKETS KUDE

**Especificación Asociada:** [SPEC-004](file:///c:/ENTORNO%20LOCAL/Control/specs/004_impresion_ticket_kude/spec.md)  
**Estado:** Implementado

---

## 1. ARQUITECTURA DEL MOTOR DE EMISIÓN DE TICKETS

```
┌────────────────────────────────────────────────────────┐
│                   TicketDialog (PyQt6)                 │
│  - Carga Invoice, Items, Payments y CompanySettings    │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    KuDE Format Engine                  │
│  - Formateo monoespaciado 40 columnas (80 mm)          │
│  - Tax Engine (Liquidación IVA 10/5/0)                 │
│  - CDC Generator (Algoritmo Módulo 11 en 43 dígitos)   │
│  - QR Engine (Librería `qrcode` en Base64 / Pixmap)    │
│  - POS Voucher Renderer (Auth, Voucher, Brand)         │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                  Hardware Output Channels              │
│  1. Visor UI (QTextEdit con tipografía Courier New)    │
│  2. Impresión Nativa (QPrinter / QPrintDialog)         │
│  3. ESC/POS Raw Text Stream                            │
└────────────────────────────────────────────────────────┘
```

---

## 2. ESTRUCTURA DE COMPOSICIÓN DEL CDC (44 DÍGITOS)

| Campo | Longitud | Descripción | Ejemplo |
| :--- | :---: | :--- | :--- |
| `tipo_doc` | 2 | Tipo de documento fiscal (01 = Factura Electrónica) | `01` |
| `ruc_emisor` | 8 | RUC del emisor sin DV relleno con ceros a la izquierda | `80012345` |
| `dv_ruc` | 1 | Dígito verificador del RUC de la empresa | `6` |
| `estab` | 3 | Código del establecimiento | `001` |
| `pto_exp` | 3 | Código del punto de expedición | `001` |
| `nro_sec` | 7 | Número correlativo de la factura | `0000123` |
| `tipo_contrib`| 1 | 1 = Persona Jurídica, 2 = Persona Física | `1` |
| `fecha_emision`| 8 | Formato `AAAAMMDD` | `20261001` |
| `tipo_emision` | 1 | 1 = Normal, 2 = Contingencia | `1` |
| `cod_seguridad`| 9 | Código numérico aleatorio/seguro de 9 dígitos | `100000001` |
| **`dv_cdc`** | **1** | **Dígito Verificador Módulo 11 de los 43 dígitos previos** | `X` |

---

## 3. INTEGRACIÓN CON VOUCHERS DE COBRO POS

Al iterar los pagos asociados a la factura en `models.Payment`, si `p.auth_code` o `p.voucher_nro` están presentes:
```text
  [TARJETA VISA] Auth: 789123 | Voucher: T1024
```
se incluye en la sección de medios de pago del comprobante.
