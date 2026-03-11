# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Digesto(models.Model):
    _inherit = 'digest.digest'

    kpi_empleado_noexistentes = fields.Boolean('Empleados No encontrados', help='Empleados que o se encontraron en TIPS')
    kpi_empleado_noexistentes_value = fields.Integer(string='Calculo de empleado', compute='_compute_empleados')
    kpi_empleado_sin_identificacion = fields.Boolean('Empleados Sin identificación', help='Empleados que o se encontraron en TIPS')
    kpi_empleado_sin_identificacion_value = fields.Integer(string='Empleado sin identificación', compute='_compute_empleados')
    kpi_empleado_sin_correo = fields.Boolean('Empleados Sin correo', help='Empleados que o se encontraron en TIPS')
    kpi_empleado_sin_correo_value = fields.Integer(string='Empleado sin identificación', compute='_compute_empleados')

    def _compute_empleados(self):
        empleados = self.env['hr.employee'].search([('active', '=', True)])
        for registros in self:
            registros.kpi_empleado_noexistentes_value = len(empleados)
        self.kpi_empleado_sin_identificacion_value = self.env['hr.employee'].search_count([('identification_id', '=', False)])
        self.kpi_empleado_sin_correo_value = self.env['hr.employee'].search_count([('work_email', '=', False)])
