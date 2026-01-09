from odoo import models, fields


class GcValoresConceptos(models.Model):
    _name = 'gc.valores_conceptos'
    _description = 'Valores de Conceptos'

    fecha_inicial = fields.Date(string='Fecha Inicial', required=True)
    fecha_final = fields.Date(string='Fecha Final')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, ondelete='restrict')
    monto = fields.Monetary(string='Monto', currency_field='currency_id', required=True)
    producto_id = fields.Many2one('product.product', string='Producto', ondelete='cascade', required=True, help='Producto asociado al concepto de cobro')
    recurrente = fields.Boolean(string='Recurrente', default=True, help='Indica si este concepto es recurrente')
    activo = fields.Boolean(string='Activo', default=True, help='Indica si este concepto está activo')
    usar_coeficiente = fields.Boolean(
        string='Usar Coeficiente', 
        default=True, 
        help='Si está marcado, el monto se multiplicará por el coeficiente del apartamento. Si no, se usará el monto fijo.'
    )

