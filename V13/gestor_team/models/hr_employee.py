# -*- coding: utf-8 -*-
from calendar import month
import logging
from odoo import models, fields, api
import datetime
import pymssql
import pandas as pd
import os
import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

param_dic = {
            'server': '20.119.218.50',
            'database': 'TipsII',
            'user': 'sa',
            'password': 'Soluciondig2015'
            }


def connect(params_dic):
    """ Connect to the SQL Server database server """
    conn = None
    try:
        # connect to the MSsqlServer server
        print('Conectandose con base de datos MS SQL Server Solución digital...')
        conn = pymssql.connect(**params_dic)
    except Exception as error:
        print(error)
        raise ValidationError(error)
    print("Conexión satisfactoria")
    return conn


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sucursal_id = fields.Many2one('gestor.sucursales',
                                  required=True,
                                  track_visibility='onchange')
    category_id = fields.Many2one('hr.employee.category',
                                  groups="hr.group_hr_manager",
                                  string='Categoría',
                                  required=True,
                                  track_visibility='onchange')
    comisiones_ids = fields.Many2many('gestor.comisiones.team',
                                      string='Comisiones',
                                      help='Comisiones que se aplican a este empleado')
    work_phone = fields.Char(track_visibility='onchange')
    private_email = fields.Char(track_visibility='onchange')
    phone = fields.Char(track_visibility='onchange')
    work_email = fields.Char('Work Email',
                             required=True,
                             track_visibility='onchange')
    identification_id = fields.Char(string='Identification No',
                                    groups="hr.group_hr_user",
                                    required=True)
    parent_id = fields.Many2one('hr.employee', 'Manager', required=True, track_visibility='onchange')
    job_id = fields.Many2one('hr.job', 'Job Position', required=True, track_visibility='onchange')
    department_id = fields.Many2one('hr.department', 'Department', required=True, track_visibility='onchange')
    especial_hogar = fields.Boolean('Especial HOGAR', help='Categoría especial para liquidación de comisiones de HOGAR', required=True, track_visibility='onchange')
    comisiones_hogar_ids = fields.One2many('gestor.captura.hogar.detalle.agrupado.team',
                                           'detalle_agrupado_hogar_id',
                                           string='Comisiones Hogar',
                                           track_visibility='onchange')
    planillas_hogar_id = fields.Integer('Planilla')
    tipo_cuenta = fields.Selection([('ahorros', 'Ahorros'), ('corriente', 'Corriente')], track_visibility='onchange')
    banco_id = fields.Many2one('res.bank', track_visibility='onchange')
    cuenta_id = fields.Char('No. Cuenta', track_visibility='onchange')
    otro_titular = fields.Boolean('Otro Titular', help='En caso de que la cuenta pertenezca a otra persona', track_visibility='onchange')
    nombre_titular = fields.Char('Nomre del titular', track_visibility='onchange')
    tipo_documento_titular = fields.Selection([('cc','Cédula'), ('nit', 'NIT')], track_visibility='onchange')
    identificacion_titular = fields.Integer('Número identificación', track_visibility='onchange')
    tarifa_especial_ids = fields.One2many('gestor.tarifas.especiales.hogar.historico',
                                          'empleado_id', string='Tarifa Especial',
                                          track_visibility='onchange')
    categoria_historico_ids = fields.One2many('gestor.hr.categoria.historico',
                                              'empleado_id', string='Categoría Empleados',
                                              track_visibility='onchange')
    planillas_wz_id = fields.Integer(string='Planillas de Liquidación')
    liquidacion_wz_id = fields.Integer(string='Liquidación comisiones')
    iva = fields.Float('IVA', help='Valor a aplicar de IVA (%)', track_visibility='onchange')
    retencion = fields.Float('Retención', help='Valor a aplicar de Retención (%)', track_visibility='onchange')
    reteiva = fields.Float('ReteIVA', help='Valor a aplicar de Retención al IVA (%)', track_visibility='onchange')
    descuento_biometria = fields.Float('Descuento Biometría',
                                       help='Valor a aplicar de descuento por biometría al asesor que realizó la venta.',
                                       track_visibility='onchange')
    comision_propia = fields.Boolean(default=False,
                                     string='Comisión Propia',
                                     help="Esta opción hace que se pague la comisión por gestión así la venta sea propia",
                                     track_visibility='onchange')
    tarifa_especial_id = fields.Many2one('gestor.tarifas.especiales.hogar',
                                         groups="hr.group_hr_manager",
                                         string='Tarifa Especial',
                                         # required=True,
                                         track_visibility='onchange')
    job_historico_ids = fields.One2many('hr.job.historico', 'empleado_id', string='Cargo', track_visibility='onchange')
    sucursal_historico_ids = fields.One2many('gestor.hr.sucursal.historico', 'empleado_id', string='Sucursal', cascade='True', track_visibility='onchange')
    responsable_historico_ids = fields.One2many('hr.responsable.historico', 'empleado_id', string='Responsable', track_visibility='onchange')
    sucursal_historico_cont = fields.Integer('Hitorico sucursales count', compute='_get_historicos_count')
    responsable_historico_cont = fields.Integer('Hitorico sucursales count', compute='_get_historicos_count')
    job_historico_cont = fields.Integer('Hitorico sucursales count', compute='_get_historicos_count')
    categoria_historico_cont = fields.Integer('Hitorico categorías count', compute='_get_historicos_count')
    planillas_wz_propias_id = fields.Integer(string='Planillas de Liquidación Ventas propias')
    planillas_hogar_wz_id = fields.Integer(string='Planillas de Liquidación Empleados a consultar')
    actualizacion_masiva_wz_id = fields.Integer(string='Cambios masivos')
    pagar_a = fields.Many2one('hr.employee', 'Pagar a',
                              help='Permite definir la información de a quien se le va a pagar realmente los valores de comisiones.',
                              track_visibility='onchange')
    user_id_tips = fields.Integer(string='User ID TIPSII', help='User ID del sistema TIPSII')
    no_biometrias = fields.Boolean(default=False, string='No descontar biometrías', help='Indica si se descuenta o no la biometría. Si se activa no descontará la biometría')
    validar_api = fields.Boolean(default=False, string='Validador API', help='Si esta activo el valor por defecto de Estado_Vendedor para el control de la API será el tres(3)')
    porcentajepresupuestales_ids = fields.One2many('gestor.porcentaje.presupuestales', 'employee_id', string='Presupuestos')
    base_liquidacion_id = fields.Integer(string='Base liquidación')
    liquidacion_descuentos_wz_id = fields.Integer(string='Liquidación Descuentos')
    estado_vendedor = fields.Integer('Estado Vendedor', compute='_get_estado',
                                      help='Verifica si el vendedor es nuevo o si tiene ventas en los últimos 3\n0 si no tiene teléfono\1No tiene ventas en los últimos 3 meses\n2 Si tiene ventas en los últimos 3 meses o es nuevo')

    _sql_constraints = [
                        ('unq_correo_hr_employee', 'UNIQUE (work_email)',
                         'El correo ya existe ya existe!'),
                        ('unq_identification_id_hr_employee', 'UNIQUE (identification_id)',
                         'La identificación ya existe, por favor verifique!')
                        ]

    @api.constrains('name', 'porcentajepresupuestales_ids')
    def _valida_porcentaje(self):
        total = 0
        sucursal_id = self._origin.id
        # raise ValidationError('sucursal_id: ' + str(sucursal_id.id))
        porcentajes_ids = self.env['gestor.porcentaje.presupuestales'].search([('employee_id', '=', sucursal_id)])
        if len(porcentajes_ids) > 0:
            for i in porcentajes_ids:
                total += i.porcentaje
            if total != 100:
                raise ValidationError('La suma de porcentajes debe ser igual al 100%.\nSuma actual: ' + str(total) + '%')

    @api.onchange('parent_id')
    def _get_monitor(self):
        self.coach_id = self.parent_id.parent_id or ''

    def _get_estado(self):
        for reg in self:
            # end_date = datetime.datetime.strptime(datetime.date, "%m/%d/%y") - datetime.timedelta(month=2)
            # end_date = datetime.date - relativedelta(months=2)
            # expired_date = fields.Datetime.from_string(reg.create_date) - relativedelta(months=2)
            limit_date_ingreso = fields.Datetime.from_string(fields.Date.today()) - relativedelta(days=91)
            #limit_date_ingreso1=fields.datetime.from_string(reg.fecha_limite)
            #create_date_str = reg.fecha_creacion
	    #create_limit_str = reg.fecha_tope
	    #create_date_obj = datetime.strptime(create_date_str, "%d/%m/%Y")
	    #create_limit_obj = datetime.strptime(create_limit_str, "%d/%m/%Y")

	    #limit_date_ingreso = create_date_obj + relativedelta(days=91)
            limit_date_venta = fields.Datetime.from_string(fields.Date.today()) - relativedelta(months=3)
            ventas = self.env['gestor.captura.hogar.team'].search([('id_asesor', '=', reg.id), ('fecha', '>=', limit_date_venta)])
			
	    #raise ValidationError('Fecha: ' + str(create_date_str))
            # raise ValidationError('Ventas: ' + str(len(ventas)))

            if reg.validar_api:
                if  reg.active == False:
                    reg.estado_vendedor = 0
                else: 
                    reg.estado_vendedor = 2              
            else:    
                if  reg.active == False:
                    reg.estado_vendedor = 0
                elif not reg.work_phone:
                    reg.estado_vendedor = 0
                elif reg.create_date < limit_date_ingreso and len(ventas)==0:
                    reg.estado_vendedor = 1
                elif reg.create_date < limit_date_ingreso and len(ventas)>0:
                    reg.estado_vendedor = 2
                elif reg.create_date >= limit_date_ingreso and len(ventas)==0:
                    reg.estado_vendedor = 2
                else:
                    reg.estado_vendedor = 0


    @api.constrains('cuenta_id')
    def _valida_campos(self):
        if self.cuenta_id:
            try:
                x = int(self.cuenta_id)
            except Exception as e:
                raise ValidationError('EL campo de Número de cuenta solo debe contener dígitos numéricos, por favor verifique!')

    def _get_historicos_count(self):
        for reg in self:
            reg.sucursal_historico_cont = len(reg.sucursal_historico_ids)
            reg.responsable_historico_cont = len(reg.responsable_historico_ids)
            reg.job_historico_cont = len(reg.job_historico_ids)
            reg.categoria_historico_cont = len(reg.categoria_historico_ids)

    @api.constrains('name', 'categoria_historico_ids')
    def _cambio_categoria_employee(self):
        for registros in self:
            reg = registros.categoria_historico_ids.search([('empleado_id', '=', registros.id)], limit=1)
            if len(reg) > 0:
                registros.category_id = reg.name
            else:
                vals = {'name': registros.category_id.id,
                        'empleado_id': registros._origin.id,

                        }
                registros.env['gestor.hr.categoria.historico'].create(vals)
        
            if registros.category_id.id == 1:
                registros.no_biometrias=True
            else:
                registros.no_biometrias=False    
        

    @api.constrains('name', 'tarifa_especial_ids')
    def _cambio_tarifa_especial_id_employee(self):
        for registros in self:
            reg = registros.env['gestor.tarifas.especiales.hogar.historico'].search([('empleado_id', '=', registros.id)], limit=1)
            if len(reg) > 0:
                registros.tarifa_especial_id = reg.name
            else:
                if registros.tarifa_especial_id:
                    vals = {'name': registros.tarifa_especial_id.id,
                            'empleado_id': registros._origin.id,
                            }
                    registros.env['gestor.tarifas.especiales.hogar.historico'].create(vals)

    @api.constrains('name', 'job_historico_ids')
    def _cambio_job_id_employee(self):
        for registros in self:
            reg = registros.env['hr.job.historico'].search([('empleado_id', '=', registros.id)], limit=1)
            if len(reg) > 0:
                registros.job_id = reg.name
                registros.job_title = reg.name.name
            else:
                vals = {'name': registros.job_id.id,
                        'empleado_id': registros._origin.id,
                        }
                registros.env['hr.job.historico'].create(vals)

    @api.constrains('name', 'sucursal_historico_ids')
    def _cambio_sucursal_id_employee(self):
        reg = self.env['gestor.hr.sucursal.historico'].search([('empleado_id', '=', self.id)], limit=1)
        if len(reg) > 0:
            self.sucursal_id = reg.name
        else:
            vals = {'name': self.sucursal_id.id,
                    'empleado_id': self._origin.id,
                    }
            self.env['gestor.hr.sucursal.historico'].create(vals)

    @api.constrains('name', 'responsable_historico_ids')
    def _cambio_responsable_id_employee(self):
        reg = self.env['hr.responsable.historico'].search([('empleado_id', '=', self.id)], limit=1)
        if len(reg) > 0:
            self.parent_id = reg.name
            self.coach_id = self.parent_id.parent_id
            
            
        else:
            vals = {'name': self.parent_id.id,
                    'empleado_id': self._origin.id,
                    }
            self.env['hr.responsable.historico'].create(vals)					   


    @api.constrains('user_id')
    def _cambio_user_id_employee(self):
        if self.user_id:
            None
        else:
            users = self.env['res.users'].search([('login', '=', self.work_email)])
            if users:
                self.user_id = users.id
            else:
                None
                # raise ValidationError('No se puede desvincular un empleado de su usuario: ' + self.name + '\nLogin: ' + str(self.work_email))

    # @api.onchange('tarifa_especial_id')
    # def _historico_tarifa_especial(self):
    #     vals = {}
    #     reg = self.env['gestor.tarifas.especiales.hogar.historico'].search([('empleado_id', '=', self._origin.id)])
    #     if len(reg) == 0:
    #         vals = {'name': self.tarifa_especial_id.id,
    #                 'empleado_id': self._origin.id,
    #                 'fecha_inicio': fields.Date.today(),
    #                 }
    #     else:
    #         vals = {'name': self.tarifa_especial_id.id,
    #                 'empleado_id': self._origin.id,
    #                 'fecha_inicio':  fields.Date.today(),
    #                 }
    #     self.env['gestor.tarifas.especiales.hogar.historico'].create(vals)

    @api.depends('category_id')
    @api.onchange('category_id')
    def __marcar_no_descontar_biometria(self):
         if self.category_id.id == 1:
            self.no_biometrias=True
         else:
            self.no_biometrias=False     

    def actualizar_monitores(self):
        self._cr.execute("""
                        update hr_employee a set coach_id =
                            (select parent_id from hr_employee b
                            where b.id=a.parent_id)
                        """
                    )

    def cargar_liquidaciones(self, fecha_incial='', fecha_final=''):
        self.env.cr.execute("""WITH RECURSIVE ctename AS
                                            (
                                				  SELECT id, name, parent_id
                                				  FROM hr_employee
                                				  WHERE parent_id = %s
                                            UNION
                                				  SELECT a.id, a.name, a.parent_id
                                				  FROM hr_employee a
                                					 JOIN ctename ON a.parent_id = ctename.id
                                            )
                                            SELECT id FROM ctename;
                            """,
                            (self.id,)
                            )
        hijos_ids = self.env.cr.fetchall()
        # raise ValidationError(self.id)
        # detalle_ids = self.env['gestor.captura.hogar.detalle.agrupado.team'].search([('captura_hogar_id.id_asesor', '=', self.id),
        #                                                                              ('captura_hogar_id.comision_pagada', '=', False)])
        detalle_ids = self.env['gestor.captura.hogar.detalle.agrupado.team'].search([('captura_hogar_id.id_asesor', 'in', hijos_ids),
                                                                                     ('captura_hogar_id.comision_pagada', '=', False),
                                                                                     ('captura_hogar_id.comision_liquidada', '=', True),
                                                                                     ('valor_comision', '>', 0)])
        self.comisiones_hogar_ids = detalle_ids
        for reg in detalle_ids:
            lf_precio = 0
            # li_empleado = self.vendedor.id
            # lc_tipo_plan = self.tipo_plan
            # lc_mintic = self.mintic

            ln_tiene_mintic = reg.env['gestor.comisiones.team'].search_count([('employees_ids', 'in', (self.id)),
                                                                               ('tipo_plan_ids', 'in', (41))
                                                                               ])
            # _logger.info('Vendedor: ' + self.vendedor.name)
            # # for reg in self.detalle_agrupado_captura_hogar_ids:
            # _logger.info('Tipo de plan: ' + str(reg.tipo_plan.id))
            # _logger.info('Servicio: ' + reg.servicio)
            # _logger.info('PETAR: ' + reg.petar)

            if reg.petar in ('5083', '5092'):
                ln_tiene_mintic = 1

            if reg.tipo_plan.id == 26:
                lf_precio = 0
            elif reg.tipo_plan.id == 24 and reg.servicio == 'Sencillo' and ln_tiene_mintic == 1:
                comisiones = reg.env['gestor.comisiones.team'].search([('employees_ids', 'in', (self.id)),
                                                                        ('tipo_plan_ids', 'in', (41))
                                                                        ])
                lf_precio = comisiones.mes1
            else:
                comisiones = reg.env['gestor.comisiones.team'].search([('employees_ids', 'in', (self.id)),
                                                                        ('tipo_plan_ids', 'in', (reg.tipo_plan.id))
                                                                        ])
                lf_precio = comisiones.mes1
            _logger.info('A pagar por registro: ' + str(lf_precio))
            # raise ValidationError(padre)
            reg.comision_padre = lf_precio


