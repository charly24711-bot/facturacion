# BITÁCORA DE DESARROLLO Y FUNCIONALIDAD DEL SISTEMA POS
**Supermercado Triple Frontera (Paraguay - Brasil - Argentina)**  
*Actualizado al: 06 de Septiembre de 2026*

---

## 📅 Sábado, 05 de Septiembre de 2026

### 1. Módulo de Sesiones de Caja y Reportes Z (`models.CashSession`, `models.CashAudit`)
- **Apertura y Cierre de Caja:** Gestión de sesiones vinculadas al usuario cajero con identificación única (`session_id`).
- **Cobranzas Multi-Moneda:** Registro de transacciones en Guaraníes (`PYG`), Dólares (`USD`), Reales (`BRL`) y Pesos Argentinos (`ARS`).
- **Arqueo y Cuadre de Turno (Reporte Z):** Comparación matemática entre el monto teórico calculado por las ventas del sistema y el monto físico declarado por el cajero, registrando diferencias sin alterar el historial contable.

### 2. Control de Inventario FIFO y Trazabilidad de Lotes (`models.ProductBatch`)
- **Deducción de Stock por Vencimiento:** Al concretar una venta, el inventario se descuenta automáticamente del lote con fecha de expiración más próxima (`First In, First Out`).

### 3. Integración de Balanzas In-Store (EAN-13)
- **Lectura Automática de Prefijos 20/21:** Decodificación instantánea de etiquetas de balanza con estructura `PP CCCCC PPPP D` (Prefijo, PLU, Peso en gramos y Dígito Verificador), calculando precio y fracción de kilogramos al escanear.

### 4. Pruebas de Carga y Robot E2E
- **Simulación Masiva:** Ejecución de 1.000 ventas concurrentes bajo SQLite (`test_carga_masiva.py`) sin bloqueos de concurrencia ni pérdida de integridad referencial.
- **Documentación:** Publicación de `DOCS/FLUJO_OPERATIVO.md` y formalización de estándares en `DOCS/GLOSARIO.md`.

---

## 📅 Domingo, 06 de Septiembre de 2026

### 1. Régimen Fiscal DNIT e IVA Paraguay (Ley 6380/19)
- **Reclasificación de Tasas de IVA:**
  * **IVA 5%:** Canasta básica familiar, productos agrícolas, carnes y harinas (`total / 21`).
  * **IVA 10%:** Productos procesados, artículos de limpieza, bebidas y perfumería (`total / 11`).
  * **Exentas (0%):** Artículos exentos por normativa tributaria.
- **Formateo Numérico Limpio:** Eliminación de ceros residuales de SQLite (`120.0000000000` ➔ `120`), respetando hasta 3 decimales únicamente para pesaje de balanzas.

### 2. Panel Fiscal en Vivo en Pantalla Principal (`ui/main_window.py`)
- **Sustitución de Espacio Inactivo:** Se retiró la sección obsoleta *"Créditos [F3]"* y se instaló el panel permanente de **Liquidación I.V.A. en Tiempo Real** (Gravadas 10%, IVA 10%, Gravadas 5%, IVA 5%, Exentas y Total IVA).
- **Atajos Ergonómicos de Teclado:** Botonera rápida integrada: `[F2] Buscar Artículo`, `[F5] Presupuestos`, `[F8] RUC Clientes` y `[F10] Arqueo de Caja`.

### 3. Padrón DNIT Offline y Facturación con RUC (`padron_ruc`)
- **Consulta Instantánea:** Autocompletado offline de Razón Social y Dígito Verificador mediante algoritmo Módulo 11 (Resolución General 1530/05).
- **Emisión de Comprobante KuDE y CDC:** Generación del **Código de Control (CDC)** oficial de 44 dígitos y desglose legal de IVA en ticket térmico de 80 mm (`ui/ticket_dialog.py`).

