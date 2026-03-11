# -*- coding: utf-8 -*-
from odoo import models, fields


class KitPrepagos(models.Model):
    _name = 'gestor.kit.prepagos.team'
    _description = 'Equipos KIT Prepago'

    identificacion = fields.Char('Identificación')
    vendedor = fields.Char('Vendedor')
    producto = fields.Char('Producto')
    numerofefactura = fields.Char('Numero De Factura')
    fechadeventa = fields.Char('Fecha De Venta')
    tipoproducto = fields.Char('Tipo De Producto')
    cantidad = fields.Float('Cantidad')
    vendedor_id = fields.Many2one('hr.employee', string='Vendedor ID', index=True)
    job_id = fields.Many2one('hr.job')
    responsable_id = fields.Many2one('hr.employee', string='Responsable')
    fecha = fields.Date('Fecha')
    categoria_tipo_planes_id = fields.Many2one('gestor.categoria.tipo.planes.team')
    tipo_plan_id = fields.Many2one('gestor.tipo.plan.team')
    tipo_plan = fields.Char('Tipo de Plan')
    year = fields.Integer('Año')
    mes = fields.Char('Mes')
