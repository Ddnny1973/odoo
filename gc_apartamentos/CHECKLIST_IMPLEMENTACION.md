# ✅ CHECKLIST DE IMPLEMENTACIÓN

## 📋 Pre-Implementación: Análisis

- [x] Analizar la estructura de Odoo Community Edition
- [x] Localizar función de reconciliación: `account.move.line.reconcile()`
- [x] Entender parámetros que recibe: **NINGUNO** (se aplica al recordset)
- [x] Revisar flujo interno: `reconcile()` → `_reconcile_plan()` → `_reconcile_plan_with_sync()`
- [x] Documentar modelos involucrados: `account.partial.reconcile`, `account.full.reconcile`
- [x] Crear documentación completa

---

## 🔧 Implementación: Modificar Código

### Fase 1: Crear el Método (`account_move.py`)

- [ ] Abrir archivo: `gc_apartamentos/models/account_move.py`

- [ ] Copiar el método `_auto_reconcile_payment()` del archivo `IMPLEMENTACION_CODIGO_RECONCILIACION.py`

- [ ] Pegarlo en la clase `AccountMove` (después de `_marcar_multas_facturadas()`)

- [ ] Verificar imports necesarios:
  ```python
  import logging
  _logger = logging.getLogger(__name__)
  ```

- [ ] Verificar que no hay errores de sintaxis (Ctrl+Shift+P > "Python: Lint")

### Fase 2: Modificar `action_post()` (en `account_move.py`)

- [ ] Localizar el método `action_post()` (línea ~401)

- [ ] Agregar la llamada al nuevo método DESPUÉS de `_marcar_multas_facturadas()`:
  ```python
  # Intentar reconciliación automática
  for move in self:
      if move.move_type == 'out_invoice':
          move._auto_reconcile_payment()
  ```

- [ ] Guardar el archivo

- [ ] Verificar que el indentation es correcto

---

## 🧪 Testing: Validar Funcionamiento

### Test 1: Pago Único

- [ ] Crear cliente de prueba: "TEST-RECONCILE-01"
- [ ] Crear apartamento de prueba: "APT-TEST-01"
- [ ] Crear factura de cliente:
  - Cliente: TEST-RECONCILE-01
  - Apartamento: APT-TEST-01
  - Monto: $1000
  - Guardar y Confirmar
- [ ] Registrar un pago de $1000:
  - Del mismo cliente y apartamento
  - Guardar y Confirmar
- [ ] ✅ Verificar en logs que se ejecutó `_auto_reconcile_payment()`
- [ ] ✅ Verificar que ambas líneas tengan `reconciled = True`
- [ ] ✅ Verificar que ambas tienen el mismo `matching_number`

### Test 2: Múltiples Facturas

- [ ] Crear cliente: "TEST-RECONCILE-02"
- [ ] Crear apartamento: "APT-TEST-02"
- [ ] Crear 3 facturas:
  - Factura 1: $500
  - Factura 2: $300
  - Factura 3: $200
- [ ] Registrar un pago de $1000 (suma de todas)
- [ ] ✅ Verificar que las 4 líneas estén reconciliadas
- [ ] ✅ Verificar `matching_number` igual en todas

### Test 3: Pago Parcial

- [ ] Crear cliente: "TEST-RECONCILE-03"
- [ ] Crear factura: $1000
- [ ] Registrar pago: $600
- [ ] ✅ Verificar que se crea `account.partial.reconcile`
- [ ] ✅ Verificar que línea de pago tiene `reconciled = True`
- [ ] ✅ Verificar que línea de factura tiene `amount_residual = 400`

### Test 4: Diferentes Clientes (No debe reconciliar)

- [ ] Crear cliente A con factura de $1000
- [ ] Crear cliente B
- [ ] Registrar pago de cliente B por $1000
- [ ] ✅ Verificar que NO se reconcilia (clientes diferentes)
- [ ] ✅ Verificar logs que muestra advertencia

### Test 5: Diferentes Apartamentos (No debe reconciliar)

- [ ] Crear cliente: "TEST-RECONCILE-05"
- [ ] Crear apartamento A con factura de $1000
- [ ] Crear apartamento B
- [ ] Registrar pago en apartamento B por $1000
- [ ] ✅ Verificar que NO se reconcilia (apartamentos diferentes)

### Test 6: En Modo Draft (No debe reconciliar)

- [ ] Crear factura SIN confirmar
- [ ] Registrar pago y confirmar
- [ ] ✅ Verificar que no se reconcilia (factura en draft)

---

## 🔍 Verificación: Datos Esperados

### Después de Reconciliación Exitosa

Verificar en base de datos:

```sql
-- Línea 1 (Pago)
SELECT id, reconciled, matching_number, amount_residual 
FROM account_move_line 
WHERE id = 5001;
-- Esperado: TRUE, "123456", 0.00

-- Línea 2 (Factura)
SELECT id, reconciled, matching_number, amount_residual 
FROM account_move_line 
WHERE id = 5002;
-- Esperado: TRUE, "123456", 0.00

-- Debe existir partial.reconcile
SELECT id, debit_move_id, credit_move_id, amount 
FROM account_partial_reconcile 
WHERE id > 0;
-- Esperado: ID nuevo, 5001, 5002, 1000.00

-- Debe existir full.reconcile
SELECT id, partial_reconcile_ids, reconciled_line_ids 
FROM account_full_reconcile 
WHERE id > 0;
-- Esperado: ID nuevo, contiene partial.reconcile
```

---

## 📊 Monitoreo: Logs

### Dónde Ver Logs

1. Odoo UI: **Menú > Configuración > Logs del Servidor**
2. Terminal: Si está ejecutándose en consola
3. Archivo: `/var/log/odoo/odoo.log` (si está configurado)

