# PLAN-007: Plan de Implementación - Catálogo Táctil y Balanza en Vivo

## Fase 1: Driver y Worker de Balanza RS232 (`utils/scale_driver.py`)
1. Implementar `ScaleDriver`:
   - Parser de tramas continuas y a demanda para protocolos Toledo / Systel / Filizola / Formato genérico ASCII.
   - Manejo de puerto serie con `pyserial` (o fallback a simulador seguro si no hay puerto físico).
   - `MockScaleDriver`: Simulador de pesaje para pruebas automatizadas y modo desarrollo.
2. Implementar `ScaleWorker (QThread)`:
   - Hilo de lectura continua que emite la señal `weight_changed(Decimal, bool)` (peso estable/inestable).

## Fase 2: Componentes UI Táctiles
1. **Numpad Táctil Modal (`ui/touch_numpad_dialog.py`)**:
   - Pantalla numérica táctil de alta visibilidad para ingresar cantidades o peso en Kg.
   - Botones rápidos: `+0.100`, `+0.250`, `+0.500`, `+1.000`, `+2.000`.
   - Soporte para captura directa desde la balanza si está conectada.
2. **Diálogo de Catálogo Táctil (`ui/touch_catalog_dialog.py`)**:
   - Pestañas de categorías con diseño moderno Dark Mode.
   - Grilla con `QScrollArea` renderizando tarjetas táctiles (`TouchProductCard`).
   - Campo de búsqueda rápida con teclado táctil en pantalla.
   - Selección rápida de productos y retorno de ítem + cantidad validada.

## Fase 3: Integración en Pantalla Principal (`ui/main_window.py`)
1. Agregar botón en la barra superior: `"🖐️ Catálogo Táctil [F6]"`.
2. Asignar atajo de teclado **F6**.
3. Conectar la selección del producto al guardrail `POSGuardrail.validate_sale_item()` y al modelo de ventas `ventas_model.add_item()`.

## Fase 4: Suite de Pruebas Automatizadas (`tests/test_touch_catalog.py`)
1. Test de parsing de tramas de balanza con `Decimal('0.001')`.
2. Test de cálculo de subtotales para productos fraccionarios y pesables.
3. Test de carga y filtrado de categorías en `TouchCatalogDialog`.
4. Test de validación con el guardrail `POSGuardrail`.

## Fase 5: Memoria Operativa (`MEMORY.md`)
1. Registrar la Fase 11 completada en la tabla de hitos y mapa de arquitectura.
