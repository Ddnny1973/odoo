# Implementación de Reconciliación Automática en GC Apartamentos

## 📋 Análisis Realizado

### Ubicación de la Función de Reconciliación en Odoo

Después de investigar en los modelos de Odoo ubicados en la carpeta `addons/` del proyecto, encontramos que:

#### **Función Principal: `account.move.line.reconcile()`**
- **Ubicación**: [gc_apartamentos/addons/account_move_line.py#L3108](account_move_line.py#L3108)
- **Funcionamiento**: Esta es la función que se ejecuta cuando presionas el botón "Reconcile" en Odoo
- **Firma**: `def reconcile(self):`

#### **Cómo Funciona Internamente**

```python
# En account_move_line.py (línea 3108-3110)
def reconcile(self):
    """ Reconcile the current move lines all together. """
    return self._reconcile_plan([self])
```

#### **Proceso de Reconciliación (Flujo Completo)**

1. **`reconcile()`** → Invoca `_reconcile_plan([self])`
   
2. **`_reconcile_plan(reconciliation_plan)`** (línea 2499-2520)
   - Recibe un plan de reconciliación como lista
   - Optimiza el plan de reconciliación
   - Sincroniza las líneas de movimiento dinámicas
   
3. **`_reconcile_plan_with_sync(plan_list, all_amls)`** (línea 2523)
   - Prepara los datos de reconciliación
   - Crea los `account.partial.reconcile` (reconciliación parcial)
   - Maneja diferencias de cambio
   - Crea las reconciliaciones completas `account.full.reconcile`

#### **Parámetros Clave**

```python
# La función reconcile() NO recibe parámetros
# Simplemente reconcilia todas las líneas del conjunto (recordset) actual

# Uso típico:
aml_ids = self.env['account.move.line'].search([
    ('account_id', '=', account_id),
    ('partner_id', '=', partner_id),
    ('reconciled', '=', False),  # Solo las no reconciliadas
])
aml_ids.reconcile()  # ✅ Esto es todo lo necesario
```

---

## 🔧 Implementación Recomendada para GC Apartamentos

### **Opción 1: Reconciliación Automática al Registrar el Pago** (Recomendado)

Modificar el método `action_post()` en [gc_apartamentos/models/account_move.py](gc_apartamentos/models/account_move.py)

```python
def action_post(self):
    """
    Registra la factura y, si es un pago, intenta reconciliarlo automáticamente
    con facturas pendientes del mismo cliente/apartamento.
    """
    result = super().action_post()
    
    # Si es un pago de cliente (inbound payment)
    if self.move_type == 'in_refund' or self.payment_state == 'paid':
        self._auto_reconcile_payment()
    
    return result

def _auto_reconcile_payment(self):
    """
    Busca facturas pendientes del mismo cliente y las reconcilia automáticamente.
    """
    if not self.partner_id or not self.apartment_id:
        return
    
    # 1. Obtener todas las líneas de pago de esta factura
    payment_lines = self.line_ids.filtered(
        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
    )
    
    if not payment_lines:
        return
    
    # 2. Buscar facturas pendientes del mismo cliente
    pending_invoices = self.env['account.move'].search([
        ('move_type', 'in', ('out_invoice', 'out_refund')),
        ('partner_id', '=', self.partner_id.id),
        ('state', '=', 'posted'),
        ('payment_state', '!=', 'paid'),
        ('id', '!=', self.id),
        ('apartment_id', '=', self.apartment_id.id),
    ])
    
    if not pending_invoices:
        return
    
    # 3. Obtener líneas de cuenta por cobrar no reconciliadas
    invoice_lines = pending_invoices.line_ids.filtered(
        lambda l: l.account_id.account_type == 'asset_receivable'
        and not l.reconciled
    )
    
    # 4. Reconciliar automáticamente
    if payment_lines and invoice_lines:
        try:
            # Esta es la función clave: reconcile() sin parámetros
            (payment_lines + invoice_lines).reconcile()
            
            _logger.info(
                f"✅ Reconciliación automática realizada para apartamento {self.apartment_id.name}, "
                f"cliente {self.partner_id.name}"
            )
        except Exception as e:
            _logger.warning(
                f"⚠️ No fue posible reconciliar automáticamente: {str(e)}"
            )
```

### **Opción 2: Reconciliación Manual Mejorada (Alternativa)**

Crear un botón adicional que permita reconciliar de forma mejorada:

```python
def action_auto_reconcile(self):
    """
    Acción manual para reconciliar pagos e invoices pendientes.
    """
    self._auto_reconcile_payment()
    
    return {
        'type': 'ir.actions.client',
        'tag': 'reload',
    }
```

---

## 📊 Flujo de Funciones Relevantes

```
Usuario registra pago (action_post)
        ↓
    ↓→ _auto_reconcile_payment() ← [NUESTRO MÉTODO]
        ↓
    Busca líneas no reconciliadas
        ↓
    Ejecuta: (payment_lines + invoice_lines).reconcile()
        ↓
    ↓→ reconcile() [account_move_line.py:3108]
        ↓
    ↓→ _reconcile_plan([self])
        ↓
    ↓→ _reconcile_plan_with_sync(plan_list, all_amls)
        ↓
    Crea account.partial.reconcile
        ↓
    Crea account.full.reconcile
        ↓
    ✅ Estado de líneas cambia a "reconciled"
```

---

## 🎯 Parámetros y Métodos Clave

### **1. `reconcile()` - Sin parámetros**
```python
# Forma correcta
aml_lines.reconcile()

# NO recibe parámetros adicionales
# El contexto se puede pasar así:
aml_lines.with_context(no_exchange_difference=True).reconcile()
```

### **2. Contextos Útiles**
```python
# Para evitar crear líneas de diferencia de cambio
with_context(no_exchange_difference=True)

# Para no crear asientos de base de efectivo
with_context(no_cash_basis=True)

# Útil para importaciones
with_context(no_exchange_difference=True, no_cash_basis=True)
```

### **3. Modelos Utilizados en la Reconciliación**
- **`account.move.line`**: Líneas de movimiento (facturas/pagos)
- **`account.partial.reconcile`**: Reconciliaciones parciales
- **`account.full.reconcile`**: Reconciliaciones completas
- **`account.account`**: Las cuentas deben tener `reconcile=True`

---

## ⚠️ Consideraciones Importantes

1. **Cuentas Reconciliables**: La cuenta debe tener `reconcile=True`
   ```python
   # Verificar
   account_receivable.reconcile  # Debe ser True
   ```

2. **Estados de las Líneas**
   - Solo se pueden reconciliar líneas con `parent_state='posted'`
   - Las líneas deben ser del mismo partner
   - Las líneas deben estar en cuentas reconciliables

3. **Validaciones Automáticas**
   ```python
   # El sistema automáticamente:
   # - Valida que los montos sean iguales
   # - Maneja diferencias de cambio
   # - Marca líneas como reconciliadas
   # - Actualiza el campo 'matching_number'
   ```

4. **Moneda Multiple**
   - Si hay múltiples monedas, se crean asientos de diferencia de cambio
   - Usa `no_exchange_difference=True` en contexto si no quieres esto

---

## 📝 Checklist de Implementación

- [ ] Ubicar el método `action_post()` en gc_apartamentos/models/account_move.py
- [ ] Agregar el método `_auto_reconcile_payment()`
- [ ] Agregar lógica de búsqueda de facturas pendientes
- [ ] Llamar a `reconcile()` en el conjunto de líneas
- [ ] Agregar manejo de errores con try/except
- [ ] Agregar logging para debugging
- [ ] Probar con pagos de clientes
- [ ] Validar que las líneas queden reconciliadas
- [ ] Verificar campos `reconciled` y `matching_number` se actualicen

---

## 🧪 Código de Prueba (para validar)

```python
# En la consola de Odoo o en un script de prueba:
# Buscar líneas no reconciliadas de un cliente
aml_ids = self.env['account.move.line'].search([
    ('partner_id.name', '=', 'SOLEDAD CRISTINA GOMEZ'),
    ('account_id.account_type', '=', 'asset_receivable'),
    ('reconciled', '=', False),
])

print(f"Líneas encontradas: {len(aml_ids)}")
for line in aml_ids:
    print(f"  - {line.move_id.name}: ${line.amount_residual} (Reconciliada: {line.reconciled})")

# Ejecutar reconciliación
if len(aml_ids) >= 2:
    aml_ids.reconcile()
    print("✅ Reconciliación realizada")
    
    # Verificar
    for line in aml_ids:
        print(f"  - {line.move_id.name}: Reconciliada={line.reconciled}")
```

---

## 📚 Referencias

- **Ubicación del código**: `gc_apartamentos/addons/account_move_line.py` (línea 3108)
- **Proceso**: `_reconcile_plan()` → `_reconcile_plan_with_sync()` → Crea registros en `account.partial.reconcile` y `account.full.reconcile`
- **Documentación Odoo**: Modelo `account.move.line` - método `reconcile()`
