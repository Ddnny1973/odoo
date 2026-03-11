# -*- coding: utf-8 -*-
from odoo import models, fields


class Cartera(models.Model):
    _name = 'gestor.cartera.team'
    _description = 'Saldo en Cartera'

    name = fields.Char('Sucursal')
    saldo = fields.Float('Saldo')
