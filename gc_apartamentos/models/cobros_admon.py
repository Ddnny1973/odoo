from odoo import models, fields


class GcCobrosAdmon(models.Model):
    _name = 'gc.cobros_admon'
    _description = 'Cobros de Administración'

    fecha_cobro = fields.Date(string='Fecha de Cobro', required=True)
    numero_apartamento_id = fields.Many2one('gc.apartamento', string='Apartamento', ondelete='restrict', required=True)
    concepto_id = fields.Many2one('gc.concepto', string='Concepto', ondelete='restrict', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, ondelete='restrict')
    monto_pago = fields.Monetary(string='Monto Pago', currency_field='currency_id', required=True)
