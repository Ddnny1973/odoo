# 🔧 GUÍA TÉCNICA - Integración de Multas en Facturación

**Fecha:** 11 de enero de 2026  
**Módulo:** gc_apartamentos  
**Función:** Cargar automáticamente multas en facturas

---

## 📋 CONTEXTO ACTUAL

### Modelos Involucrados
```
gc.multas (YA EXISTE)
├─ num_apartamento_id → gc.apartamento
├─ fecha_multa → Date
└─ concepto_multa → product.product

gc.valores_conceptos (YA EXISTE)
├─ producto_id → product.product
├─ fecha_inicial/fecha_final → Date
├─ monto → Monetary
└─ usar_coeficiente → Boolean

account.move (EXTENDIDO)
├─ apartamento_id → gc.apartamento
├─ invoice_date → Date
└─ invoice_line_ids → [account.move.line]
```

### Lógica Requerida
**Cuando se crea una factura para un apartamento:**
1. ✓ Se agregan conceptos recurrentes (FUNCIONA)
2. ✗ Se deben agregar multas del período (FALTA)
3. ✗ Cada multa usa su valor desde `gc.valores_conceptos` (FALTA)

---

## 🔴 PROBLEMA ACTUAL: DUPLICACIÓN DE RECURRENTES

### ¿Por qué se duplican?