class HrCategory(models.Model):
    _inherit = 'hr.employee.category'

    comisiones_ids = fields.Many2many('gestor.comisiones.team',
                                      string='Comisiones',
                                      help='Comisiones que se aplican a esta categoría')
    planillas_wz_id = fields.Integer('Planillas WZ', help='Planillas que se aplican a esta categoría')
    comisiones_wz_id = fields.Integer('Comisiones WZ ', help='Comisiones que se aplican a esta categoría')


class HrJob(models.Model):
    _inherit = 'hr.job'

    planillas_wz_id = fields.Integer('Planillas WZ', help='Planillas que se aplican a esta categoría')
    comisiones_wz_id = fields.Integer('Comisiones WZ ', help='Comisiones que se aplican a esta categoría')


class HrJobHistorico(models.Model):
    _name = 'hr.job.historico'
    _inherit = ['mail.thread']
    _description = 'Historico puestos de trabajo de los empleados'
    _order = "fecha_inicio desc"

    name = fields.Many2one('hr.job', string='Cargo', required=True, track_visibility='onchange')
    empleado_id = fields.Many2one('hr.employee', required=True, track_visibility='onchange')
    fecha_inicio = fields.Date('Inicio', required=True, default=fields.Date.today(), track_visibility='onchange')
    fecha_fin = fields.Date('Fin', track_visibility='onchange')

    _sql_constraints = [
                        ('unq_job_historico', 'UNIQUE (empleado_id, fecha_inicio)',
                         'Ya existe un cargo con esa vigencia!')
                        ]

    @api.constrains('name', 'fecha_inicio', 'fecha_fin')
    def _validacion_fechas(self):
        # Buscando ventas de hogar
        fecha_final = self.fecha_fin or fields.Date.today()
        if self.fecha_inicio > fecha_final:
            raise ValidationError('La fecha final para el historico del puesto de trabajo debe ser mayor a la fecha de inicio, por favor verifique!.')

        historicos_count = self.env['hr.job.historico'].search_count([('fecha_fin', '=', False),
                                                                      ('empleado_id', '=', self._origin.empleado_id.id)])
        if historicos_count > 1:
            raise ValidationError('Existen varios registros sin fecha de finalización, revise por favor')

    def unlink(self):
        # raise ValidationError('borrando')
        for hitoricos_ids in self:
            ventas_ids = self.env['gestor.captura.hogar.team'].search([('vendedor', '=', hitoricos_ids.empleado_id.user_id.id),
                                                                       ('fecha', '>=', hitoricos_ids.fecha_inicio),
                                                                       ('fecha', '<=', hitoricos_ids.fecha_fin or fields.Date.today())])
            if len(ventas_ids) > 0:
                raise ValidationError('Existen ventas asociadas a este historico, no puede eliminar el registro.')
        return super(HrJobHistorico, self).unlink()


