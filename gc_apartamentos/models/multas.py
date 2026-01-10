from odoo import models, fields, api

class GcMultas(models.Model):
    _name = 'gc.multas'
    _description = 'Multas y Sanciones'
    _order = 'id desc'

    num_apartamento_id = fields.Many2one('gc.apartamento', string='Apartamento', required=True, help='Apartamento relacionado con la multa')
    fecha_multa = fields.Date(string='Fecha de Multa', required=True)
    concepto_multa = fields.Many2one(
        'product.product',
        string='Concepto de Multa',
        required=True,
        domain="[('categ_id.name', '=', 'Multas y Sanciones'), ('categ_id.parent_id.name', '=', 'Conceptos Condominio')]",
        help='Producto asociado a la multa, filtrado por categoría "Conceptos Condominio / Multas y Sanciones"'
    )
