# 📋 PLAN DE ACCIÓN - Facturación por Apartamento

**Fecha:** 8 de enero de 2026  
**Módulo:** gc_apartamentos  
**Versión Odoo:** Community 18

---

## 🔍 CONTEXTO ACTUAL

### Modelo Principal: `gc.apartamento`

**Campos clave identificados:**
- `numero_apartamento`: Integer (número único)
- `torre`: Integer
- `propietario_ids`: Many2many con `res.partner` (múltiples propietarios)
- `arrendatario_ids`: Many2many con `res.partner` (múltiples arrendatarios)
- `habitado_por`: Selection (propietario/arrendatario)
- `area_total`, `coeficiente`: Para cálculos
- `saldo_admon`: Campo monetario para control

**Modelos relacionados:**
- `gc.concepto`: Conceptos de cobro (admon, extra, multa)
- `gc.valores_conceptos`: Valores históricos de conceptos
- `gc.cobros_admon`: Registro de cobros realizados

---

## 🎯 OBJETIVO DE LA FASE 1

Extender el modelo de facturación estándar de Odoo (`account.move`) para:
1. ✅ Añadir un campo de selección de apartamento en las facturas de cliente
2. ✅ Autocompletar el cliente (propietario principal) al seleccionar el apartamento
3. ✅ Mostrar propietarios adicionales como información de referencia
4. ✅ Mantener compatibilidad con el flujo de facturación estándar de Odoo

---

## 📝 PLAN DE IMPLEMENTACIÓN - FASE 1

### **PASO 1: Extender el Modelo de Factura (`account.move`)**
**Archivo a crear:** `models/account_move.py`

**Acciones:**
- Heredar el modelo `account.move`
- Añadir campo `apartamento_id` (Many2one a `gc.apartamento`)
- Añadir campo `propietarios_adicionales_ids` (Many2many a `res.partner`, readonly)
- Crear método `onchange` para autocompletar cuando se selecciona apartamento:
  - Establecer `partner_id` con el primer propietario
  - Llenar `propietarios_adicionales_ids` con los propietarios restantes
- Añadir dominio para que solo aparezca en facturas de cliente (`move_type = 'out_invoice'`)

### **PASO 2: Actualizar Vistas de Factura**
**Archivo a crear:** `views/account_move_views.xml`

**Acciones:**
- Heredar la vista de formulario de factura estándar
- Añadir campo `apartamento_id` en la parte superior (después del cliente)
- Añadir campo `propietarios_adicionales_ids` como etiquetas (readonly)
- Organizar en un grupo para que sea visualmente claro
- Aplicar atributo `invisible` para ocultar en facturas que no sean de cliente

### **PASO 3: Permisos y Seguridad**
**Archivo a actualizar:** `security/ir.model.access.csv`

**Acciones:**
- Verificar permisos de acceso a `account.move`
- Asegurar que usuarios puedan leer apartamentos al crear facturas
- Validar permisos de usuarios vs administradores

### **PASO 4: Actualizar Manifiesto**
**Archivo a actualizar:** `__manifest__.py`

**Acciones:**
- Añadir dependencia del módulo `account`
- Registrar el nuevo archivo de modelo
- Registrar el nuevo archivo de vista
- Asegurar orden de carga correcto

### **PASO 5: Actualizar `__init__.py`**
**Archivo a actualizar:** `models/__init__.py`

**Acciones:**
- Importar el nuevo modelo `account_move`

---

## 🗂️ ESTRUCTURA DE ARCHIVOS A CREAR/MODIFICAR

```
gc_apartamentos/
├── models/
│   ├── __init__.py                 [MODIFICAR] ← Importar account_move
│   ├── account_move.py            [CREAR]     ← Extensión de factura
│   ├── apartamento.py              [EXISTENTE]
│   ├── conceptos.py                [EXISTENTE]
│   └── ...
├── views/
│   ├── account_move_views.xml     [CREAR]     ← Vista de factura extendida
│   ├── apartamento_views.xml       [EXISTENTE]
│   └── ...
├── security/
│   └── ir.model.access.csv        [REVISAR]   ← Verificar permisos
└── __manifest__.py                [MODIFICAR] ← Añadir depend. 'account'
```

---

## ⚙️ CONSIDERACIONES TÉCNICAS

### 1. Compatibilidad
- La solución debe ser no intrusiva con el flujo estándar de Odoo
- Campos opcionales (no requeridos) para no romper facturas existentes
- Solo visible en facturas de cliente (`out_invoice`)

### 2. Lógica de Propietarios
- Si hay múltiples propietarios, tomar el primero como cliente principal
- Los demás irán a propietarios adicionales (solo informativo)
- Validación: Si el apartamento no tiene propietarios, mostrar warning

### 3. Futuras Fases (Referencias para planificación)
- **Fase 2:** Integración con conceptos de cobro
- **Fase 3:** Generación automática de facturas por período
- **Fase 4:** Aplicación de coeficientes y áreas
- **Fase 5:** Reportes y análisis por apartamento

---

## ✅ CRITERIOS DE ÉXITO - FASE 1

- [ ] Campo apartamento visible y funcional en facturas de cliente
- [ ] Al seleccionar apartamento, se autocompleta el cliente (propietario)
- [ ] Propietarios adicionales se muestran como información
- [ ] No afecta el flujo normal de facturación sin apartamento
- [ ] Módulo instala sin errores
- [ ] Permisos correctamente configurados

---

## 📊 ESTADO DE IMPLEMENTACIÓN

### Fase 1: Facturación Básica por Apartamento
- [ ] Paso 1: Modelo `account_move` extendido
- [ ] Paso 2: Vistas de factura actualizadas
- [ ] Paso 3: Permisos y seguridad
- [ ] Paso 4: Manifiesto actualizado
- [ ] Paso 5: Init actualizado
- [ ] Paso 6: Pruebas funcionales

---

## 📝 NOTAS DE DESARROLLO

### Cambios Realizados
_(Se irá actualizando conforme avance la implementación)_

**Fecha:** ___________
- [ ] Cambio 1
- [ ] Cambio 2

---

## 🔄 PRÓXIMAS FASES

### Fase 2: Integración con Conceptos de Cobro
- Vincular líneas de factura con `gc.concepto`
- Aplicar valores automáticos desde `gc.valores_conceptos`
- Generar cobros en `gc.cobros_admon`

### Fase 3: Generación Automática
- Wizard para generar facturas masivas
- Aplicación de conceptos recurrentes
- Filtros por torre, fecha, tipo

### Fase 4: Coeficientes y Distribución
- Aplicar coeficientes para gastos comunes
- Distribución proporcional por área
- Cálculos automáticos

### Fase 5: Reportes y Analytics
- Reporte de facturación por apartamento
- Estado de cuenta por apartamento
- Dashboard de administración