class HrSucursalHistorico(models.Model):
    _name = 'gestor.hr.sucursal.historico'
    _inherit = ['mail.thread']
    _description = 'Historico Sucursales de los empleados'
    _order = "fecha_inicio desc"

    name = fields.Many2one('gestor.sucursales', string='Sucursal', required=True, track_visibility='onchange')
    empleado_id = fields.Many2one('hr.employee', required=True, cascade='True', track_visibility='onchange')
    fecha_inicio = fields.Date('Inicio', required=True, default=fields.Date.today(), track_visibility='onchange')
    fecha_fin = fields.Date('Fin', track_visibility='onchange')

    _sql_constraints = [
                        ('unq_sucursal_historico', 'UNIQUE (empleado_id, fecha_inicio)',
                         'Ya existe una sucursal asignada con esa vigencia!')
                        ]

    @api.constrains('name', 'fecha_inicio', 'fecha_fin')
    def _validacion_fechas(self):
        # Buscando ventas de hogar
        fecha_final = self.fecha_fin or fields.Date.today()
        if self.fecha_inicio > fecha_final:
            raise ValidationError('La fecha final para el historico de la sucursal debe ser mayor a la fecha de inicio, por favor verifique!.')

        historicos_count = self.env['gestor.hr.sucursal.historico'].search_count([('fecha_fin', '=', False),
                                                                                  ('empleado_id', '=', self._origin.empleado_id.id)])
        if historicos_count > 1:
            raise ValidationError('Existen varios registros sin fecha de finalización, revise por favor')

    def unlink(self):
        # raise ValidationError('borrando')
        for hitoricos_ids in self:
            ventas_ids = self.env['gestor.captura.hogar.team'].search([('vendedor', '=', hitoricos_ids.empleado_id.user_id.id),
                                                                       ('fecha', '>=', hitoricos_ids.fecha_inicio),
                                                                       ('fecha', '<=', hitoricos_ids.fecha_fin or fields.Date.today())])
            if len(ventas_ids) > 0:
                raise ValidationError('Existen ventas asociadas a este historico, no puede eliminar el registro.')
        return super(HrSucursalHistorico, self).unlink()


