# -*- coding: utf-8 -*-
from odoo import models, fields, api
# import matplotlib.pyplot as plt, mpld3
# import matplotlib as mpld3
import numpy as np


class Zonas(models.Model):
    _name = 'gestor.zonas'
    _description = 'Zonas de venta'

    name = fields.Char('Zona')
    codigo = fields.Char('Código')
    country_id = fields.Many2one('res.country', string='País')
    state_id = fields.Many2one('res.country.state', domain="[('country_id', '=', country_id)]", string='Departamento')
    city_ids = fields.One2many('l10n_co_cities.city', 'zona_id', string='Ciudad')
    active = fields.Boolean('Activo', default=True)
    # mpld3_chart = fields.Text(string='Mpld3 Chart', compute='_compute_mpld3_chart', store=True)

    _sql_constraints = [('unq_zona_name', 'UNIQUE (name)',
                         'El nombre de la sucursal ya existe!'),
                        ('unq_zona_code', 'UNIQUE (codigo)',
                         'Este código ya existe!')
                        ]

    # def _compute_mpld3_chart(self):
    #     for rec in self:
    #         # Design your mpld3 figure:
    #         plt.scatter([1, 10], [5, 9])
    #
    #         X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
    #         C, S = np.cos(X), np.sin(X)
    #
    #         plt.plot(X, C)
    #
    #         figure = plt.figure()
    #         rec.mpld3_chart = mpld3.fig_to_html(figure)
