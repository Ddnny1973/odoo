from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime

import logging

_logger = logging.getLogger(__name__)


class CambioResponsablesWizard(models.TransientModel):
    _name = "gestor.cambio.responsables.wizard"
    _description = "Cambiar responsables de forma masiva"

    responsable_origen = fields.Many2one('hr.employee',
                                         string='Responsable Original')
    responsable_destino = fields.Many2one('hr.employee',
                                          string='Responsable Destino')
    dependientes_ids = fields.One2many('hr.employee', 'actualizacion_masiva_wz_id',
                                       string='Dependientes')
    registros_count = fields.Integer(string='Cantidad de registros', compute='_registros_count')
    fecha = fields.Date('Inicio', required=True, default=fields.Date.today())
    todos = fields.Boolean('Todos', default=True)

    @api.onchange('responsable_origen', 'todos')
    def _empleados_a_procesar(self):
        if self.todos and self.responsable_origen:
            conteo = self.env['hr.employee'].search_count([('parent_id', '=', self.responsable_origen.id)])
            if len(self.responsable_origen) > 0:
                self.dependientes_ids = self.env['hr.employee'].search([('parent_id', '=', self.responsable_origen.id)])
            else:
                self.dependientes_ids = self.env['hr.employee'].search([('parent_id', '=', 0)])
                # self.registros_count = len(self._origin.dependientes_ids) # conteo
                self.dependientes_ids = self.env['hr.employee'].search([('parent_id', '=', self.responsable_origen.id)])
            self.registros_count = conteo
        else:
            self.dependientes_ids = None
            self.registros_count = 0

    @api.depends('dependientes_ids')
    def _registros_count(self):
        self.registros_count = len(self.dependientes_ids)

    def realizar_cambio(self):
        if self.responsable_destino:
            for empleados_ids in self.dependientes_ids:
                for i in self.env['hr.responsable.historico'].search([('empleado_id', '=', empleados_ids.id),
                                                                      ('fecha_fin', '=', False)]
                                                                     ):
                    i.fecha_fin = self.fecha - datetime.timedelta(days=1)
                empleados_ids.parent_id = self.responsable_destino.id
                empleados_ids.coach_id = self.responsable_destino.parent_id
                vals = {'name': self.responsable_destino.id,
                        'empleado_id': empleados_ids.id,
                        'fecha_inicio': self.fecha,
                        }
                self.env['hr.responsable.historico'].create(vals)
        else:
            raise ValidationError('Debe seleccionar un empleado como destino para realizar la nueva asignación.')
        self.responsable_destino = None
