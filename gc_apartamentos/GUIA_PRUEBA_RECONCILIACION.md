# 🧪 GUÍA DE PRUEBA - RECONCILIACIÓN AUTOMÁTICA

## 📋 Resumen de Escenarios

Esta guía contiene 5 escenarios de prueba para validar que la reconciliación automática funciona correctamente.

---

## 🎬 ESCENARIO 1: Pago que reconcilia 1 factura

### Objetivo
Validar que un pago reconcilia automáticamente con 1 factura pendiente.

### Pasos

**PASO 1: Crear Factura**
```
1. Ir a: Contabilidad > Clientes > Facturas
2. Botón "Crear"
3. Rellenar:
   ├─ Cliente: JUAN PEREZ (o cualquier cliente)
   ├─ Línea 1:
   │  ├─ Producto: [cualquier producto]
   │  └─ Cantidad: 1
   │  └─ Precio unitario: $1000
   └─ Confirmar
4. Resultado esperado: 
   ├─ Estado: "Posted"
   └─ payment_state: "not_paid"
```

**PASO 2: Crear Pago**
```
1. Ir a: Contabilidad > Clientes > Pagos
2. Botón "Crear"
3. Rellenar:
   ├─ Tipo: Inbound (Recibido)
   ├─ Partiendo de: [dejar vacío]
   ├─ Empresa: [seleccionar correcta]
   ├─ Transferencia Bancaria
   │  ├─ Tipo de diario: Bank
   │  ├─ Cuenta bancaria: [seleccionar]
   │  └─ Cuenta de contrapartida: [debería ser cuentas por cobrar]
   ├─ Compañía de moneda: USD (o la que uses)
   ├─ Fecha: [hoy]
   ├─ Socio: JUAN PEREZ (MISMO DEL PASO 1)
   ├─ Importe: $1000 (MISMO DE LA FACTURA)
   └─ Guardar
```

**PASO 3: Confirmar Pago**
```
1. Botón "Confirmar"
2. Se ejecuta action_post()
   ├─ Crea movimiento contable
   ├─ Estado cambia a "paid"
   └─ 🆕 SE EJECUTA RECONCILIACIÓN AUTOMÁTICA ←
```

### Verificación

**Esperado en Logs** (Menú > Configuración > Logs del Servidor):
```
🔄 Iniciando reconciliación automática para pago PAY/2026/00001
✅ Se encontraron 1 líneas de pago sin reconciliar
✅ Se encontraron 1 facturas pendientes
✅ Se encontraron 1 líneas de factura sin reconciliar
🔗 Reconciliando 1 líneas de pago con 1 líneas de factura
✅ RECONCILIACIÓN EXITOSA - Líneas reconciliadas: 2/2
✅ Reconciliación automática completada para cliente JUAN PEREZ
```

**Verificar en Interfaz**:
1. Volver a factura (del PASO 1)
   ├─ payment_state debe ser "paid" ✅
   └─ Debería haber un "matching_number" asignado ✅

2. Volver a pago (del PASO 2)
   ├─ Estado debe ser "paid" ✅
   └─ Debería haber un "matching_number" asignado ✅

---

## 🎬 ESCENARIO 2: Pago que reconcilia 3 facturas

### Objetivo
Validar que un pago puede reconciliar automáticamente con múltiples facturas.

### Pasos

**PASO 1: Crear 3 Facturas**
```
Factura 1:
├─ Cliente: JUAN PEREZ
├─ Monto: $300
└─ Confirmar

Factura 2:
├─ Cliente: JUAN PEREZ
├─ Monto: $400
└─ Confirmar

Factura 3:
├─ Cliente: JUAN PEREZ
├─ Monto: $300
└─ Confirmar

Verificar: Todas en state="Posted", payment_state="not_paid"
```

**PASO 2: Crear Pago por $1000**
```
1. Crear pago (igual a ESCENARIO 1)
2. Cliente: JUAN PEREZ
3. Importe: $1000 (suma de las 3 facturas)
4. Confirmar
```

### Verificación

**Esperado en Logs**:
```
✅ Se encontraron 3 facturas pendientes
✅ Se encontraron 3 líneas de factura sin reconciliar
🔗 Reconciliando 1 líneas de pago con 3 líneas de factura
✅ RECONCILIACIÓN EXITOSA - Líneas reconciliadas: 4/4
```

**Verificar en Interfaz**:
1. Todas las 3 facturas:
   ├─ payment_state = "paid" ✅
   └─ matching_number = (mismo valor) ✅

---

## 🎬 ESCENARIO 3: Pago parcial

### Objetivo
Validar que un pago PARCIAL crea una reconciliación parcial (partial.reconcile).

### Pasos

**PASO 1: Crear Factura por $1000**
```
Cliente: JUAN PEREZ
Monto: $1000
Confirmar
```

**PASO 2: Crear Pago por $600**
```
1. Crear pago
2. Cliente: JUAN PEREZ
3. Importe: $600 (MENOR a $1000)
4. Confirmar
```

### Verificación

**Esperado en Logs**:
```
✅ Se encontraron 1 facturas pendientes
✅ Se encontraron 1 líneas de factura sin reconciliar
🔗 Reconciliando 1 líneas de pago con 1 líneas de factura
✅ RECONCILIACIÓN EXITOSA - Líneas reconciliadas: 2/2
```

**Verificar en Interfaz**:
1. Factura:
   ├─ payment_state = "partial" (no "paid")
   ├─ amount_residual = $400 ✅
   └─ matching_number = (asignado) ✅

