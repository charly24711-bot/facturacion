# PLAN-005: Plan de Implementación - Driver de Impresión ESC/POS

## 1. Componentes a Desarrollar

### Componente 1: Motor Generador de Comandos ESC/POS (`ESCPOSCommandBuilder`)
- Construcción estructurada de bytes con codificación configurable (`cp850`, `latin1`, `utf-8`).
- Formateo de texto en tabla (2 columnas, 3 columnas, 4 columnas) con ancho fijo de 40 o 42 caracteres.
- Generación de comandos de QR code nativo según la especificación ESC/POS de Epson/XPrinter (`GS ( k`).
- Comandos de corte y apertura de cajón de dinero.

### Componente 2: Driver de Comunicación de Hardware (`ESCPOSPrinterDriver`)
- **Modo Red (TCP/IP)**: `socket.create_connection((ip, port), timeout=2.0)`.
- **Modo Windows RAW Spooler**: Uso de `ctypes.windll.winspool.drv` (`OpenPrinterW`, `StartDocPrinterW`, `StartPagePrinter`, `WritePrinter`, `EndPagePrinter`, `EndDocPrinter`, `ClosePrinter`).
- **Modo Serial**: Manejo de puerto `COMx` con timeout.
- **Modo Simulador**: Buffer en memoria para tests unitarios e integración continua.

### Componente 3: Worker Asíncrono de PyQt6 (`ESCPOSPrintWorker`)
- Hilo secundario `QThread` para evitar bloquear el Event Loop de PyQt6 al imprimir o abrir cajón.
- Señales `print_finished(bool, str)` y `progress(str)`.

### Componente 4: Integración en Interfaz de Usuario
- Integración en [`ui/ticket_dialog.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/ticket_dialog.py): Botón "⚡ Impresión Rápida ESC/POS" y soporte de configuración.
- Integración en [`ui/payment_dialog.py`](file:///c:/ENTORNO%20LOCAL/Control/ui/payment_dialog.py): Disparo de pulso de apertura de cajón si la venta incluye efectivo.

### Componente 5: Pruebas Unitarias Automatizadas
- [`tests/test_escpos_driver.py`](file:///c:/ENTORNO%20LOCAL/Control/tests/test_escpos_driver.py): Pruebas de builders, secuencias de bytes, simulador, worker asíncrono y resiliencia ante errores de conexión.