class HrResponsablelHistorico(models.Model):
    _name = 'hr.responsable.historico'
    _inherit = ['mail.thread']
    _description = 'Historico del responsable del empleado'
    _order = "fecha_inicio desc"

    name = fields.Many2one('hr.employee', string='Responsable', required=True, track_visibility='onchange')
    empleado_id = fields.Many2one('hr.employee', required=True, cascade='True', track_visibility='onchange')
    fecha_inicio = fields.Date('Inicio', required=True, default=fields.Date.today(), track_visibility='onchange')
    fecha_fin = fields.Date('Fin', track_visibility='onchange')

    _sql_constraints = [
                        ('unq_responsable_historico', 'UNIQUE (empleado_id, fecha_inicio)',
                         'Ya existe un responsable asignado con esa vigencia!')
                        ]

    @api.constrains('name', 'fecha_inicio', 'fecha_fin')
    def _validacion_fechas(self):
        # Buscando ventas de hogar
        fecha_final = self.fecha_fin or self.fecha_inicio
        if self.fecha_inicio > fecha_final:
            raise ValidationError('La fecha final para el historico del responsable debe ser mayor a la fecha de inicio, por favor verifique!.')
        historicos_count = self.env['hr.responsable.historico'].search_count([('fecha_fin', '=', False),
                                                                              ('empleado_id', '=', self._origin.empleado_id.id)])
        if historicos_count > 1:
            raise ValidationError('Existen varios registros sin fecha de finalización, revise por favor')

    def unlink(self):
        # raise ValidationError('borrando')
        for hitoricos_ids in self:
            ventas_ids = self.env['gestor.captura.hogar.team'].search([('vendedor', '=', hitoricos_ids.empleado_id.user_id.id),
                                                                       ('fecha', '>=', hitoricos_ids.fecha_inicio),
                                                                       ('fecha', '<=', hitoricos_ids.fecha_fin or fields.Date.today())])
            if len(ventas_ids) > 0:
                raise ValidationError('Existen ventas asociadas a este historico, no puede eliminar el registro.')
        return super(HrResponsablelHistorico, self).unlink()