2. Pago:
   ├─ Estado = "paid" ✅
   └─ Totalmente reconciliado ✅

---

## 🎬 ESCENARIO 4: Pago sin facturas pendientes

### Objetivo
Validar que la reconciliación maneja gracefully el caso sin facturas pendientes.

### Pasos

**PASO 1: Crear Pago sin Facturas**
```
1. Cliente: NUEVO_CLIENTE (sin facturas)
2. Importe: $500
3. Confirmar
```

### Verificación

**Esperado en Logs**:
```
🔄 Iniciando reconciliación automática para pago PAY/2026/00002
⚠️ No hay facturas pendientes para cliente NUEVO_CLIENTE
```

**Verificar en Interfaz**:
1. Pago se confirma normalmente ✅
2. Estado = "paid" ✅
3. No hay errores, solo warning en logs ✅

---

## 🎬 ESCENARIO 5: Error en reconciliación (simulado)

### Objetivo
Validar que si falla la reconciliación, el pago igual se confirma.

### Pasos

**PASO 1: Crear situación anormal**
```
(Este escenario es para validar la robustez del error handling)
Puede ocurrir en casos como:
├─ Problemas con las cuentas configuradas
├─ Diferencias de cambio múltiples
└─ Movimientos bloqueados/archivados
```

**PASO 2: Si ocurre error**
```
El pago se debe confirmar igual
```

### Verificación

**Esperado en Logs** (en caso de error):
```
🔄 Iniciando reconciliación automática para pago PAY/2026/00003
❌ ERROR en reconciliación automática: [descripción del error]
⚠️ El pago PAY/2026/00003 se confirmó, pero la reconciliación 
   automática falló. Deberá reconciliarse manualmente.
```

**Verificar en Interfaz**:
1. Pago tiene estado = "paid" ✅ (no está bloqueado por error)
2. Debe reconciliarse manualmente después

---

## 📊 Matriz de Pruebas

| Escenario | Cliente | # Facturas | Monto Pago | Resultado | Estado Log |
|-----------|---------|-----------|-----------|-----------|-----------|
| 1 | JUAN | 1 | $1000 | Reconcilia 1 | ✅ SUCCESS |
| 2 | JUAN | 3 | $1000 | Reconcilia 3 | ✅ SUCCESS |
| 3 | JUAN | 1 | $600 | Partial | ✅ PARTIAL |
| 4 | NUEVO | 0 | $500 | No reconcilia | ⚠️ INFO |
| 5 | * | * | * | Falla limpia | ❌ ERROR |

---

## 🔍 Cómo Revisar los Logs

### En Odoo UI
```
1. Menú > Configuración > Técnico > Logs del Servidor
2. Aparece una lista de logs del sistema
3. Buscar por:
   ├─ Nombre del pago (ej: PAY/2026/00001)
   ├─ Nombre del cliente (ej: JUAN PEREZ)
   └─ Palabra clave (ej: "reconciliación")
4. Hacer clic en el log para ver detalles completos
```

### En Terminal
```
# Ver últimos 100 logs
tail -100 /var/log/odoo/odoo.log | grep -i "reconciliación"

# Ver logs en tiempo real
tail -f /var/log/odoo/odoo.log | grep -i "reconciliación"
```

---

## ✅ Checklist de Validación

- [ ] Escenario 1: Pago $1000 reconcilia con factura $1000
- [ ] Escenario 2: Pago $1000 reconcilia con 3 facturas ($300+$400+$300)
- [ ] Escenario 3: Pago $600 crea partial.reconcile con factura $1000
- [ ] Escenario 4: Pago sin facturas no genera error
- [ ] Escenario 5: Error en reconciliación no bloquea el pago
- [ ] Logs muestran mensajes ✅ correctos
- [ ] Matching numbers son consistentes
- [ ] Estados de pago (payment_state) son correctos
- [ ] No hay excepciones no manejadas
- [ ] El pago siempre se confirma exitosamente

---

## 🐛 Problemas Comunes y Soluciones

### Problema: "No hay facturas pendientes" pero sí hay

**Causas posibles:**
```
1. La factura está en estado != 'posted'
   └─ Solución: Confirmar la factura antes
   
2. La factura ya está pagada (payment_state='paid')
   └─ Solución: Crear nueva factura sin pagos
   
3. El cliente es diferente
   └─ Solución: Verificar que el pago y factura tienen mismo cliente
```

### Problema: Error en reconciliación

**Causas posibles:**
```
1. Cuenta por cobrar no configurada correctamente
   └─ Solución: Revisar configuración de empresa
   
2. Diferencias de cambio
   └─ Solución: Usar misma moneda en pago y factura
   
3. Líneas archivadas
   └─ Solución: Revisar que todas las líneas estén activas
```

### Problema: matching_number diferente

**Esto NO es un error:**
```
Si la reconciliación es PARCIAL, cada partial.reconcile crea su
propio matching_number. Es el comportamiento esperado de Odoo.
```

---

## 📈 Métricas Esperadas

Después de las pruebas, deberías ver:

```
✅ 5 pagos confirmados
✅ 5+ facturas reconciliadas
✅ 0 errores no manejados
✅ 100% de logs con información útil
✅ 0 pagos bloqueados por error
```

---

**Última actualización**: 14 de enero de 2026  
**Estado**: Listo para prueba  
**Escenarios**: 5 completos
