# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class reconocimientologisticoTEAM(models.Model):
    _name = 'gestor.reconocimiento.logistico.team'
    _description = 'Reconocimiento logístico TEAM'

    name = fields.Many2one('product.product', string='Product')
    fecha = fields.Date('Fecha')
    precio_final = fields.Float('Precio Final',
                                help='En planes en CFM mayores a $99.900 Imp Incluidos \nPrecio Final de venta al publico IVA incluido')
    precio_final_sin_iva = fields.Float('Precio Final',
                                        help='Aplica IVA a equipos con valor igual o mayor a 783.354 \nPrecio Final de venta al publico SIN IVA')
    valor_sim_iva = fields.Float('Precio SIM',
                                 help='AValor SIM IVA incluido')
    reconocimiento = fields.Float('Reconocimiento', help='Reconocimiento Costo Logístico Para el Distribuidor')

    _sql_constraints = [('unq_reconocimiento_team_name', 'UNIQUE (name, fecha)',
                         'Un mismo producto no puede tener dos precios el mismo día!')
                        ]