class HrCategoriasHistorico(models.Model):
    _name = 'gestor.hr.categoria.historico'
    _inherit = ['mail.thread']
    _description = 'Historico Categorias empleados'
    _order = "fecha_inicio desc"

    name = fields.Many2one('hr.employee.category', string='Categoría Empleados', required=True, track_visibility='onchange')
    empleado_id = fields.Many2one('hr.employee', required=True, cascade='True', track_visibility='onchange')
    fecha_inicio = fields.Date('Inicio', required=True, default=fields.Date.today(), track_visibility='onchange')
    fecha_fin = fields.Date('Fin', track_visibility='onchange')

    _sql_constraints = [
                        ('unq_categoria_historico', 'UNIQUE (name, empleado_id, fecha_inicio)',
                         'Ya existe una categoría con esa vigencia!')
                        ]

    @api.constrains('name', 'fecha_inicio', 'fecha_fin')
    def _validacion_fechas(self):
        # Buscando ventas de hogar
        fecha_final = self.fecha_fin or fields.Date.today()
        if self.fecha_inicio > fecha_final:
            raise ValidationError('La fecha final para el historico de la categoría debe ser mayor a la fecha de inicio, por favor verifique!.')

        historicos_count = self.env['gestor.hr.categoria.historico'].search_count([('fecha_fin', '=', False),
                                                                                   ('empleado_id', '=', self._origin.empleado_id.id)])
        if historicos_count > 1:
            raise ValidationError('Existen varios registros sin fecha de finalización, revise por favor')

    def unlink(self):
        # raise ValidationError('borrando')
        for hitoricos_ids in self:
            ventas_ids = self.env['gestor.captura.hogar.team'].search([('vendedor', '=', hitoricos_ids.empleado_id.user_id.id),
                                                                       ('fecha', '>=', hitoricos_ids.fecha_inicio),
                                                                       ('fecha', '<=', hitoricos_ids.fecha_fin or fields.Date.today())])
            if len(ventas_ids) > 0:
                raise ValidationError('Existen ventas asociadas a este historico, no puede eliminar el registro.')
        return super(HrCategoriasHistorico, self).unlink()


