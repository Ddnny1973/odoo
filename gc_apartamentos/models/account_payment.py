import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """
    Extensión del modelo account.payment para agregar reconciliación automática.
    
    Cuando se registra un pago, busca automáticamente facturas pendientes del mismo cliente
    y las reconcilia automáticamente con el pago.
    """
    _inherit = 'account.payment'

    def _auto_reconcile_payment(self):
        """
        Busca facturas pendientes del cliente y las reconcilia automáticamente con este pago.
        
        Esta función se ejecuta cuando se registra un pago (en action_post).
        Realiza los siguientes pasos:
        1. Obtiene las líneas de pago (líneas de cuenta por pagar/cobrar)
        2. Busca facturas pendientes del mismo cliente
        3. Obtiene las líneas de factura no reconciliadas
        4. Ejecuta la reconciliación utilizando account.move.line.reconcile()
        
        :return: True si la reconciliación fue exitosa, False en caso contrario
        """
        
        _logger.info(f"🔄 Iniciando reconciliación automática para pago {self.name}")
        
        # ====================================================================
        # VALIDACIONES PREVIAS
        # ====================================================================
        
        if not self.partner_id:
            _logger.debug(
                f"⚠️ Pago {self.name}: Sin cliente definido, abortando reconciliación"
            )
            return False
        
        if not self.move_id:
            _logger.debug(
                f"⚠️ Pago {self.name}: Sin movimiento contable asociado"
            )
            return False
        
        # ====================================================================
        # PASO 1: OBTENER LÍNEAS DE PAGO DEL MOVIMIENTO CREADO
        # ====================================================================
        
        # Filtrar solo las líneas que corresponden a la cuenta por cobrar/pagar
        # y que no estén reconciliadas
        current_lines = self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            and not l.reconciled
        )
        
        if not current_lines:
            _logger.debug(
                f"⚠️ Pago {self.name}: No hay líneas de cuenta por cobrar/pagar sin reconciliar"
            )
            return False
        
        _logger.info(
            f"✅ Se encontraron {len(current_lines)} líneas de pago sin reconciliar"
        )
        
        # ====================================================================
        # PASO 2: BUSCAR FACTURAS PENDIENTES DEL MISMO CLIENTE
        # ====================================================================
        
        # Buscar facturas salientes (facturas de cliente) que no estén pagadas
        # del mismo cliente
        pending_invoices = self.env['account.move'].search([
            ('move_type', 'in', ('out_invoice', 'out_refund')),  # Solo facturas salientes
            ('partner_id', '=', self.partner_id.id),             # Del mismo cliente
            ('state', '=', 'posted'),                             # Solo confirmadas
            ('payment_state', '!=', 'paid'),                     # Que no estén pagadas
            ('id', '!=', self.move_id.id),                       # Diferentes al movimiento del pago
        ])
        
        if not pending_invoices:
            _logger.debug(
                f"⚠️ No hay facturas pendientes para cliente {self.partner_id.name}"
            )
            return False
        
        _logger.info(
            f"✅ Se encontraron {len(pending_invoices)} facturas pendientes"
        )
        
        # ====================================================================
        # PASO 3: OBTENER LÍNEAS DE FACTURA NO RECONCILIADAS
        # ====================================================================
        
        # Obtener todas las líneas de cuentas por cobrar de las facturas pendientes
        # que aún no estén reconciliadas
        invoice_lines = pending_invoices.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
            and not l.reconciled
        )
        
        if not invoice_lines:
            _logger.debug(
                f"⚠️ No hay líneas de factura pendientes sin reconciliar"
            )
            return False
        
        _logger.info(
            f"✅ Se encontraron {len(invoice_lines)} líneas de factura sin reconciliar"
        )
        
        # ====================================================================
        # PASO 4: EJECUTAR RECONCILIACIÓN
        # ====================================================================
        
        try:
            # Combinar las líneas de pago y factura
            lines_to_reconcile = current_lines + invoice_lines
            
            _logger.info(
                f"🔗 Reconciliando {len(current_lines)} líneas de pago con "
                f"{len(invoice_lines)} líneas de factura"
            )
            
            # 🎯 FUNCIÓN CLAVE: reconcile() sin parámetros
            # Esta es la función de Odoo que realiza toda la reconciliación
            lines_to_reconcile.reconcile()
            
            # ================================================================
            # VALIDACIÓN POST-RECONCILIACIÓN
            # ================================================================
            
            reconciled_count = sum(1 for line in lines_to_reconcile if line.reconciled)
            _logger.warning(
                f"✅ RECONCILIACIÓN EXITOSA - Líneas reconciliadas: "
                f"{reconciled_count}/{len(lines_to_reconcile)}"
            )
            
            _logger.warning(
                f"✅ Reconciliación automática completada para cliente {self.partner_id.name}"
            )
            
            return True
            
        except Exception as e:
            _logger.error(
                f"❌ ERROR en reconciliación automática: {str(e)}\n"
                f"   Pago: {self.name}\n"
                f"   Cliente: {self.partner_id.name}",
                exc_info=True
            )
            return False

    def action_post(self):
        """
        Registra el pago e intenta reconciliarlo automáticamente con facturas pendientes.
        
        Extensión del método original para agregar la reconciliación automática después
        de confirmar el pago.
        """
        # Ejecutar el método original de Odoo
        result = super().action_post()
        
        # 🆕 NUEVO: Intentar reconciliación automática después de registrar el pago
        for payment in self:
            if payment.state in ('in_process', 'paid'):
                _logger.info(
                    f"🔄 Ejecutando reconciliación automática para pago {payment.name}"
                )
                payment._auto_reconcile_payment()
        
        return result
