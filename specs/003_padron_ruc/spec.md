# SPEC-003: PADRÓN DNIT OFFLINE Y MOTOR DE BÚSQUEDA RÁPIDA DE CLIENTES POR RUC

**Estado:** Aprobado / Implementado  
**Versión:** 1.0.0  
**Fecha:** Octubre 2026

---

## 1. PROPÓSITO Y ALCANCE
Optimizar y acelerar la consulta del Padrón de Contribuyentes de la DNIT (Paraguay) y el registro local de clientes (`clients`), permitiendo autocompletado instantáneo (< 10 ms), cálculo offline de Dígito Verificador (Módulo 11), búsqueda difusa por aproximación fonética/sinónimos y soporte de importación masiva de padrones tributarios oficiales.

---

## 2. REQUERIMIENTOS FUNCIONALES

### RF-01: Validación y Normalización RUC / DV Módulo 11
- Cálculo determinista del Dígito Verificador según Resolución General 1530/05 (Módulo 11 base 11 con pesos 2..8/2..9).
- Detección automática de tipo de identificación:
  * RUC con guión (ej: `80001234-4`).
  * Cédula de Identidad numérica limpia (ej: `4455667` -> autocalcula DV `-1`).
  * RUC Extranjero / Pasaporte.

### RF-02: Búsqueda Reactiva Ultrarrápida (Filtro < 10ms)
- Búsqueda en tiempo real a medida que el cajero digita en `PaymentDialog` o `ClientSearchDialog`.
- Soporte para consultas por:
  1. RUC base o con DV.
  2. C.I. numérica sin puntos ni espacios.
  3. Razón Social o Nombre de Fantasía sin acentos (`unaccent`).
  4. Código interno de cliente de 6 dígitos.

### RF-03: Integración Padrón Offline -> Alta Automática de Cliente
- Si el RUC consultado existe en `TaxpayerRegistry` (`padron_ruc`) pero no como cliente frecuente (`clients`):
  * Al seleccionar o presionar Enter, se realiza el alta automática con código correlativo.
  * Se asigna la Razón Social oficial de la DNIT para garantizar validez fiscal en el ticket KuDE.

### RF-04: Herramienta de Carga Masiva de Padrones DNIT
- Utilidad CLI y de background para procesar archivos de padrón de texto plano oficial (`ruc0.txt` a `ruc9.txt`) a una velocidad de al menos 10.000 registros/segundo en SQLite.

---

## 3. REQUERIMIENTOS NO FUNCIONALES

### RNF-01: Eficiencia y Latencia
- Búsquedas sobre un padrón de > 100.000 contribuyentes deben responder en menos de 10ms sin bloquear el hilo principal de PyQt6.

### RNF-02: 100% Offline y Tolerancia Cero a Errores Fiscales
- La emisión de comprobantes fiscales jamás dependerá de la disponibilidad de internet o de servidores de la DNIT caídos.
