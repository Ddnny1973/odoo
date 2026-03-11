from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class CambiarFechasPeriodoWizard(models.TransientModel):
    _name = "gestor.cambiar.fechas.periodo.wizard"
    _description = "Cambia las fechas del período a liquidar"

    fecha_inicio = fields.Date('Inicio', help='Fecha inicio del período a liquidar')
    fecha_fin = fields.Date('Fin', help='Fecha final del período a liquidar')

    def action_fechas_update(self):
        # Actualizando período de consulta por usuario
        periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])
        if periodo:
            periodo.fecha_inicio = self.fecha_inicio
            periodo.fecha_fin = self.fecha_fin
        else:
            self.env['gestor.periodos.liquidacion'].create({'fecha_inicio': self.fecha_inicio,
                                                            'fecha_fin': self.fecha_fin, })
