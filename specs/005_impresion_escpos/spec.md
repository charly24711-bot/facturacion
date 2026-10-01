# SPEC-005: Driver Directo de Impresión Térmica ESC/POS (USB / Serial / Red)

## 1. Visión General y Objetivos
Proporcionar un motor nativo y asíncrono de impresión directa en formato de comandos binarios **ESC/POS** para impresoras térmicas de 80mm y 58mm (Epson, Hasar, Bematech, XPrinter, Bixolon, etc.) en puntos de venta (POS). 

### Objetivos Principales:
1. **Emisión Física Instantánea (< 100 ms)**: Enviar streams de bytes crudos (RAW) a la impresora térmica sin abrir cuadros de diálogo del sistema operativo.
2. **Corte Automático y Apertura de Gaveta de Dinero**: Enviar comandos de corte de papel (parcial/total) y pulsos eléctricos a la gaveta de efectivo (`ESC p`).
3. **Múltiples Canales de Comunicación**:
   - **RED / TCP-IP**: Socket directo a IP y puerto (predeterminado: 9100).
   - **USB / Spooler Windows RAW**: Uso de la API nativa de Windows `winspool.drv` vía `ctypes` para enviar bytes crudos a cualquier impresora instalada sin dependencias externas.
   - **SERIAL (COM)**: Escritura directa a puertos `\\.\COMx`.
   - **SIMULADOR / VIRTUAL**: Buffer de memoria para testing automatizado y diagnóstico.
4. **No-Bloqueo de UI (`QThread`)**: Todas las operaciones de I/O de impresión y apertura de cajón se despachan en un hilo secundario (`ESCPOSPrintWorker`).
5. **Resiliencia y Filosofía Offline-First**: Si la impresora está apagada, sin papel o inaccesible, el sistema no congela la caja ni aborta la venta; emite advertencias claras y registra el incidente en el log.

---

## 2. Especificación de Comandos ESC/POS Binarios

| Comando | Código Hexadecimal | Función |
| :--- | :--- | :--- |
| **Inicializar** | `\x1b\x40` (`ESC @`) | Limpia el buffer y restaura parámetros predeterminados. |
| **Alineación Izquierda** | `\x1b\x61\x00` (`ESC a 0`) | Justifica texto a la izquierda. |
| **Alineación Centro** | `\x1b\x61\x01` (`ESC a 1`) | Centra encabezados, logotipos y QR. |
| **Alineación Derecha** | `\x1b\x61\x02` (`ESC a 2`) | Alinea totales y montos. |
| **Negrita ON / OFF** | `\x1b\x45\x01` / `\x1b\x45\x00` | Activa/desactiva fuente en negrita. |
| **Doble Altura / Ancho** | `\x1d\x21\x11` / `\x1d\x21\x00` | Tamaño de fuente para encabezados y totales. |
| **Apertura de Cajón** | `\x1b\x70\x00\x19\xfa` (`ESC p 0 25 250`) | Pulso eléctrico al solenoide del cajón de dinero. |
| **Avance de Papel** | `\x1b\x64\x04` (`ESC d 4`) | Avanza 4 líneas de papel para despejar el cabezal. |
| **Corte Parcial** | `\x1d\x56\x42\x00` (`GS V 66 0`) | Corta el ticket dejando una pestaña de unión. |
| **Corte Total** | `\x1d\x56\x00` (`GS V 0`) | Corte completo de papel. |
| **QR Code Nativo** | `\x1d\x28\x6b...` (`GS ( k`) | Modelo QR 2 estándar ESC/POS para URLs de KuDE/SIFEN. |

---

## 3. Arquitectura del Módulo

1. **`utils/escpos_driver.py`**:
   - `ESCPOSCommandBuilder`: Constructor fluido de secuencias de bytes binarias.
   - `ESCPOSPrinterDriver`: Gestor de conexiones y despacho (Red, Windows RAW, Serial, Simulador).
   - `ESCPOSPrintWorker(QThread)`: Worker asíncrono para PyQt6.
2. **`ui/ticket_dialog.py`**:
   - Integración del botón de impresión rápida directa ESC/POS con feedback visual sin bloquear el hilo principal.
3. **`ui/payment_dialog.py`**:
   - Apertura automática opcional del cajón de dinero tras confirmar pagos con efectivo (`PYG`, `USD`, `BRL`, `ARS`).
