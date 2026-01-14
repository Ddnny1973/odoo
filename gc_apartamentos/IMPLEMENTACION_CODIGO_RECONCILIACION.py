# ==============================================================================
# IMPLEMENTACIÓN DE RECONCILIACIÓN AUTOMÁTICA EN GC_APARTAMENTOS
# ==============================================================================
# Este archivo contiene el código que debe agregarse a account_move.py
# para implementar la reconciliación automática de pagos e invoices
# ==============================================================================

import logging
from odoo import models, fields, api, Command
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ==============================================================================
# MÉTODOS A AGREGAR EN LA CLASE AccountMove (en gc_apartamentos/models/account_move.py)
# ==============================================================================

def _auto_reconcile_payment(self):
    """
    Busca facturas pendientes del mismo apartamento y cliente, y las reconcilia 
    automáticamente.
    
    Este método intenta reconciliar automáticamente el pago con las facturas 
    pendientes del mismo cliente y apartamento.
    
    Funciona de la siguiente manera:
    1. Obtiene las líneas de pago (líneas de cuenta por pagar/cobrar)
    2. Busca facturas pendientes del mismo cliente y apartamento
    3. Obtiene las líneas de factura no reconciliadas
    4. Ejecuta la reconciliación utilizando account.move.line.reconcile()
    """
    
    _logger.info(f"🔄 Iniciando reconciliación automática para factura {self.name}")
    
    # ========================================================================
    # VALIDACIONES PREVIAS
    # ========================================================================
    
    if not self.partner_id:
        _logger.debug(f"⚠️ Factura {self.name}: Sin cliente definido, abortando reconciliación")
        return False
    
    if not self.apartamento_id:
        _logger.debug(f"⚠️ Factura {self.name}: Sin apartamento definido, abortando reconciliación")
        return False
    
    # ========================================================================
    # PASO 1: OBTENER LÍNEAS DE PAGO/ENTRADA DE LA FACTURA ACTUAL
    # ========================================================================
    
    # Filtrar solo las líneas que corresponden a la cuenta por cobrar/pagar
    current_lines = self.line_ids.filtered(
        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
        and not l.reconciled  # Solo las no reconciliadas
    )
    
    if not current_lines:
        _logger.debug(
            f"⚠️ Factura {self.name}: No hay líneas de cuenta por cobrar/pagar sin reconciliar"
        )
        return False
    
    _logger.info(f"✅ Se encontraron {len(current_lines)} líneas de pago sin reconciliar")
    
    # ========================================================================
    # PASO 2: BUSCAR FACTURAS PENDIENTES DEL MISMO CLIENTE Y APARTAMENTO
    # ========================================================================
    
    # Buscar facturas salientes (facturas de cliente) que no estén pagadas
    # y del mismo cliente y apartamento
    pending_invoices = self.env['account.move'].search([
        ('move_type', 'in', ('out_invoice', 'out_refund')),  # Solo facturas salientes
        ('partner_id', '=', self.partner_id.id),             # Del mismo cliente
        ('apartment_id', '=', self.apartamento_id.id),       # Del mismo apartamento
        ('state', '=', 'posted'),                             # Solo confirmadas
        ('payment_state', '!=', 'paid'),                     # Que no estén pagadas
        ('id', '!=', self.id),                               # Diferentes a la actual
    ])
    
    if not pending_invoices:
        _logger.debug(
            f"⚠️ No hay facturas pendientes para cliente {self.partner_id.name} "
            f"en apartamento {self.apartamento_id.name}"
        )
        return False
    
    _logger.info(f"✅ Se encontraron {len(pending_invoices)} facturas pendientes")
    
    # ========================================================================
    # PASO 3: OBTENER LÍNEAS DE FACTURA NO RECONCILIADAS
    # ========================================================================
    
    # Obtener todas las líneas de cuentas por cobrar de las facturas pendientes
    # que aún no estén reconciliadas
    invoice_lines = pending_invoices.line_ids.filtered(
        lambda l: l.account_id.account_type == 'asset_receivable'
        and not l.reconciled  # Solo las no reconciliadas
    )
    
    if not invoice_lines:
        _logger.debug(f"⚠️ No hay líneas de factura pendientes sin reconciliar")
        return False
    
    _logger.info(f"✅ Se encontraron {len(invoice_lines)} líneas de factura sin reconciliar")
    
    # ========================================================================
    # PASO 4: EJECUTAR RECONCILIACIÓN
    # ========================================================================
    
    try:
        # Combinar las líneas de pago y factura
        lines_to_reconcile = current_lines + invoice_lines
        
        _logger.info(
            f"🔗 Reconciliando {len(current_lines)} líneas de pago con {len(invoice_lines)} "
            f"líneas de factura"
        )
        
        # FUNCIÓN CLAVE: reconcile() sin parámetros
        # Esta es la función que realiza toda la reconciliación
        lines_to_reconcile.reconcile()
        
        # ====================================================================
        # VALIDACIÓN POST-RECONCILIACIÓN
        # ====================================================================
        
        reconciled_count = sum(1 for line in lines_to_reconcile if line.reconciled)
        _logger.warning(
            f"✅ RECONCILIACIÓN EXITOSA - Líneas reconciliadas: {reconciled_count}/{len(lines_to_reconcile)}"
        )
        
        _logger.warning(
            f"✅ Reconciliación automática completada para apartamento {self.apartamento_id.name}, "
            f"cliente {self.partner_id.name}"
        )
        
        return True
        
    except Exception as e:
        _logger.error(
            f"❌ ERROR en reconciliación automática: {str(e)}\n"
            f"   Factura: {self.name}\n"
            f"   Cliente: {self.partner_id.name}\n"
            f"   Apartamento: {self.apartamento_id.name}",
            exc_info=True
        )
        return False


