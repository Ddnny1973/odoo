# -*- coding: utf-8 -*-
from odoo import models, fields


class SimsPrendidas(models.Model):
    _name = 'gestor.sims.prendidas'
    _description = 'Sims Prendidas'

    iccid = fields.Char('ICCID', index=True)
    min = fields.Char('MIN', index=True)
    fecha = fields.Date('Fecha de Recarga')
    recarga = fields.Integer('Valor Recarga')

    _sql_constraints = [('unq_DP_team_name', 'UNIQUE (iccid, min, fecha, recarga)',
                         'El registro ya existe!')
                        ]
