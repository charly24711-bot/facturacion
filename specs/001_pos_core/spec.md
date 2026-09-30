# SPEC-001: NÚCLEO POS, BALANZAS Y LIQUIDACIÓN FISCAL TRIPLE FRONTERA

**Estado:** Aprobado / Implementado  
**Versión:** 1.0.0  
**Fecha:** Septiembre 2026

---

## 1. PROPÓSITO Y ALCANCE
Proveer el motor de punto de venta (POS) para terminales de supermercado en zona de Triple Frontera, capaz de procesar ventas de alta velocidad, lectura de balanzas in-store (EAN-13), liquidación fiscal en vivo según normativa DNIT de Paraguay (IVA 10%, 5% y Exentas), cobros multi-moneda (PYG, USD, BRL, ARS) y operación 100% offline.

---

## 2. REQUERIMIENTOS FUNCIONALES

### RF-01: Operaciones de Venta y Carrito
- Búsqueda de productos por código de barras, PLU o descripción.
- Visualización de foto de producto, descripción, precio unitario, cantidad, IVA y subtotal.
- Manejo de cantidades con teclado numérico y multiplicador (`*` o ingreso directo).
- Eliminación de ítems individuales (`[Supr]`) y cancelación de venta completa (`[F9]`).
- Selector reactivo de canales de precios (Minorista, Mayorista, Distribuidor).

### RF-02: Balanzas In-Store (EAN-13)
- Decodificación automática de códigos con prefijo `20` o `21` (`PP CCCCC PPPP D`).
- Conversión de gramos a kilogramos con precisión de hasta 3 decimales (`Decimal('0.001')`).
- Cálculo exacto del subtotal multiplicando peso por precio por kilo.

### RF-03: Régimen Fiscal Paraguay (DNIT / Ley 6380)
- Cálculo de IVA 10%: `subtotal / 11`.
- Cálculo de IVA 5%: `subtotal / 21`.
- Exentas: 0% IVA.
- Panel en vivo en pantalla principal con desglose de Gravadas 10%, IVA 10%, Gravadas 5%, IVA 5%, Exentas y Total IVA.
- Autocompletado de RUC y cálculo de Dígito Verificador Módulo 11 para emisión de comprobante con CDC (44 dígitos).

### RF-04: Cobros Multi-Moneda y Cuentas Corrientes
- Moneda base en Guaraníes (`PYG`, sin decimales).
- Aceptación de divisas secundarias (`USD`, `BRL / PIX`, `ARS`) calculadas según cotización vigente inmutable.
- Modalidad de venta a crédito con control estricto de límite disponible del cliente.

---

## 3. REQUERIMIENTOS NO FUNCIONALES

### RNF-01: Tolerancia Cero a `float`
- Todos los cálculos monetarios, precios, subtotales, totales, impuestos y existencias de stock deben emplear `decimal.Decimal`.

### RNF-02: Rendimiento UI
- La grilla del carrito debe utilizar `QTableView` con `QAbstractTableModel` para asegurar latencias inferiores a 16ms en inserciones continuas.

### RNF-03: Resiliencia Offline-First
- Operaciones 100% locales sobre SQLite en modo WAL, tolerando desconexión de red sin interrumpir el flujo de caja.