# ==============================================================================
# INTEGRACIÓN CON action_post()
# ==============================================================================
# 
# Modificar el método action_post() actual para incluir la reconciliación:
#
# def action_post(self):
#     """
#     Sobreescribir action_post para:
#     1. Marcar multas cuando la factura se confirma
#     2. Asignar partner_id a los apuntes contables
#     3. **NUEVO**: Ejecutar reconciliación automática si es un pago
#     """
#     # ... código existente ...
#     resultado = super().action_post()
#     
#     # FIX: Asignar partner_id a los apuntes de cuentas por cobrar/pagar
#     for move in self:
#         for line in move.line_ids:
#             if not line.partner_id and line.account_id.account_type in ('asset_receivable', 'liability_payable'):
#                 line.partner_id = move.partner_id
#     
#     # **NUEVO**: Marcar multas y reconciliar
#     self._marcar_multas_facturadas()
#     
#     # **NUEVO**: Intentar reconciliación automática
#     for move in self:
#         if move.move_type == 'out_invoice':
#             # Si es una factura saliente, intentar reconciliarla automáticamente
#             move._auto_reconcile_payment()
#     
#     return resultado


# ==============================================================================
# ALTERNATIVA: CREAR UN BOTÓN DE ACCIÓN MANUAL
# ==============================================================================
# 
# Si prefieres no hacerlo automático en action_post(), puedes crear un botón
# que el usuario pueda presionar manualmente:
#
# def action_auto_reconcile(self):
#     """
#     Acción manual para ejecutar la reconciliación automática.
#     """
#     for move in self:
#         move._auto_reconcile_payment()
#     
#     return {
#         'type': 'ir.actions.client',
#         'tag': 'reload',
#     }
#
# Y en el XML de la vista agregar:
#
# <button name="action_auto_reconcile" 
#         string="Reconciliar Automáticamente"
#         type="object" 
#         class="oe_highlight"
#         attrs="{'invisible': [('state', '!=', 'posted')]}" />


# ==============================================================================
# PARÁMETROS CLAVE DE account.move.line.reconcile()
# ==============================================================================
#
# La función reconcile() es un método que se ejecuta en un recordset de 
# account.move.line (líneas de movimiento).
#
# FIRMA:
#   def reconcile(self):
#       """ Reconcile the current move lines all together. """
#       return self._reconcile_plan([self])
#
# PARÁMETROS: NINGUNO (se aplica al recordset actual)
#
# RETORNO: Resultado de _reconcile_plan (normalmente None o dict)
#
# CONTEXTOS ÚTILES:
#   - with_context(no_exchange_difference=True): No crea asientos de diferencia de cambio
#   - with_context(no_cash_basis=True): No crea asientos de base de efectivo
#   - with_context(move_reverse_cancel=True): Para reversos
#


# ==============================================================================
# FLUJO INTERNO DE LA RECONCILIACIÓN
# ==============================================================================
#
# Cuando llamas a reconcile():
#
# 1. reconcile()
#    └─> _reconcile_plan([self])
#        └─> _reconcile_plan_with_sync(plan_list, all_amls)
#            └─> Prepara los datos de reconciliación
#            └─> Crea account.partial.reconcile (reconciliación parcial)
#            └─> Maneja diferencias de cambio
#            └─> Crea account.full.reconcile (reconciliación completa)
#            └─> Actualiza campos reconciled=True en las líneas
#            └─> Actualiza matching_number en las líneas
#


