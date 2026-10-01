# SPEC-007: Catálogo Táctil para Góndolas, Frutas/Verduras y Balanza en Vivo

## 1. Visión General y Objetivos
Proporcionar una interfaz táctil ergonómica y de alta velocidad para puntos de venta (*POS Touch-Screen*) orientada a la comercialización de productos de góndola sin código de barras o que requieren pesaje directo en mostrador (frutería, verdulería, panadería, fiambrería, carnicería y rotisería).

### Objetivos Principales:
1. **Ergonomía Táctil Rápida (< 2 toques por producto)**:
   - Botones y tarjetas de tamaño mínimo accesible (140x120px) con imágenes, nombre, código PLU y precio por unidad de medida (`Un` o `Kg`).
2. **Pestañas de Navegación por Categoría**:
   - Selector por departamentos: *Favoritos / Top Vendidos*, *Frutas & Verduras*, *Panadería & Confitería*, *Fiambrería*, *Carnicería*, *Bebidas & Kiosco*.
3. **Manejo Dual de Cantidades y Pesaje**:
   - **Productos Unitarios (`uom="Un"`)**: Un toque agrega `1` unidad directamente al carrito.
   - **Productos por Peso (`uom="Kg"`, `is_fractional=True`)**:
     - Conexión a balanza física RS232 (Toledo, Systel, Filizola, CAS) para capturar el peso estable en tiempo real.
     - Diálogo Numpad Táctil integrado con botones rápidos (`+100g`, `+250g`, `+500g`, `+1Kg`) y precisión estricta de hasta 3 decimales (`Decimal('0.001')`).
4. **Integración con Guardrail y Grilla de Ventas**:
   - Todo ítem seleccionado valida precio y stock mediante [`POSGuardrail.validate_sale_item()`](file:///c:/ENTORNO%20LOCAL/Control/.agents/skills/validator/validator.py) y se añade al [`VentasTableModel`](file:///c:/ENTORNO%20LOCAL/Control/ui/ventas_table_model.py).
5. **Driver Asíncrono de Balanza RS232 (`ScaleDriver` / `ScaleWorker`)**:
   - Hilo secundario `QThread` para lectura de puertos serie COM sin congelamiento de UI.

---

## 2. Diagrama de Flujo

```mermaid
flowchart TD
    User([Cajero / Pantalla Táctil]) -->|Presiona F6 o Botón Táctil| Dialog[TouchCatalogDialog]
    Dialog --> CatSelect[Selecciona Categoría: Frutas / Panadería]
    CatSelect --> ItemClick[Toca Tarjeta del Producto]
    
    ItemClick --> CheckUom{¿UOM = 'Kg' / Fraccionario?}
    CheckUom -->|No: Unitario| AddOne[Cantidad = Decimal('1.000')]
    CheckUom -->|Sí: Por Peso| WeightFlow{¿Balanza RS232 Activa?}
    
    WeightFlow -->|Sí| AutoScale[Lee Peso del ScaleWorker]
    WeightFlow -->|No / Manual| Numpad[TouchQuantityDialog Numpad Táctil]
    
    AutoScale --> Validate
    Numpad --> Validate
    AddOne --> Validate
    
    Validate[POSGuardrail.validate_sale_item] --> Table[VentasTableModel / Factura]
```

---

## 3. Especificación del Driver de Balanza RS232

| Protocolo | Formato de Trama Estándar | Parámetros Serial |
| :--- | :--- | :--- |
| **Toledo / Systel / Filizola** | `STX + Status + Peso (5-6 chars) + ETX` | 9600 bps, 8 bits, Sin paridad, 1 stop bit |
| **Continuo / Polling** | `W: 01.450 kg \r\n` | 4800 / 9600 bps |
| **Simulador / Mock** | Peso configurable en memoria | Buffer virtual para pruebas automáticas |

---

## 4. Requerimientos de Precisión Numérica
- **Prohibido `float`**: Las lecturas de peso se formatean como `Decimal(str(raw_weight)).quantize(Decimal('0.001'))`.
- **Cálculo de Subtotal**: `subtotal = (cantidad * precio_unitario).quantize(Decimal('1'), rounding=ROUND_HALF_UP)` para Guaraníes (`PYG`).
