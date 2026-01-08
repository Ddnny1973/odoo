from odoo import models, fields


class GcConcepto(models.Model):
    _name = 'gc.concepto'
    _description = 'Concepto'

    name = fields.Char(string='Concepto', required=True)
    tipo_concepto = fields.Selection(
        [('admon', 'Cuota Admon'), ('extra', 'Cuota Extra'), ('multa', 'Multa')],
        string='Tipo de Concepto', required=True, default='admon'
    )
    valor_ids = fields.One2many('gc.valores_conceptos', 'concepto_id', string='Valores')
