# Flujo Operativo del Sistema (Punto de Venta)

Para garantizar un funcionamiento correcto, un inventario exacto y finanzas precisas, el sistema debe operarse en un orden lógico secuencial (desde lo más general hasta la transacción del día a día). 

Aquí tienes el flujo maestro paso a paso de cómo se debe implementar y operar el sistema en el supermercado:

## FASE 1: Configuración Maestra (Setup Inicial)
Estos pasos se hacen por única vez o de manera esporádica cuando el supermercado crece.

1. **Registrar Marcas y Categorías**
   - *Ejemplo:* Crear categorías como "Lácteos", "Carnicería", "Bebidas". Crear marcas como "Coca-Cola", "Trébol".
2. **Registrar Clientes Habituales y Mayoristas** (Opcional)
   - *Ejemplo:* Dar de alta al cliente "Juan Pérez" con su RUC, o crear un cliente "Consumidor Final" genérico para las ventas rápidas.
3. **Registrar Proveedores**
   - *Ejemplo:* Dar de alta a "Distribuidora Guaraní S.A." con su número de contacto y RUC. Sin el proveedor, no podrás ingresar mercadería al sistema.

---

## FASE 2: Gestión de Catálogo y Precios
Donde se define qué se vende y a qué valor.

4. **Alta de Artículos (Gestión de Artículos)**
   - Crear el producto.
   - Asignarle su código de barra principal (EAN-13) o código de balanza.
   - Definir si se vende por "Unidad" o si es "Fraccionable" (Kilos, Litros).
   - Establecer el Costo Base y el Precio de Venta Público (PYG).
5. **Configurar Precios Especiales (Opcional)**
   - **Precios por Volumen:** *Ejemplo:* "Llevando 6 unidades, el precio baja a 5.000 ₲".
   - **Promociones Temporales:** *Ejemplo:* "Viernes de Descuento: Cerveza a 10.000 ₲ válido hasta el domingo".
   - **Listas de Precios:** Asignar una lista "Mayorista" para ciertos clientes VIP.

---

## FASE 3: Ingreso de Inventario
El dinero se convierte en mercadería.

6. **Ingreso de Compras (Recepción de Mercadería)**
   - Ingresar la Factura de Compra seleccionando al Proveedor creado en el paso 3.
   - Escanear los productos que llegaron y declarar la **Cantidad** ingresada.
   - *Automático:* El sistema crea lotes de inventario, actualiza el Costo Promedio (CPP) si la mercadería subió de precio, e inyecta las unidades al Stock.

> [!CAUTION]
> Nunca vendas un producto cuyo paso 6 (Ingreso de Compras) no se haya completado, de lo contrario, el sistema registrará stock negativo.

---

## FASE 4: Operación de Caja (El Día a Día)
El corazón del supermercado.

7. **Apertura de Caja (Inicio de Turno)**
   - El cajero ingresa al sistema y declara el fondo fijo de sencillo (Ej: 150.000 ₲ en billetes pequeños).
8. **Ventas (Facturación Continua)**
   - El cajero escanea productos de corrido.
   - El motor `POSGuardrail` valida que los cálculos de precios, centavos y cantidades fraccionadas (como la carne) sean matemáticamente perfectos.
   - **Cobro:** El cliente paga (El sistema soporta split de pagos: ej. Mitad en Dólares, mitad con Tarjeta, calculando el vuelto exacto en Guaraníes).
   - *Automático:* Se deduce el stock (aplicando FIFO: se descuentan los lotes más viejos primero).
9. **Gestión de Devoluciones / Notas de Crédito** (Solo si ocurre)
   - Un cliente devuelve un producto defectuoso.
   - Se procesa la devolución: el sistema reintegra el dinero contablemente y devuelve el ítem al stock disponible.
10. **Arqueo y Cierre de Caja (Fin de Turno)**
    - El cajero cuenta el dinero físico de la gaveta (Efectivo PYG, Efectivo USD, Tickets de Tarjeta de Crédito).
    - Se ingresan los totales en la pantalla de Arqueo.
    - El sistema revela si hay **Sobrantes** o **Faltantes** de dinero comparando lo físico con las ventas del día, y luego cierra el turno.