# ==============================================================================
# MODELOS UTILIZADOS
# ==============================================================================
#
# - account.move: Documento contable (factura, pago, etc)
# - account.move.line: Línea individual de un documento contable
# - account.partial.reconcile: Registro de reconciliación parcial
# - account.full.reconcile: Registro de reconciliación completa
# - account.account: Cuenta contable (debe tener reconcile=True)
#
# CAMPOS IMPORTANTES:
# - account.move.line.reconciled: Boolean (solo lectura, computed)
# - account.move.line.matching_number: Char (número de matching)
# - account.move.line.amount_residual: Monetary (monto pendiente por reconciliar)
# - account.move.line.full_reconcile_id: Many2one (referencia a full reconcile si aplica)
#


# ==============================================================================
# EJEMPLO DE USO EN CONSOLA ODOO
# ==============================================================================
#
# # Buscar líneas no reconciliadas de un cliente
# aml_ids = self.env['account.move.line'].search([
#     ('partner_id.name', '=', 'SOLEDAD CRISTINA GOMEZ'),
#     ('account_id.account_type', '=', 'asset_receivable'),
#     ('reconciled', '=', False),
#     ('parent_state', '=', 'posted'),
# ])
#
# print(f"Líneas encontradas: {len(aml_ids)}")
#
# # Ver detalles
# for line in aml_ids:
#     print(f"  - Factura: {line.move_id.name}")
#     print(f"    Monto residual: ${line.amount_residual}")
#     print(f"    Reconciliada: {line.reconciled}")
#
# # Ejecutar reconciliación
# if len(aml_ids) >= 2:
#     aml_ids.reconcile()
#     print("✅ Reconciliación realizada")
#
# # Verificar resultado
# for line in aml_ids:
#     print(f"  - {line.move_id.name}: Reconciliada={line.reconciled}")
#


# ==============================================================================
# DEBUGGING Y LOGS
# ==============================================================================
#
# El código incluye logs en varios niveles:
#
# - _logger.debug(): Info detallada (activar con DEBUG)
# - _logger.info(): Información general
# - _logger.warning(): Advertencias importantes (lo muestra el usuario)
# - _logger.error(): Errores con stack trace
#
# Ver logs en: Menú > Configuración > Logs del Servidor
#


# ==============================================================================
# VALIDACIONES Y MANEJO DE ERRORES
# ==============================================================================
#
# El método _auto_reconcile_payment() valida:
#
# 1. Que el cliente esté definido
# 2. Que el apartamento esté definido
# 3. Que haya líneas de pago sin reconciliar
# 4. Que existan facturas pendientes
# 5. Que existan líneas de factura sin reconciliar
# 6. Captura excepciones durante la reconciliación
#
# Si algo falla, retorna False y registra un error
#


# ==============================================================================
# CASOS DE USO
# ==============================================================================
#
# CASO 1: Pago Manual registrado
# ─────────────────────────────────
# 1. Usuario registra un pago en cuenta bancaria
# 2. Se crea un apunte contable en cuenta por pagar
# 3. Al registrar el apunte, se ejecuta action_post()
# 4. Se llama automáticamente _auto_reconcile_payment()
# 5. Se reconcilia automáticamente con facturas pendientes del cliente
# 6. El pago queda en estado "Paid" automáticamente
#
# CASO 2: Factura de cliente
# ──────────────────────────
# 1. Usuario crea una factura de cliente
# 2. Al registrar, se llama action_post()
# 3. Si no hay pagos, la factura queda pendiente
# 4. Si luego se registra un pago, este se reconcilia con la factura
#
# CASO 3: Múltiples facturas
# ───────────────────────────
# 1. Cliente tiene 3 facturas pendientes: $100, $200, $300
# 2. Se registra un pago de $600
# 3. La reconciliación automática reconcilia todas las facturas con el pago
# 4. Las 4 líneas quedan completamente reconciliadas
#


# ==============================================================================
# COMPARATIVA: MANUAL vs AUTOMÁTICO
# ==============================================================================
#
# MANUAL (Odoo Community sin este código):
# ├─ 1. Usuario registra el pago
# ├─ 2. Usuario va a Contabilidad > Apuntes Contables
# ├─ 3. Busca manualmente facturas y pagos del cliente
# ├─ 4. Selecciona múltiples registros
# ├─ 5. Hace clic en "Reconciliar"
# ├─ 6. Se abre diálogo de reconciliación
# ├─ 7. Valida y confirma
# └─ ✅ Reconciliación completa
#    Tiempo: ~5-10 minutos por cliente
#
# AUTOMÁTICO (con este código):
# ├─ 1. Usuario registra el pago
# └─ ✅ Reconciliación automática en 1-2 segundos
#    Tiempo: ~2 segundos por cliente
#