### 4. Control Visual de Stock y Grillas Ordenables
- **Stock Negativo en Rojo:** Implementación de `StockItemDelegate` en grillas para resaltar existencias agotadas o en negativo (`-8`) con fondo rosa suave y tipografía roja negrita (inmune al resaltado de selección).
- **Ordenamiento Numérico Bidireccional (`NumericTableWidgetItem`):** Permite ordenar columnas de precios, stock e impuestos de menor a mayor y viceversa (`▲` / `▼`) con base en valores `Decimal` reales.
- **Advertencia Preventiva:** Alerta al cajero al intentar vender productos con stock insuficiente o negativo antes de agregarlos al carrito.

### 5. Catálogo Fotográfico y Visores de Producto
- **Generación de 103 Fotos de Productos (`assets/images/`):** Creación de tarjetas visuales categorizadas por rubro (Carnicería, Lácteos, Bebidas, Limpieza, Panadería).
- **Visor Lateral POS:** Panel activo de 260 px en la pantalla de cobro que exhibe la foto, código, precio y stock del artículo en foco.
- **Buscador con Fotos (`[F2] / [F4]`):** Miniaturas (thumbnails) en cada fila de la grilla de búsqueda y tarjeta de foto de 210x160 px con actualización reactiva al navegar con las flechas del teclado.
- **Resolución Inmune de Rutas (`resolve_image_path`):** Localización segura de imágenes independiente del directorio de inicio del ejecutable.

### 6. Circuito Comercial de Presupuestos y Cotizaciones (`[F6]` / `[F5]`)
- **Sustitución de "Remisión [F7]" por "Presupuesto [F6]":** Permite al cliente solicitar una cotización formal impresa en 4 monedas (PYG, USD, BRL, ARS) con validez de 15 días **sin alterar ni descontar stock de góndola**.
- **Cargar Presupuesto al Carrito (`[F5]`):** El cajero recupera la cotización pendiente con un solo clic o atajo. Al concretar la venta con `[F11] Cobrar`, el presupuesto se actualiza automáticamente a `'FACTURADO'` y recién allí se descuenta el stock físico de la base de datos.
- **Blindaje de Señales PyQt:** Protección de métodos visuales contra argumentos imprevistos de eventos `QItemSelection`, garantizando cero caídas en ejecución.

### 7. Seguridad, Autenticación y Panel Administrativo (`ui/admin_window.py`)
- **Modelo de Usuarios (`models.User`):** Cifrado de contraseñas mediante hash SHA-256 (`hash_password` / `verify_password`) con roles `ADMIN` y `CAJERO`.
- **Auto-Login para Desarrollo:** Inicio inmediato con usuario `admin` (`main.py`) para máxima agilidad en el ciclo de trabajo.
- **Panel Administrativo Back-Office:** Separación arquitectónica entre la terminal de cobro POS (Front-Office) y la gestión de compras, costos, márgenes, lotes y timbrados (Back-Office).

### 8. Dashboard Enriquecido y Ventana Emergente de Ventas (`ui/invoice_detail_dialog.py`)
- **Analítica Retail en Vivo:** Fila de 5 KPIs (`Ventas del Día`, `Comprobantes`, `Ticket Promedio`, `IVA Liquidado`, `Stock Crítico / FIFO`).
- **Tesorería Multidivisa Triple Frontera:** Panel de arqueo con desglose de pagos en `PYG`, `USD`, `BRL / PIX` y `ARS`.
- **Rotación de Góndola:** Grilla con el `Top 5 de Artículos Más Vendidos` (volumen e importe en Gs.).
- **Monitor de Cajas y Alertas FIFO:** Estado de terminales abiertas y alertas de lotes que vencen en menos de 7 días.
- **Detalle de Venta al Clic:** Al hacer clic en cualquier factura del historial, se despliega una ventana emergente modal con cabecera legal, grilla de ítems, precios, impuestos, pagos y botón para reimprimir el ticket KuDE con QR oficial SIFEN.

