from odoo import models, fields


class GcValoresConceptos(models.Model):
    _name = 'gc.valores_conceptos'
    _description = 'Valores de Conceptos'

    fecha_inicial = fields.Date(string='Fecha Inicial', required=True)
    fecha_final = fields.Date(string='Fecha Final')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, ondelete='restrict')
    monto = fields.Monetary(string='Monto', currency_field='currency_id', required=True)
    concepto_id = fields.Many2one('gc.concepto', string='Concepto', ondelete='cascade', required=True)

