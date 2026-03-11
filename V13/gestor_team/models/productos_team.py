# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class tipoproductosTEAM(models.Model):
    _name = 'gestor.tipo.productos.team'
    _description = 'Tipos de productos TEAM'

    name = fields.Char('Tipo de producto')

    _sql_constraints = [('unq_tipo_productos_team_name', 'UNIQUE (name)',
                         'El tipo de producto ya existe!')
                        ]


class productosTEAM(models.Model):
    _name = 'gestor.productos.team'
    _description = 'Productos globales TEAM'

    name = fields.Char('Producto')
    codigo = fields.Char('Código')
    descripcion = fields.Text('Descripción')

    # @api.constrains('name')
    # def _check_name(self):
    #    if self.name == self.name:
    #        raise ValidationError("El nombre del producto ya existe!")

    _sql_constraints = [('unq_productos_team_name', 'UNIQUE (name)',
                         'El nombre del producto ya existe!')
                        ]
    _sql_constraints = [('unq_productos_team_code', 'UNIQUE (codigo)',
                         'Este código ya existe!')
                        ]
