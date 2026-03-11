# -*- coding: utf-8 -*-

from odoo import models, fields


class PResupuestosReport(models.TransientModel):
    _name = 'presupuestos.team.report.wizard'
    _description = 'Reporte de Presupuestos'

    date_from = fields.Date('Desde')
    date_to = fields.Date('Hasta')
    company_id = fields.Many2one('res.company')
    check_report = fields.Boolean('Reporte')

    def _print_report(self, data):
        return self.env.ref('gestor_team.action_report_presupuestos').report_action(self, data=data)
