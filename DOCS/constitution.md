# CONSTITUCIÓN DEL SISTEMA POS - SUPERMERCADO TRIPLE FRONTERA

**Versión:** 1.0.0  
**Fecha de Ratificación:** Septiembre 2026  
**Alcance:** Sistema de Punto de Venta (POS) y Back-Office para Entorno Minorista/Mayorista de Alta Rotación en Triple Frontera (Paraguay - Brasil - Argentina).

---

## 1. PRINCIPIOS FUNDAMENTALES E INMUTABLES

### Artículo 1.1: Stack Tecnológico Obligatorio
1. **Frontend / UI**: Exclusivamente **Python 3.12+** y **PyQt6**.
2. **Patrón de Presentación**: Arquitectura Modelo-Vista-Controlador (MVC). En grillas transaccionales de alto tráfico queda prohibido el uso de `QTableWidget`; se debe utilizar `QTableView` respaldado por `QAbstractTableModel` para garantizar rendimiento instantáneo.
3. **Persistencia Local**: Base de datos local **SQLite** (`stock_control.db`) gestionada mediante **SQLAlchemy** (ORM y Core) con modo WAL (`Write-Ahead Logging`) activado.

### Artículo 1.2: Aritmética Financiera Estricta (Tolerancia Cero a `float`)
1. **Prohibición Absoluta**: Queda terminantemente prohibido el uso del tipo primitivo `float` o conversiones implícitas de punto flotante en cualquier cálculo monetario, de inventario, pesaje, margen o liquidación impositiva.
2. **Uso de Decimal**: Toda operación matemática debe implementarse exclusivamente con `decimal.Decimal` y cuantización explícita.
3. **Moneda Base**: Guaraní Paraguayo (`PYG`), cuantizado a enteros (`Decimal('1')`). No admite centavos ni fracciones decimales en importes finales.
4. **Monedas Secundarias**: Dólares Americanos (`USD`), Reales Brasileños (`BRL`) y Pesos Argentinos (`ARS`), cuantizados estrictamente a 2 decimales (`Decimal('0.01')`).
5. **Inmutabilidad de Cotizaciones**: Cada ajuste de tipo de cambio genera un registro nuevo inmutable en la tabla `currency_rates`. Está prohibida la sobreescritura (`UPDATE`) destructiva de tasas de cambio aplicadas a turnos o comprobantes anteriores.

### Artículo 1.3: Régimen Fiscal y Normativas DNIT (Paraguay)
1. **Tasas de IVA (Ley 6380/19)**:
   * **IVA 10%**: `total / 11` (Productos generales, manufacturas, perfumería y limpieza).
   * **IVA 5%**: `total / 21` (Canasta básica, carnes, productos agrícolas, harinas y productos de la canasta familiar).
   * **Exentas (0%)**: `IVA = 0` (Libros, medicamentos o artículos con exención legal expresa).
2. **Comprobantes y Facturación**:
   * Generación reglamentaria de Código de Control (CDC) de 44 dígitos y representación gráfica KuDE.
   * Compatibilidad nativa con exportación Hechauka / Marangatú (RG90) para libros de compras y ventas.

### Artículo 1.4: Integración de Balanzas e In-Store Hardware
1. **Códigos EAN-13 de Balanza**: Prefijos `20` o `21`.
   * Estructura estándar: `PP CCCCC PPPP D` (PP=Prefijo, C=Código PLU de 5 dígitos, P=Peso/Precio de 5 dígitos en gramos, D=Dígito verificador).
2. **Precisión de Pesaje**: Las cantidades pesadas admiten hasta un máximo de 3 decimales (`Decimal('0.001')`).
3. **Periféricos y Puertos**: La lectura de puertos seriales (RS232) de balanzas o lectores de códigos de barras debe ejecutarse en hilos secundarios desacoplados (`QThread`) para asegurar que la interfaz de usuario nunca sufra micro-bloqueos.

### Artículo 1.5: Resiliencia Offline-First
1. **Autonomía Operativa**: Toda transacción de venta, movimiento de caja, arqueo o consulta de inventario debe resolverse en milisegundos contra la base de datos local SQLite.
2. **Tolerancia a Fallos de Red**: La caída de la red externa o del servidor central jamás debe impedir que una caja continúe cobrando o emitiendo tickets.
3. **Trazabilidad Global**: Toda tabla transaccional (`ventas`, `detalles`, `pagos`, `arqueos`, `movimientos`) debe poseer identificadores únicos universales (`uuid`), marcas de sincronización (`synced: bool`) y marca de tiempo (`sync_timestamp`).

---

## 2. METODOLOGÍA DE DESARROLLO (SDD - Spec-Driven Development)

El ciclo de vida de cualquier funcionalidad, refactor o modificación en este proyecto se rige por los siguientes pasos obligatorios:

```
[Paso 1: Constitución] ──> [Paso 2: Especificación (spec.md)] ──> [Paso 3: Clarificación]
                                       │
[Paso 7: Validación]   <── [Paso 6: Implementación] <── [Paso 5: Tareas (tasks.md)] <── [Paso 4: Planificación (plan.md)]
         │
         └──> [Loop al Paso 2: Mantenimiento / Nuevas Fases]
```

1. **Paso 1 - Constitución (`docs/constitution.md`)**: Define los mandatos inmutables de arquitectura, legalidad y calidad (este documento).
2. **Paso 2 - Especificación (`specs/NNN/spec.md`)**: Describe el qué y el por qué de la necesidad de negocio, casos de uso y criterios de aceptación sin ambigüedad.
3. **Paso 3 - Clarificación**: Diálogo y validación de supuestos de frontera (moneda, hardware, auditoría) antes de escribir código.
4. **Paso 4 - Planificación (`specs/NNN/plan.md`)**: Diseño técnico, modelos de datos, arquitectura de componentes UI/Controlador y riesgos.
5. **Paso 5 - Tareas (`specs/NNN/tasks.md`)**: Checklist granular y ejecutable de tareas atómicas numeradas.
6. **Paso 6 - Implementación**: Escritura de código siguiendo estrictamente las tareas aprobadas y las directivas constitucionales.
7. **Paso 7 - Validación**: Ejecución de suites de prueba automatizadas (unitarias, integración, estrés y ergonomía) e invocación del guardrail de validación.

---

## 3. GUARDRAIL DE SEGURIDAD OBLIGATORIO

Cualquier operación que intente persistir una venta, modificar inventario o alterar precios debe pasar obligatoriamente por el validador central:
* **Módulo**: [validator.py](file:///c:/ENTORNO%20LOCAL/Control/.agents/skills/validator/validator.py)
* **Función**: `POSGuardrail.validate_sale_item(payload)`
* **Condición de Rechazo**: Si la función retorna `is_valid == False`, la transacción debe ser cancelada de inmediato y reportar los errores en la UI.
