# DICCIONARIO DE DOMINIO Y GLOSARIO TÉCNICO-COMERCIAL (POS TRIPLE FRONTERA)

Este documento define el vocabulario ubicuo, las reglas fiscales de la DNIT (Paraguay) y los estándares transaccionales para evitar inconsistencias en el desarrollo de la solución.

---

## 1. Régimen Fiscal y Facturación Electrónica (Paraguay)

### SIFEN (Sistema Integrado de Facturación Electrónica Nacional)
Plataforma oficial de la DNIT (Dirección Nacional de Ingresos Tributarios) que recibe, valida, autoriza y almacena los Documentos Tributarios Electrónicos (DTE). Toda venta formal debe ser emitida en formato XML firmado digitalmente y enviada a los Web Services de SIFEN.

### DTE (Documento Tributario Electrónico)
Comprobante fiscal estructurado en XML con validez legal. Los principales tipos para supermercados son:
- **Factura Electrónica (Tipo 1):** Comprobante estándar de venta al consumidor final o contribuyente.
- **Autofactura Electrónica (Tipo 4):** Utilizada para compras a personas físicas que no emiten factura formal.
- **Nota de Crédito Electrónica (Tipo 5):** Empleada para devoluciones, descuentos posventa o anulaciones.

### CDC (Código de Control)
Identificador alfanumérico único de 44 dígitos asignado a cada DTE. Se genera de forma determinística antes de transmitir el XML mediante la concatenación de:
- Tipo de documento (2 dígitos)
- RUC emisor sin DV (8 dígitos)
- Dígito verificador del RUC (1 dígito)
- Establecimiento (3 dígitos)
- Punto de expedición (3 dígitos)
- Número de documento secuencial (7 dígitos)
- Tipo de contribuyente (1 dígito)
- Fecha de emisión en formato YYYYMMDD (8 dígitos)
- Tipo de emisión (1 dígito: normal o contingencia)
- Código de seguridad aleatorio generado por el sistema (9 dígitos)
- Dígito verificador del CDC calculado por Módulo 11 (1 dígito)

### KuDE (Representación Gráfica del DTE)
Formato visual y físico del comprobante electrónico (impreso en ticket térmico ESC/POS de 80mm o formato PDF). Debe incluir obligatoriamente:
- Datos del emisor y cliente.
- Desglose de ítems, precios e impuestos (Exenta, 5%, 10%).
- CDC de 44 dígitos visible.
- Código QR estándar bidimensional con la URL de consulta pública de la DNIT.

### Identificación de Clientes
- **Contribuyentes:** RUC completo compuesto por número base y Dígito Verificador (DV) calculado mediante algoritmo Módulo 11 ponderado base 11.
- **Personas Físicas Locales:** Cédula de Identidad (CI) numérica.
- **Clientes Extranjeros (Brasil / Argentina / Resto del Mundo):** DNI, CPF o Pasaporte, indicando el código de país correspondiente en el esquema SIFEN.
- **Consumidor Final (Sin nombre):** Ventas menores sin exigencia de identificación nominal según los topes legales vigentes.

---

## 2. Monedas, Cotizaciones y Redondeo

### Moneda Base (PYG - Guaraní)
Moneda contable y legal obligatoria del sistema.
- **Precisión:** Entero sin decimales (`Decimal('1')`).
- **Regla de Redondeo:** Redondeo aritmético estándar o compensatorio legal al entero más próximo.

### Monedas Transaccionales Secundarias
- **USD (Dólar estadounidense):** Precisión 2 decimales (`Decimal('0.01')`).
- **BRL (Real brasileño):** Precisión 2 decimales (`Decimal('0.01')`).
- **ARS (Peso argentino):** Precisión 2 decimales (`Decimal('0.01')`).

### Cotización Compra vs. Cotización Venta
- **Tipo Comprador (`buy_rate`):** Tasa aplicada cuando el cliente entrega divisa extranjera en caja para pagar una compra en Guaraníes.
- **Tipo Vendedor (`sell_rate`):** Tasa aplicada cuando el supermercado entrega divisa extranjera (por ejemplo, al devolver cambio en dólares o reales).
- **Inmutabilidad:** Cada actualización de cotización genera un nuevo registro temporal. Las ventas cerradas guardan la cotización histórica exacta aplicada en su momento.

### Split de Pago (Cobro Mixto / Pagos Cruzados)
Capacidad de saldar una única cuenta combinando múltiples medios y monedas:
- Ejemplo: Total 350.000 Gs. saldado con USD 20.00 en efectivo + BRL 50.00 vía PIX + saldo restante en tarjeta de débito local.
- **Vuelto Cruzado:** La diferencia a favor del cliente calculada en Guaraníes y liquidada en la moneda que el cajero seleccione según la disponibilidad física en gaveta.

---

## 3. Códigos de Barra y Pesables en Supermercado

### EAN-13 Estándar
Código de barras comercial de 13 dígitos numéricos asignado por GS1 a productos envasados de fábrica.

### EAN-13 In-Store (Balanza de Mostrador)
Formato de código de barras dinámico generado por balanzas de sectores como carnicería, verdulería, panadería o fiambrería:
- **Estructura:** `PP CCCCC VVVVV D`
  - `PP` (2 dígitos): Prefijo reservado para uso interno (`20` o `21`).
  - `CCCCC` (5 dígitos): Código PLU del producto asociado en la base de datos.
  - `VVVVV` (5 dígitos): Carga útil de la balanza, que según su configuración puede ser:
    * **Modo Peso:** Peso exacto en kilogramos con 3 decimales (ej. `01500` = 1,500 kg).
    * **Modo Importe:** Precio total precalculado en Guaraníes sin decimales.
  - `D` (1 dígito): Dígito de control estándar EAN-13.

---

## 4. Auditoría de Caja y Prevención de Pérdidas

### Arqueo Ciego
Procedimiento de fin de turno donde el cajero debe declarar físicamente los billetes, monedas y comprobantes en su poder sin conocer los saldos teóricos esperados por el sistema, evitando ajustes manuales fraudulentos.

### Reporte X (Corte Parcial)
Informe informativo de auditoría intermedia que imprime los acumulados de ventas, cobros y anulaciones hasta el momento sin cerrar el turno contable ni resetear acumuladores.

### Reporte Z (Cierre Fiscal/Definitivo de Caja)
Informe final que bloquea el turno, consolida las ventas del período, calcula sobrantes o faltantes por divisa, cierra la sesión del operador y emite el asiento contable para sincronización.
