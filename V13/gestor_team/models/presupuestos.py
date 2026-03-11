import logging
import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Presupuestos(models.Model):
    _name = 'gestor.presupuestos.team'
    _inherit = ['mail.thread']
    _description = 'Gestión de presupuestos'

    cargo_id = fields.Many2one('hr.job', required=True)
    responsable_id = fields.Many2one('hr.employee')
    identificacion_responsable = fields.Char(related='responsable_id.identification_id', store=True)
    empleado_id = fields.Many2one('hr.employee', required=True, index=True)
    identificacion_empleado = fields.Char(related='empleado_id.identification_id', store=True)
    responsable = fields.Char(string='Responsable', default='empleado_id.parend_id.name')
    mes = fields.Selection([('01', 'Enero'),
                            ('02', 'Febrero'),
                            ('03', 'Marzo'),
                            ('04', 'Abril'),
                            ('05', 'Mayo'),
                            ('06', 'Junio'),
                            ('07', 'Julio'),
                            ('08', 'Agosto'),
                            ('09', 'Septiembre'),
                            ('10', 'Octubre'),
                            ('11', 'Noviembre'),
                            ('12', 'Diciembre'),
                            ], copy=False, index=True)
    year = fields.Integer('Año', required=True, default=fields.Date.today().year, group_operator=False)
    presupuesto_detalle_ids = fields.One2many('gestor.presupuestos.detalle.team', 'presupuesto_id')

    _sql_constraints = [('unq_presupuesto_team', 'UNIQUE (empleado_id, year, mes)',
                         'El presupuesto para este mes ya existe!')]

    def calculo_ejecutado(self):
        inicio_busqueda_iterativa = datetime.datetime.now()
        for registros in self:
            # Verificando si es responsable de vendedores
            vendedores = []
            for i in registros.env['hr.employee'].search([('parent_id', '=', registros.empleado_id.id)]):
                vendedores.append(i.id)
            # Buscando categorías de preupuesto propio.
            for i in registros.presupuesto_detalle_ids:
                if vendedores:
                    ventas_acumuladas = 0
                    for j in registros.env['gestor.presupuestos.detalle.team'].search([('presupuesto_id.empleado_id.id', 'in', vendedores),
                                                                                       ('categorias_planes_id', '=', i.categorias_planes_id.id),
                                                                                       ('presupuesto_id.mes', '=',  registros.mes),
                                                                                       ('presupuesto_id.year', '=', registros.year)]):
                        ventas_acumuladas = ventas_acumuladas + j.ejecutado_propio
                else:
                    ventas_acumuladas = 0
                i.ejecutado = ventas_acumuladas + i.ejecutado_propio
            # registros.ejecutado_propio = ventas
        fin_busqueda_iterativa = datetime.datetime.now()
        duracion_busqueda = fin_busqueda_iterativa - inicio_busqueda_iterativa
        _logger.info('Duración búsqueda ventas iterativa ' + registros.identificacion_empleado + ': ' + str(duracion_busqueda))
        # Actualización por BD
        # update gestor_presupuestos_detalle_team set ejecutado_propio=presupuesto_ejecucion_propia(id);
        # update gestor_presupuestos_detalle_team set ejecutado=presupuesto_ejecucion_responsable(
        # 	employee_id,
        # 	year,
        # 	mes,
        # 	categorias_planes_id);


    @api.onchange('mes')
    def _copy_hijos(self):
        # Borrando _copy_hijos
        for rec in self:
            rec.presupuesto_detalle_ids = [(5, 0, 0)]

        detalle = []
        meses = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        mes_anterior = meses[int(self.mes) - 2]
        if self.mes == '01':
            year = self.year - 1
        else:
            year = self.year
        presupuesto_origen_id = self.env['gestor.presupuestos.team'].search([('empleado_id', '=', self.empleado_id.id),
                                                                             ('year', '=', year),
                                                                             ('mes', '=', mes_anterior)])
        if presupuesto_origen_id:
            for i in self.env['gestor.presupuestos.detalle.team'].search([('presupuesto_id', '=', presupuesto_origen_id.id)]):
                detalle.append({'presupuesto_id': self.id,
                                'categorias_planes_id': i.categorias_planes_id.id,
                                'presupuesto': i.presupuesto,
                                'especial': i.especial})
            self.env['gestor.presupuestos.detalle.team'].create(detalle)

    @api.onchange('empleado_id')
    def _get_cargo(self):
        self.cargo_id = self.empleado_id.job_id

    class PresupuestosDetalle(models.Model):
        _name = 'gestor.presupuestos.detalle.team'
        _inherit = ['mail.thread']
        _description = 'Gestión de presupuestos'

        # Cálculo por asignar al momento de grabar el registro
        def _calculo_por_asignar(self):
            for presupuesto_encabezado in self:
                responsable_id = presupuesto_encabezado.presupuesto_id.responsable_id.id
                categoria_id = presupuesto_encabezado.categorias_planes_id.id
                presupuesto_responsable = 0
                presupuesto_asignado = 0
                mes = presupuesto_encabezado.presupuesto_id.mes
                year = presupuesto_encabezado.presupuesto_id.year
                if responsable_id:
                    for presupuesto_ids in presupuesto_encabezado.env['gestor.presupuestos.team'].search([('empleado_id', '=', responsable_id),
                                                                                                          ('mes', '=', mes),
                                                                                                          ('year', '=', year)]):
                        registros_detalle = presupuesto_ids.presupuesto_detalle_ids
                        for i in registros_detalle:
                            if i.categorias_planes_id.id == categoria_id:
                                presupuesto_responsable = i.presupuesto
                    # Presupuestos asignados del responsable
                    for presupuesto_ids in presupuesto_encabezado.env['gestor.presupuestos.detalle.team'].search([('presupuesto_id.responsable_id', '=', responsable_id),
                                                                                                              ('presupuesto_id.year', '=', year),
                                                                                                              ('presupuesto_id.mes', '=', mes),
                                                                                                              ('categorias_planes_id', '=', categoria_id)]):
                        presupuesto_asignado = presupuesto_asignado + presupuesto_ids.presupuesto
                presupuesto_encabezado.por_asignar = presupuesto_responsable - presupuesto_asignado

        # Cálculo por asignar al momento de digitar el registro
        @api.depends('categorias_planes_id')
        @api.onchange('presupuesto', 'categorias_planes_id')
        def _calculo_por_asignar_dinamico(self):
            for presupuesto_encabezado in self:
                responsable_id = presupuesto_encabezado.presupuesto_id.responsable_id.id
                categoria_id = presupuesto_encabezado.categorias_planes_id.id
                presupuesto_responsable = 0
                presupuesto_asignado = 0
                mes = presupuesto_encabezado.presupuesto_id.mes
                year = presupuesto_encabezado.presupuesto_id.year
                if responsable_id:
                    for presupuesto_ids in presupuesto_encabezado.env['gestor.presupuestos.team'].search([('empleado_id', '=', responsable_id),
                                                                                                          ('mes', '=', mes),
                                                                                                          ('year', '=', year)]):
                        registros_detalle = presupuesto_ids.presupuesto_detalle_ids
                        for i in registros_detalle:
                            if i.categorias_planes_id.id == categoria_id:
                                presupuesto_responsable = i.presupuesto
                    # Presupuestos asignados del responsable
                    for presupuesto_ids in presupuesto_encabezado.env['gestor.presupuestos.detalle.team'].search([('presupuesto_id.responsable_id', '=', responsable_id),
                                                                                                              ('presupuesto_id.year', '=', year),
                                                                                                              ('presupuesto_id.mes', '=', mes),
                                                                                                              ('categorias_planes_id', '=', categoria_id)]):
                        presupuesto_asignado = presupuesto_asignado + presupuesto_ids.presupuesto
                presupuesto_encabezado.por_asignar = presupuesto_responsable - presupuesto_asignado - presupuesto_encabezado.presupuesto

        # Cálculo iterativo de ventas
        @api.depends('categorias_planes_id')
        def _calculo_iterativo(self):
            # Actualizando ventas propias
            self.env.cr.execute("""update gestor_presupuestos_detalle_team a set ejecutado_propio = presupuesto_ejecucion_propia(a.id);""")
            self.env.cr.execute("""update gestor_presupuestos_detalle_team a set ejecutado=presupuesto_ejecucion_responsable(	a.employee_id,
																							a.year,
																							a.mes,
																							a.categorias_planes_id) + a.ejecutado_propio;""")
            inicio_busqueda_iterativa = datetime.datetime.now()
            for registros in self:
                # Verificando ventas propias
                ventas_acumuladas = 0
                # Verificando si es responsable de vendedores
                vendedores = registros.env['hr.employee'].search([('parent_id', '=', registros.presupuesto_id.empleado_id.id)])
                if vendedores:
                    for i in vendedores:
                        for j in registros.env['gestor.presupuestos.detalle.team'].search([('presupuesto_id.empleado_id.id', '=', i.id),
                                                                                           ('categorias_planes_id', '=', registros.categorias_planes_id.id),
                                                                                           ('presupuesto_id.mes', '=',  registros.presupuesto_id.mes),
                                                                                           ('presupuesto_id.year', '=', registros.year)]):
                            ventas_acumuladas = ventas_acumuladas + j.ejecutado
                registros.ejecutado = registros.ejecutado_propio + ventas_acumuladas
            fin_busqueda_iterativa = datetime.datetime.now()
            duracion_busqueda = fin_busqueda_iterativa - inicio_busqueda_iterativa
            _logger.info('Duración proceso automático actualización presupuesto dpf_0001: ' + str(duracion_busqueda))

        presupuesto_id = fields.Many2one('gestor.presupuestos.team')
        categorias_planes_id = fields.Many2one('gestor.categoria.tipo.planes.team', required=True)
        presupuesto = fields.Integer('Presupuesto', required=True)
        cargo = fields.Char(string='Cargo', related='presupuesto_id.cargo_id.name')
        employee = fields.Char(string='Empleado', related='presupuesto_id.empleado_id.name', store=True)
        employee_id = fields.Integer(related='presupuesto_id.empleado_id.id', store=True, string='Empleado ID')
        responsable_id = fields.Integer(related='presupuesto_id.responsable_id.id', store=True, string='Responsable ID')
        responsable = fields.Char(string='Responsable', related='presupuesto_id.responsable_id.name', store=True)
        mes = fields.Selection([('01', 'Enero'),
                                ('02', 'Febrero'),
                                ('03', 'Marzo'),
                                ('04', 'Abril'),
                                ('05', 'Mayo'),
                                ('06', 'Junio'),
                                ('07', 'Julio'),
                                ('08', 'Agosto'),
                                ('09', 'Septiembre'),
                                ('10', 'Octubre'),
                                ('11', 'Noviembre'),
                                ('12', 'Diciembre'),
                                ], related='presupuesto_id.mes', store=True)
        year = fields.Integer(string='Año', related='presupuesto_id.year', store=True)
        especial = fields.Boolean('Especial', help='Comisión especial')
        por_asignar = fields.Integer(compute='_calculo_por_asignar',
                                     default=_calculo_por_asignar,
                                     help='Presupuesto pendiente por asignar según árbol de asignación')
        ejecutado = fields.Integer(string='Ejecutado',
                                   help='Presupuesto ejecutado en el período propio y de dependientes.')
        ejecutado_propio = fields.Integer(string='Ejecutado Propio',
                                          help='Preuspuesto ejecutado en el período.',
                                          store=True)
        # ejecutado_propio = fields.Integer(string='Ejecutado Propio',
        #                                   help='Preuspuesto ejecutado en el período.',
        #                                   store=True,
        #                                   compute=_calculo_iterativo)

        @api.onchange('presupuesto')
        @api.constrains('presupuesto')
        def _check_valor_presupuesto(self):
            for i in self:
                if i.presupuesto > i.por_asignar and i.presupuesto_id.responsable_id and 1 == 2:
                    i.presupuesto = False
                    raise ValidationError('El presupuesto no puede ser mayor al disponible por asignar!')
