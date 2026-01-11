from odoo import models, fields, api
from datetime import date


class GcCobrosAdmon(models.Model):
    _name = 'gc.cobros_admon'
    _description = 'Cobros de Administración'

    fecha_cobro = fields.Date(string='Fecha de Cobro', required=True)
    numero_apartamento_id = fields.Many2one('gc.apartamento', string='Apartamento', ondelete='restrict', required=True)
    producto_id = fields.Many2one('product.product', string='Concepto', ondelete='restrict', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, ondelete='restrict')
    monto_pago = fields.Monetary(string='Monto Pago', currency_field='currency_id', required=True)

    @api.onchange('producto_id', 'fecha_cobro')
    def _onchange_producto_monto(self):
        """Autocompletar monto desde gc.valores_conceptos"""
        if not self.producto_id or not self.fecha_cobro:
            return
        
        # Buscar valor vigente del producto
        valor = self.env['gc.valores_conceptos'].search([
            ('producto_id', '=', self.producto_id.id),
            ('activo', '=', True),
            ('fecha_inicial', '<=', self.fecha_cobro),
            '|',
            ('fecha_final', '=', False),
            ('fecha_final', '>=', self.fecha_cobro),
        ], limit=1, order='fecha_inicial desc')
        
        if valor:
            self.monto_pago = valor.monto