**Ubicación:** [account_move.py](models/account_move.py#L108-L125)

```python
@api.onchange('apartamento_id', 'invoice_date')
def _onchange_apartamento_o_fecha(self):
    # Esta función se ejecuta varias veces durante save():
    # 1. Cuando el usuario selecciona apartamento
    # 2. Cuando el usuario cambia fecha
    # 3. Al hacer save() (internamente)
    # 4. En validaciones post-save
```

**Problema específico:**
```python
# Línea 116 - Protección débil:
if any(line.price_unit > 0 for line in self.invoice_line_ids):
    return  # Solo si HAY líneas con precio > 0
```

**Escenario de error:**
1. Usuario selecciona apartamento → Se crean líneas (OK)
2. Usuario hace save → onchange se ejecuta de nuevo
3. Las líneas existen pero alguna tiene `price_unit = 0`
4. Condición `any(line.price_unit > 0)` puede ser falsa
5. Se regeneran líneas → DUPLICACIÓN

### ✅ SOLUCIÓN PROPUESTA

Reemplazar la lógica de protección por una más robusta:

```python
def _crear_lineas_conceptos(self):
    """
    Genera las líneas de factura basadas en conceptos recurrentes vigentes.
    CORREGIDO: Evita duplicación verificando estado de líneas.
    """
    if not self.apartamento_id or not self.invoice_date:
        return
    
    # ✅ NUEVA VERIFICACIÓN: Si hay líneas con cantidad > 0, asumimos ya creadas
    lineas_activas = [
        line for line in self.invoice_line_ids 
        if line.quantity > 0 and line.price_unit > 0
    ]
    
    if lineas_activas:
        # Ya tenemos líneas válidas, no regenerar
        return
    
    # Resto del código original...
    valores_conceptos = self.env['gc.valores_conceptos'].search([...])
    # ...
```

**Alternativa más conservadora - No limpiar automáticamente:**

```python
def _crear_lineas_conceptos(self):
    # Solo crear líneas si NO hay ninguna línea
    if self.invoice_line_ids:
        return  # Usuario debe editarlas manualmente si cambia apartamento
    
    # Crear líneas por primera vez
    # ...
```

---

## 🟢 IMPLEMENTACIÓN: Integración de Multas

### **PASO 1: Extender el modelo `gc.multas`** (Opcional)

Considerar agregar un campo para el período facturado:

```python
# En multas.py - OPCIONAL
fecha_multa = fields.Date(string='Fecha de Multa', required=True)
periodo_cobro = fields.Selection(  # OPCIONAL
    [('actual', 'Mes Actual'), ('siguiente', 'Mes Siguiente')],
    string='Período de Cobro',
    default='siguiente',
    help='¿En qué período se debe facturar?'
)
```

### **PASO 2: Determinar el Período de Factura**

¿Cómo sabemos qué período es cada factura?

**OPCIÓN A - Por mes/año de `invoice_date`:**
```python
from datetime import datetime, timedelta

def _obtener_periodo_factura(invoice_date):
    """Retorna inicio y fin del mes de la factura"""
    inicio = invoice_date.replace(day=1)
    siguiente_mes = inicio + timedelta(days=32)
    fin = siguiente_mes.replace(day=1) - timedelta(days=1)
    return inicio, fin
```

**OPCION B - Por rango fijo (ej: 1-31 de cada mes):**
```python
def _obtener_periodo_factura(invoice_date):
    """Período estándar: 1 a último día del mes"""
    inicio = invoice_date.replace(day=1)
    # Ir al siguiente mes y restar 1 día
    if invoice_date.month == 12:
        fin = date(invoice_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        fin = date(invoice_date.year, invoice_date.month + 1, 1) - timedelta(days=1)
    return inicio, fin
```

### **PASO 3: Código para integración de multas**

**Modificar método `_crear_lineas_conceptos()` en [account_move.py](models/account_move.py):**

```python
def _crear_lineas_conceptos(self):
    """
    Genera las líneas de factura basadas en:
    1. Conceptos recurrentes vigentes
    2. Multas del período
    """
    if not self.apartamento_id or not self.invoice_date:
        return
    
    # Protección contra duplicados
    lineas_activas = [
        line for line in self.invoice_line_ids 
        if line.quantity > 0 and line.price_unit > 0
    ]
    if lineas_activas:
        return
    
    # ===== 1. PROCESAR CONCEPTOS RECURRENTES =====
    valores_conceptos = self.env['gc.valores_conceptos'].search([
        ('recurrente', '=', True),
        ('activo', '=', True),
        ('fecha_inicial', '<=', self.invoice_date),
        '|',
        ('fecha_final', '=', False),
        ('fecha_final', '>=', self.invoice_date),
    ], order='fecha_inicial desc')
    
    productos_vigentes = {}
    for valor in valores_conceptos:
        producto_id = valor.producto_id.id
        if producto_id not in productos_vigentes:
            productos_vigentes[producto_id] = valor
    
    # ===== 2. PROCESAR MULTAS DEL PERÍODO =====
    productos_multas = {}
    
    # Determinar período de factura
    inicio_periodo, fin_periodo = self._obtener_periodo_factura(self.invoice_date)
    
    # Buscar multas en el período
    multas_periodo = self.env['gc.multas'].search([
        ('num_apartamento_id', '=', self.apartamento_id.id),
        ('fecha_multa', '>=', inicio_periodo),
        ('fecha_multa', '<=', fin_periodo),
    ])
    
    # Procesar cada multa
    for multa in multas_periodo:
        producto_multa = multa.concepto_multa
        
        # Buscar valor de la multa en gc.valores_conceptos
        valor_multa = self.env['gc.valores_conceptos'].search([
            ('producto_id', '=', producto_multa.id),
            ('activo', '=', True),
            ('fecha_inicial', '<=', multa.fecha_multa),
            '|',
            ('fecha_final', '=', False),
            ('fecha_final', '>=', multa.fecha_multa),
        ], limit=1, order='fecha_inicial desc')
        
        if valor_multa:
            # Usar monto de la multa sin coeficiente
            productos_multas[producto_multa.id] = {
                'producto': producto_multa,
                'monto': valor_multa.monto,
                'es_multa': True,
                'fecha_multa': multa.fecha_multa,
            }
    
    # ===== 3. PREPARAR LÍNEAS PARA CREAR =====
    comandos_lineas = [Command.clear()]
    coef = self.apartamento_id.coeficiente
    
    # Agregar líneas de conceptos recurrentes
    for valor in productos_vigentes.values():
        if valor.usar_coeficiente:
            precio_unit = valor.monto * coef
        else:
            precio_unit = valor.monto
        
        if precio_unit > 0:
            comandos_lineas.append(Command.create({
                'product_id': valor.producto_id.id,
                'quantity': 1.0,
                'price_unit': precio_unit,
                'coeficiente': coef if valor.usar_coeficiente else 0.0,
                'name': valor.producto_id.name,
            }))
    
    # Agregar líneas de multas (SIN coeficiente)
    for producto_id, info_multa in productos_multas.items():
        comandos_lineas.append(Command.create({
            'product_id': info_multa['producto'].id,
            'quantity': 1.0,
            'price_unit': info_multa['monto'],  # Precio fijo sin coeficiente
            'coeficiente': 0.0,  # Las multas NO usan coeficiente
            'name': f"Multa - {info_multa['producto'].name} ({info_multa['fecha_multa']})",
        }))
    
    # Aplicar solo si hay algo que crear
    if len(comandos_lineas) > 1:
        self.invoice_line_ids = comandos_lineas

def _obtener_periodo_factura(self, invoice_date):
    """
    Calcula el período de facturación (mes) para buscar multas.
    
    Retorna: (fecha_inicio, fecha_fin)
    """
    from datetime import date, timedelta
    
    # Inicio: primer día del mes
    inicio = invoice_date.replace(day=1)
    
    # Fin: último día del mes
    if invoice_date.month == 12:
        fin = date(invoice_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        siguiente_mes = date(invoice_date.year, invoice_date.month + 1, 1)
        fin = siguiente_mes - timedelta(days=1)
    
    return inicio, fin
```

---

## ⚙️ CONFIGURACIÓN NECESARIA EN gc.valores_conceptos

### Para que funcione correctamente:

**IMPORTANTE:** Cada multa debe tener una entrada en `gc.valores_conceptos`

**Ejemplo:**
```
Producto: "MULTA POR RUIDO"
Categoría: Conceptos Condominio > Multas y Sanciones
Valor en gc.valores_conceptos:
├─ fecha_inicial: 01/01/2026
├─ fecha_final: (vacío - indefinido)
├─ monto: 150000
├─ recurrente: FALSE ← Importante para que NO aparezca automáticamente
├─ activo: TRUE
└─ usar_coeficiente: FALSE ← Las multas NO usan coeficiente
```

---

## 🧪 CASOS DE PRUEBA

### Test Case 1: Factura sin multas
**Setup:**
- Apartamento: 101
- Período: Enero 2026
- Multas: Ninguna

**Resultado esperado:**
- Factura con solo conceptos recurrentes ✓

---

### Test Case 2: Factura con una multa
**Setup:**
- Apartamento: 101
- Período: Enero 2026
- Multa: 15-ene-2026, Ruido (valor $150.000)

**Resultado esperado:**
- Línea recurrente: Cuota Admon $500.000 × 0.05 = $25.000
- Línea multa: Multa Ruido $150.000 (sin coeficiente)
- Total: $175.000

---

### Test Case 3: Múltiples multas en el período
**Setup:**
- Apartamento: 101
- Período: Enero 2026
- Multas: 
  - 05-ene-2026, Ruido $150.000
  - 20-ene-2026, Pago Atrasado $200.000

**Resultado esperado:**
- Línea recurrente: Cuota Admon $25.000
- Línea multa 1: Multa Ruido $150.000
- Línea multa 2: Multa Pago Atrasado $200.000
- Total: $375.000

---

### Test Case 4: Evitar duplicación al guardar
**Setup:**
- Crea factura con apartamento
- Sistema agrega líneas automáticamente
- Usuario hace save

**Resultado esperado:**
- NO se duplican las líneas
- Factura se guarda correctamente

---

## 📝 VALIDACIONES RECOMENDADAS

Agregar en el método `_crear_lineas_conceptos()`:

```python
# Validación 1: Verificar que el apartamento existe y está activo
if not self.apartamento_id or not self.apartamento_id.active:
    return

# Validación 2: Verificar que hay productos configurados
if not productos_vigentes and not productos_multas:
    return  # No hay nada que cobrar, no crear líneas vacías

# Validación 3: Log de auditoria
_logger.info(
    f"Factura {self.name}: {len(productos_vigentes)} conceptos, "
    f"{len(productos_multas)} multas"
)
```

---

## 🔗 RELACIÓN ENTRE MODELOS

```
invoice (account.move)
    │
    ├─→ apartamento_id (gc.apartamento)
    │       │
    │       └─→ propietario_ids (res.partner)
    │
    └─→ invoice_line_ids (account.move.line)
            │
            └─→ product_id (product.product)
                    │
                    ├─→ Categoría: Conceptos Condominio/Multas y Sanciones
                    │
                    └─→ gc.valores_conceptos (búsqueda por producto + fecha)
                            │
                            ├─ monto
                            ├─ usar_coeficiente
                            └─ recurrente
```

---

## 📚 REFERENCIAS

- [account_move.py - Línea 126](models/account_move.py#L126)
- [multas.py](models/multas.py)
- [valores_conceptos.py](models/valores_conceptos.py)
- [Documentación Odoo API - Commands](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#odoo.fields.Command)