class HrTarifasEspecialesHistorico(models.Model):
    _name = 'gestor.tarifas.especiales.hogar.historico'
    _inherit = ['mail.thread']
    _description = 'Historico Tarifas especiales'
    _order = "fecha_inicio desc"

    name = fields.Many2one('gestor.tarifas.especiales.hogar', string='Tarifa', required=True, track_visibility='onchange')
    empleado_id = fields.Many2one('hr.employee', required=True, track_visibility='onchange')
    fecha_inicio = fields.Date('Inicio', required=True, default=fields.Date.today(), track_visibility='onchange')
    fecha_fin = fields.Date('Fin', track_visibility='onchange')

    _sql_constraints = [
                        ('unq_tarifa_especial_historico', 'UNIQUE (empleado_id, name, fecha_inicio)',
                         'Ya existe una tarifa especial con esa vigencia!'),
                        ('unq_inicio_especial_historico', 'UNIQUE (empleado_id, fecha_inicio)',
                         'Ya existe una tarifa especial con ese inicio de vigencia!'),

                        ]

    @api.constrains('name', 'fecha_inicio', 'fecha_fin')
    def _validacion_fechas(self):
        # Buscando ventas de hogar
        fecha_final = self.fecha_fin or fields.Date.today()
        if self.fecha_inicio > fecha_final:
            raise ValidationError('La fecha final para el historico de las tarifas debe ser mayor a la fecha de inicio, por favor verifique!.')

        historicos_count = self.env['gestor.tarifas.especiales.hogar.historico'].search_count([('fecha_fin', '=', False),
                                                                                               ('empleado_id', '=', self._origin.empleado_id.id)])
        if historicos_count > 1:
            raise ValidationError('Existen varios registros sin fecha de finalización, revise por favor')

    def unlink(self):
        # raise ValidationError('borrando')
        for hitoricos_ids in self:
            ventas_ids = self.env['gestor.captura.hogar.team'].search([('vendedor', '=', hitoricos_ids.empleado_id.user_id.id),
                                                                       ('fecha', '>=', hitoricos_ids.fecha_inicio),
                                                                       ('fecha', '<=', hitoricos_ids.fecha_fin or fields.Date.today())])
            if len(ventas_ids) > 0:
                raise ValidationError('Existen ventas asociadas a este historico, no puede eliminar el registro.')
        return super(HrTarifasEspecialesHistorico, self).unlink()
    