### 9. Batería de Stress Integral 360° (`test_stress_integral_360.py`)
- **Stress de Compras y Lotes FIFO:** Procesamiento masivo de 50 compras a proveedores (300 ítems y 300 lotes generados con fecha de vencimiento incremental) en 0.17s (295.5 compras/seg) totalizando Gs. 408.375.000 invertidos en mercadería.
- **Stress de Devoluciones y Notas de Crédito:** 25 notas de crédito emitidas atómicamente con restitución exacta de stock a góndola y validación `POSGuardrail`.
- **Stress de Cuentas Corrientes (Fiados):** 20 transacciones de cargo a crédito auditando el bloqueo automático ante excedente de límite (`cli_limite`), 5 abonos parciales y conciliación contable ($\sum \text{Debe} - \sum \text{Haber}$) en `Decimal`.
- **Motor de Escalas de Precio Mayorista:** Verificación automática de precios por volumen (Minorista, Mayorista x 6, Distribuidor x 12).
- **Arqueo Ciego con Discrepancias Reales:** Auditoría de fin de turno simulando faltante en PYG (-Gs. 20.000), sobrante en BRL (+R$ 20.00) y cuadre exacto en USD (US$ 0.00), grabados inmutablemente en `models.CashAudit`.

### 10. Suite Comercial 360° para Supermercados (Fases 1, 2 y 3)
- **Fase 1 - Ergonomía POS y Operaciones de Caja:**
  * Selector reactivo de Canales de Precios en vivo (`cmb_canal_precio`) con jerarquía: Promoción > Escala Tier > Canal Seleccionado > Lista Cliente > Minorista Base.
  * Quitar ítem del carrito con `[Supr] / Delete` y recálculo instantáneo de IVA y totales.
  * Cancelar venta en curso con `[F9]` y confirmación rápida.
  * Movimientos de Caja / Sangría (`ui/caja_movimiento_dialog.py`) con ticket impreso y registro en `CashMovement`.
  * Arqueo ciego integrando fondo fijo y sangrías para calcular el efectivo neto real.
- **Fase 2 - Módulos Administrativos del Back-Office:**
  * Gestión visual de usuarios y cajeros (`ui/users_management_dialog.py`) con roles `ADMIN`, `GERENTE`, `CAJERO` y hash SHA-256.
  * Registro y control de mermas, roturas y ajustes de inventario (`ui/stock_adjustment_dialog.py`) con afectación atómica de `art_stkini`.
  * Exportador Oficial Tributario DNIT Hechauka / Marangatú (`ui/hechauka_export_dialog.py`) para Libros de Ventas y Compras con IVA 10% (`total / 11`) e IVA 5% (`total / 21`).
- **Fase 3 - Utilidades de Góndola y Seguridad:**
  * Generador de códigos de barras vectoriales EAN-13 y Code-128 (`ui/barcode_renderer.py`).
  * Impresor de etiquetas de góndola adhesivas A4 (14 y 24 etiquetas) y rollos térmicos (`ui/shelf_labels_dialog.py`) con precio destacado en PYG y USD, vista previa y exportación directa a PDF.
  * Bloqueo y pausa de terminal POS con PIN y teclado numérico táctil (`ui/lock_screen_dialog.py`), atajo `[F12]`, cronómetro en vivo y rescate por supervisor.

---

## 📊 Resumen de Estado Actual del Repositorio
- **Framework UI:** PyQt6 con modelo MVC (`QTableView` + `QAbstractTableModel`).
- **Base de Datos:** SQLite (`stock_control.db`) con SQLAlchemy ORM.
- **Aritmética Financiera:** 100% `decimal.Decimal` con cuantización estricta (prohibido `float`).
- **Tests Automatizados:** 100% superados (`test_fase1_pos_ergonomia.py` (27/27), `test_fase2_backoffice.py` (31/31), `test_fase3_gondola_seguridad.py` (14/14), `test_stress_integral_360.py`, `test_riguroso_panel_admin.py`, etc.).

