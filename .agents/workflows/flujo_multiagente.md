# FLUJO MULTIAGENTE - POS SUPERMERCADO TRIPLE FRONTERA

**Topología**: `Coordinador -> Planificador -> Implementador -> Revisor/Verificador`

```mermaid
flowchart TD
    User([Petición del Usuario]) --> Coord[🧑‍✈️ (A) Coordinador]
    
    subgraph Ciclo de Desarrollo Multiagente
        Coord -->|1. Transmite Contexto y Petición| Plan[📐 (S) Planificador]
        Plan -->|2. Retorna Spec, Plan y Tasks SDD| Coord
        
        Coord -->|3. Asigna Tareas Técnicas| Imp[💻 (S) Implementador]
        Imp -->|4. Escribe Código y Ejecuta Tests| Coord
        
        Coord -->|5. Solicita Auditoría Cruzada| Rev[🔍 (S) Revisor / Verificador]
        Rev -->|6. Evalúa contra Plan y Reglas| Decision{¿Pasa? SÍ / NO}
        
        Decision -->|❌ NO: Hallazgos y Correcciones| Coord
        Decision -->|✅ SÍ: Aprobado| Complete[📦 Entrega y Registro en MEMORY.md]
    end
    
    Complete --> Output([Respuesta Estructurada al Usuario])
```

---

## 1. Definición de Roles y Responsabilidades

### 🧑‍✈️ (A) Coordinador (Orquestador Principal)
- **Propósito**: Administrar las fases, custodiar la memoria del proyecto ([`MEMORY.md`](file:///c:/ENTORNO%20LOCAL/Control/MEMORY.md)), coordinar a los subagentes y unificar la comunicación con el usuario.
- **Responsabilidades**:
  1. Recibir la petición del usuario y determinar el alcance.
  2. Invocar al **Planificador** para estructurar la especificación (`spec.md`, `plan.md`, `tasks.md`).
  3. Despachar al **Implementador** con los requerimientos precisos.
  4. Enviar los cambios al **Revisor** para validación antes de dar por cerrada la fase.
  5. Mantener actualizado el archivo de tareas y la memoria operativa.

---

### 📐 (S) Planificador (Arquitecto SDD)
- **Propósito**: Analizar la petición a nivel de arquitectura, modelo de datos y reglas de negocio, diseñando la solución bajo la metodología *Spec-Driven Development*.
- **Responsabilidades**:
  1. Generar la especificación formal en `specs/XXX_nombre/`:
     - `spec.md`: Requerimientos funcionales, contratos de interfaz y diagramas.
     - `plan.md`: Desglose por fases de desarrollo.
     - `tasks.md`: Lista granular de tareas con checkboxes.
  2. Garantizar cumplimiento previo de las directivas de [`AGENTS.md`](file:///c:/ENTORNO%20LOCAL/Control/.agents/AGENTS.md):
     - Tipos monetarios 100% `decimal.Decimal` (0 `float`).
     - Rendimiento de UI (`QTableView` + `QAbstractTableModel`).
     - Filosofía Offline-First con `uuid`, `synced`, `synced_at`.
     - Fórmulas fiscales Paraguay (IVA 10%, IVA 5%, Exentas).

---

### 💻 (S) Implementador (Desarrollador & Tester)
- **Propósito**: Traducir el plan en código fuente ejecutable en Python 3.12+ / PyQt6 / SQLAlchemy y crear las pruebas automatizadas asociadas.
- **Responsabilidades**:
  1. Escribir/modificar los módulos correspondientes en `ui/`, `utils/`, `models.py` o `database.py`.
  2. Integrar el guardrail pre-transaccional [`POSGuardrail.validate_sale_item()`](file:///c:/ENTORNO%20LOCAL/Control/.agents/skills/validator/validator.py).
  3. Crear o actualizar la suite de tests en `tests/test_*.py`.
  4. Ejecutar `pytest` en el entorno virtual (`.\venv\Scripts\pytest.exe`) y confirmar que todas las pruebas pasen en verde.

---

### 🔍 (S) Revisor / Verificador (Auditor de Calidad y Reglas)
- **Propósito**: Realizar auditoría estricta e independiente del código implementado contra el plan original y las directivas de Triple Frontera.
- **Lista de Chequeo de Auditoría**:
  - [ ] ¿El código cumple con todos los objetivos definidos en `spec.md` y `tasks.md`?
  - [ ] ¿Existe algún uso indebido de `float` en montos o cantidades? (Debe ser `decimal.Decimal`).
  - [ ] ¿Las operaciones con hardware (impresora, balanza, pinpad) se ejecutan en `QThread`?
  - [ ] ¿Todos los tests de `pytest` pasaron con 100% de éxito?
  - [ ] ¿Se respetó el guardrail transaccional?
- **Veredicto**:
  - **¿Pasa? SÍ**: El Coordinador actualiza `tasks.md` y `MEMORY.md`, y entrega el resultado al usuario.
  - **¿Pasa? NO**: Retorna al Coordinador con el detalle de errores para que el Implementador aplique los ajustes necesarios.

---

## 2. Formato de Salida Obligatorio del Coordinador
Al finalizar el ciclo, la respuesta hacia el usuario debe estructurarse obligatoriamente en:
1. `[Implementación Técnica]`
2. `[Validación Frontera]`
3. `[Propuestas de Mejora Progresiva]`
4. `[Próximo Paso]`