### Qué Buscar

```
🔄 Iniciando reconciliación automática para factura INV/2026/00001
✅ Se encontraron 2 líneas de pago sin reconciliar
✅ Se encontraron 1 facturas pendientes
✅ Se encontraron 2 líneas de factura sin reconciliar
🔗 Reconciliando 2 líneas de pago con 2 líneas de factura
✅ RECONCILIACIÓN EXITOSA - Líneas reconciliadas: 4/4
✅ Reconciliación automática completada para apartamento APT-101
```

### En Caso de Error

```
⚠️ Factura INV/2026/00001: Sin cliente definido, abortando reconciliación
⚠️ Factura INV/2026/00001: Sin apartamento definido, abortando reconciliación
⚠️ No hay facturas pendientes para cliente...
⚠️ No hay líneas de factura pendientes sin reconciliar

❌ ERROR en reconciliación automática: [MENSAJE DE ERROR]
   Factura: INV/2026/00001
   Cliente: SOLEDAD CRISTINA GOMEZ
   Apartamento: APT-101
   [Stack trace completo]
```

---

## 🚀 Deployment: Puesta en Producción

### Pre-Deployment

- [ ] Hacer backup de la base de datos
- [ ] Hacer backup del código actual
- [ ] Probar en ambiente de desarrollo/testing

### Deployment

- [ ] Copiar archivo modificado a producción
- [ ] Reiniciar módulo gc_apartamentos:
  - Ir a Menú > Aplicaciones > Módulos Instalados
  - Buscar "gc_apartamentos"
  - Hacer clic en el módulo
  - Clic en "Upgrade" o "Reinstall"

### Post-Deployment

- [ ] Verificar que el módulo cargó sin errores
- [ ] Ejecutar test en producción con cliente real
- [ ] Validar logs
- [ ] Comunicar a usuarios
- [ ] Monitorear durante 24-48 horas

---

## 📞 Rollback Plan (En Caso de Problemas)

Si algo falla:

1. **Reverter cambios inmediatos**
   ```bash
   cd gc_apartamentos/models
   git checkout account_move.py  # Revierte a versión anterior
   ```

2. **Reiniciar módulo**
   - Menú > Aplicaciones > gc_apartamentos > Upgrade

3. **Verificar funcionalidad**
   - Probar crear/confirmar factura
   - Probar crear/confirmar pago
   - Verificar que sigue funcionando manualmente

4. **Contactar soporte** si necesario

---

## 📈 Monitoreo Post-Implementación

### Métricas a Monitorear

- [ ] % de pagos reconciliados automáticamente
- [ ] Errores en logs relacionados con reconciliación
- [ ] Tiempo promedio de reconciliación
- [ ] Usuarios reportando problemas

### Revisión Mensual

- [ ] Revisar logs de errores
- [ ] Validar integridad de reconciliaciones
- [ ] Evaluar si hay mejoras necesarias

### Dashboard Sugerido (crear después)

```
📊 RECONCILIACIÓN AUTOMÁTICA
├─ Pagos totales procesados (mes)
├─ % Reconciliados automáticamente
├─ % Reconciliados manualmente
├─ Errores encontrados
├─ Tiempo promedio por reconciliación
└─ Clientes problemáticos
```

---

## 🎓 Capacitación de Usuarios

### Cambios Visibles para el Usuario

- ✅ Los pagos ahora se reconcilian automáticamente
- ✅ Los pagos cambian a estado "Paid" inmediatamente
- ✅ Las facturas también cambian a "Paid" automáticamente
- ❌ No es necesario hacer reconciliación manual más

### Capacitación Necesaria

- [ ] Explicar que la reconciliación ahora es automática
- [ ] Mostrar que payment_state cambia a "Paid"
- [ ] Mostrar dónde ver los matching numbers
- [ ] Documentar si hay caso de excepción

### Documentación para Usuarios

Crear guía:
```
TÍTULO: "Reconciliación Automática de Pagos"

CONTENIDO:
1. ¿Qué cambió?
2. Flujo automático
3. Cómo verificar reconciliación
4. Qué hacer si no se reconcilia
5. Preguntas frecuentes
```

---

## 🔐 Seguridad y Validaciones

- [ ] Validar que solo usuarios con permisos pueden ver logs
- [ ] Validar que reconciliación respeta security rules
- [ ] Validar que no se reconcilian compañías diferentes
- [ ] Validar que no se reconcilian partners diferentes
- [ ] Auditar qué usuario creó la reconciliación

---

## 🎉 Tareas Finales

- [ ] Crear wiki interna documentando la implementación
- [ ] Actualizar runbooks de operaciones
- [ ] Comunicar feature a stakeholders
- [ ] Planificar próximas mejoras
- [ ] Recopilar feedback de usuarios

---

## 📊 Timeline Sugerido

```
FASE            DURACIÓN    ACTIVIDAD
─────────────────────────────────────────────────────────────
Desarrollo      2-4 horas   Implementar código
Testing         1-2 horas   Ejecutar tests
Capacitación    30 min      Preparar usuarios
Deployment      30 min      Cambios en producción
Monitoreo       2-3 días    Supervisar funcionamiento
```

---

## 📋 Firma de Aprobación (para tracking)

```
IMPLEMENTACIÓN DE RECONCILIACIÓN AUTOMÁTICA
Módulo: gc_apartamentos
Fecha de Inicio: _______________
Fecha de Finalización: _______________
Responsable: _______________
Revisado por: _______________
Aprobado por: _______________

Notas:
_____________________________________________________________
_____________________________________________________________
```

---

**Última actualización**: 14 de enero de 2026
**Versión**: 1.0
**Estado**: Listo para implementar
