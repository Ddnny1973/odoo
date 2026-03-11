 # -*- coding: utf-8 -*-
import logging
import pandas as pd
from odoo import models, fields, api

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class comisionesTEAM(models.Model):
    _name = 'gestor.comisiones.team'
    _inherit = ['mail.thread']
    _description = 'Esquema de comisiones TEAM'

    servicios_selection = [('Doble','Doble'),
                            ('Doble DTH','Doble DTH'),
                            ('FOX','FOX'),
                            ('FOX+','FOX+'),
                            ('FULLPACK FOX','FULLPACK FOX'),
                            ('GOLDEN PREMIER','GOLDEN PREMIER'),
                            ('HBO','HBO'),
                            ('HOTPACK','HOTPACK'),
                            ('Sencillo','Sencillo'),
                            ('Sencillo DTH','Sencillo DTH'),
                            ('Triple','Triple'),
                            ('Triple DTH','Triple DTH'),
                            ('ULTRA WIFI','ULTRA WIFI'),
                            ('ULTRAWIFI','ULTRAWIFI'),
                            ('WIN PREMIUM','WIN PREMIUM'),
                            ('WIN+ PREMIUM SD','WIN+ PREMIUM SD')
                           ]

    def _get_servicios(self):
        base = {}
        self._cr.execute("select servicio from gestor_base_liquidacion_hogar group by servicio;")

        for reg in self._cr.fetchall():
            # valor = reg[0]
            # raise ValidationError(valor)
            base[reg[0]] = reg[0]
        myList = base.items()
        raise ValidationError(myList)
        # state = fields.Selection(STATES, default=STATES[0][0])
        return myList

    name = fields.Char('Esquema', help='Identificación o nombre del plan de comisiones', copy=False)
    codigo = fields.Char('Código', help='Código único del Esquema de comisiones', copy=False)
    descripcion = fields.Text('Descripción')
    # activo = fields.Boolean(default=True, string='Activo', help="Archiva o desarchivar el registro.", track_visibility='onchange')
    employees_ids = fields.Many2many('hr.employee', string='Empleados', track_visibility='onchange')
    tipo_plan_ids = fields.Many2many('gestor.tipo.plan.team', string='Tipo de plan', track_visibility='onchange')
    categoria_tipo_plan_ids = fields.Many2many('gestor.categoria.tipo.planes.team', track_visibility='onchange')
    categoria_empleado_ids = fields.Many2many('hr.employee.category', track_visibility='onchange')
    sucursales_ids = fields.Many2many('gestor.sucursales', track_visibility='onchange')
    job_ids = fields.Many2many('hr.job', string='Cargo')
    canal_id = fields.Boolean(default=False, string='Pago por canal', help="Determina si la tabla de pago depende del canal del empleado.", track_visibility='onchange') # eliminar
    canales_ids = fields.Many2many('crm.team', string='Canales', track_visibility='onchange')
    dependencia_id = fields.Boolean(default=False, string='Pago por dependencia', track_visibility='onchange') # Eliminar
    por_responsable = fields.Many2one('hr.employee', track_visibility='onchange')  # Validar que solo sean responsables
    tope = fields.Integer('Tope', track_visibility='onchange')
    tope_minimo = fields.Integer('Tope Mínimo', track_visibility='onchange')
    tope_maximo = fields.Integer('Tope Máximo', track_visibility='onchange')
    meta = fields.Integer('Meta', help='Pago por cumplimiento de meta', track_visibility='onchange')
    porc_pago = fields.Float('Porcentaje de Pago', track_visibility='onchange')
    pago_fijo = fields.Float('Pago Fijo', track_visibility='onchange')
    planes_ids = fields.Many2many('gestor.planes.team', string='Planes', track_visibility='onchange')
    planes_ex_ids = fields.Many2many('gestor.planes.team', 'gestor_comisiones_team_gestor_planes_team_ex_rel', string='Planes Excluidos',
                                     track_visibility='onchange',
                                     help='Estos planes no estarán dentro de este esquema de comisión.')
    tipo_pago = fields.Selection([('valor', 'Por Valor Fijo'),
                                  ('porcentaje', 'Porcentaje')], track_visibility='onchange')
    mes1 = fields.Float('Pago 1')
    mes2 = fields.Float('Pago 2')
    mes3 = fields.Float('Pago 3')
    mes4 = fields.Float('Pago 4')
    mes5 = fields.Float('Pago 5')
    mes6 = fields.Float('Pago 6')
    secuencia = fields.Integer(string='Secuencia de aplicación', compute='_get_prioridad')
    pago_obligado = fields.Boolean(default=False, string='Pago Obligatorio',
                                   help="Esta opción hace que el esquema se pague adicional a otros esquemas asociados a la venta.",
                                   track_visibility='onchange')
    limite_ventas = fields.One2many('gestor.limites.venta', 'name', string='Limite de Ventas', help='Topes de ventas', track_visibility='onchange')
    tarifas_especiales_ids = fields.Many2many('gestor.tarifas.especiales.hogar', string='Tarifas Especiales', track_visibility='onchange')
    tarifas_especiales_count = fields.Integer('Cantidad TE', compute='_cantidad_tarifas_especiales', track_visibility='onchange')
    limite_ventas_count = fields.Integer('Cantidad TE', compute='_cantidad_limite_ventas', track_visibility='onchange')
    servicios_tmp = fields.Selection(selection=servicios_selection, string='Servicios', track_visibility='onchange')
    es_incentivo = fields.Boolean('Incentivo/Descuento', default=False, help="Es incentivo o descuento por venta.\nSi es decuento colocar el valor negativo.", track_visibility='onchange')
    tipo_comision = fields.Selection([('comision','Comisión'),
                                      ('incentivo', 'Incentivo'),
                                      ('descuento', 'Descuento'),
                                      ('biometria', 'Biometría')
                                      ],
                                     required=True,
                                     track_visibility='onchange'
                                     )
    convergencia = fields.Selection([('si', 'Si'), ('no', 'No')], string='Convergencia', default='no', track_visibility='onchange')
    estado_venta = fields.Many2many('gestor.estados_ap.team', string='Estado de la Venta',
                                    track_visibility='onchange',
                                    help='Estado de la venta para las biometrías'
                                    )
    # condiciones_ids = fields.One2many('gestor.prioridades.comisiones.team', 'name')
    condiciones_ids = fields.One2many('gestor.prioridades.comisiones.team',
                                      'name',
                                      string='Condiciones',
                                      help='Condiciones del esquema.\nLa posición indica prioridad.',
                                      track_visibility='onchange',
                                      copy=True)
    active = fields.Boolean('Activo', default=True)
    referidos_ids = fields.Many2many('gestor.referidos.team', string='Referidos', track_visibility='onchange')
    all_referidos = fields.Boolean('Todos los Referidos', help='Si esta activo, el esquema tendrá encuenta a todos los referidos activos en la tabla de referidos')

    _sql_constraints = [('unq_comisiones_team_name', 'UNIQUE (name)',
                         'El nombre del Esquema ya existe!'),
                        ('unq_comisiones_team_name', 'UNIQUE (codigo)',
                         'El código del plan de Esquemas ya existe!')]

    @api.onchange('tarifas_especiales_ids')
    def _cantidad_tarifas_especiales(self):
        self.tarifas_especiales_count = len(self.tarifas_especiales_ids)

    @api.onchange('all_referidos')
    def _get_referidos(self):
        if self.all_referidos:
            self.referidos_ids = self.env['gestor.referidos.team'].search([])

    @api.onchange('tipo_comision')
    def _tipo_comision(self):
        if self.tipo_comision != 'biometria':
            self.es_incentivo = False

    @api.onchange('limite_ventas')
    def _cantidad_limite_ventas(self):
        self.limite_ventas_count = len(self.limite_ventas)

    def _get_prioridad(self):
        for reg in self:
            prioridad = 0
            if reg.por_responsable:
                prioridad += 100
            if reg.employees_ids:
                prioridad += 80
            if reg.categoria_empleado_ids:
                prioridad += 60
            if reg.job_ids:
                prioridad += 40
            if reg.canales_ids:
                prioridad += 20

            if reg.sucursales_ids:
                prioridad += 100

            if reg.planes_ids:
                prioridad += 100
            if reg.categoria_tipo_plan_ids:
                prioridad += 80
            if reg.tipo_plan_ids:
                prioridad += 60

            reg.secuencia = prioridad


class LimitesDeVenta(models.Model):
    _name = 'gestor.limites.venta'
    _description = 'Topes para la cantidad de ventas'
    _order = 'desde'

    name = fields.Many2one('gestor.prioridades.comisiones.team')
    desde = fields.Integer('Desde', help='Valor desde donde se comenzará a aplicar el pago de la comisión')
    hasta = fields.Integer('Hasta', help='Valor hasta donde se pagará la comisión, por encima de esto no será tenido en cuenta.')
    valor = fields.Float('Valor', help='Valor a pagar por rango')


class VentasComisiones(models.Model):
    _name = 'gestor.consulta.comisiones.tips'
    _description = 'Consulta Ventas para Comisiones'

    def _get_categoria_plan(self):
        for registros in self:
            categoria = registros.env['gestor.tipo.plan.team'].search([('name', '=', registros.tipo_plan)])
            registros.categoria_tipo_plan = categoria.categoria_id.name

    def _get_year(self):
        for registros in self:
            registros.year = registros.fecha.strftime("%Y")

    def _get_month(self):
        for registros in self:
            registros.mes = registros.fecha.strftime("%m")

    def _get_presupuesto(self):
        for registros in self:
            categoria_id = registros.env['gestor.categoria.tipo.planes.team'].search([('name', '=', registros.categoria_tipo_plan)])
            presupuesto_id = registros.env['gestor.presupuestos.team'].search([('identificacion_empleado', '=', registros.vendedor_id),
                                                                            ('year', '=', registros.year),
                                                                            ('mes', '=', registros.mes)])
            if presupuesto_id:
                for i in presupuesto_id.presupuesto_detalle_ids.search([('categorias_planes_id.id', '=', categoria_id.id)]):
                    registros.presupuesto = i.presupuesto
            else:
                registros.presupuesto = 0

    fecha = fields.Date('Fecha')
    min = fields.Char('MIN')
    iccid = fields.Char('ICCID')
    imei = fields.Char('IMEI')
    contrato = fields.Char('Contrato')
    valor = fields.Char('Valor')
    custcode = fields.Char('CUSTCODE')
    marca_del_equipo = fields.Char('Marca del equipo')
    nombre_de_equipo_en_stok = fields.Char('Nombre del equipo en STOK')
    nombre_de_la_simcard_en_stok = fields.Char('Nombre de la simcard en STOK')
    modelo_del_equipo = fields.Char('Modelo del equipo')
    valor_del_equipo = fields.Char('Valor del equipo')
    nombre_para_mostrar_del_vendedor = fields.Char('Nombre para mostrar del vendedor')
    tipo_de_vendedor = fields.Char('Tipo de vendedor')
    regional = fields.Char('Regional')
    sucursal = fields.Char('Sucursal')
    ciudad = fields.Char('Ciudad')
    nombre_del_plan = fields.Char('Nombre del plan')
    tipo_de_plan = fields.Char('Tipo de plan')
    valor_cobrado = fields.Char('Valor cobrado')
    codigo_distribuidor = fields.Char('Código de distribuuidor')
    cliente_nombre = fields.Char('Nombre del cliente')
    cliente_id = fields.Char('Código del cliente')
    vendedor_nombre = fields.Char('Nombre del vendedor')
    vendedor_id = fields.Char('Ientificación del vendedor')
    cargo_fijo_mensual = fields.Char('Cargo fijo mensual')
    permanencia_pendiente = fields.Char('Permanencia pendiente')
    clasificacion_del_plan = fields.Char('Claseificación del plan')
    es_multiplay = fields.Boolean('Es multiplay')
    es_upgrade = fields.Boolean('Es upgrade')
    es_linea_nueva = fields.Boolean('Es slínea nueva')
    es_venta_digital = fields.Boolean('Es venta digital')
    es_con_equipo = fields.Boolean('Es con equipo')
    es_telemercadeo = fields.Boolean('Es telemercadeo')
    fecha_de_activacion_en_punto_de_activacion = fields.Date('Fecha de activación')
    usuario_creador = fields.Char('Usuario creador')
    venta_id = fields.Char('Venta ID', help='ID de la venta en TIPS')
    plan_id = fields.Many2one('gestor.planes.team')
    meses = fields.Integer('Meses', help='Tiempo en meses desde la activación a la fecha del cruce')
    valor_a_pagar = fields.Float('Valor a pagar', help='Valor a pagar de la comisión al vendedor')
    estado_tips = fields.Char('Estado TIPS')
    empleado_id = fields.Many2one('hr.employee', index=True)
    categoria_empleado = fields.Char(string='Categoría Empleado', related='empleado_id.category_id.name', store=True)
    cargo = fields.Char(string='Cargo', related='empleado_id.job_id.name', store=True)
    responsable = fields.Many2one('hr.employee', string='Responsable ID', related='empleado_id.parent_id', store=True)
    responsable_nombre = fields.Char(related='responsable.name', string='Responsable', store=True)
    tipo_plan = fields.Char(string='Tipo de Plan',
                            related='plan_id.tipo_plan.name')
    categoria_tipo_plan = fields.Char(string='Categoría Plan',
                                      compute='_get_categoria_plan',
                                      store=True)
    year = fields.Integer('Año', compute='_get_year', store=True, group_operator=False)
    mes = fields.Char('Mes', compute='_get_month', store=True)
    presupuesto = fields.Integer(compute='_get_presupuesto', string='Preuspuesto', store=True, group_operator='avg')
    comision_pagada = fields.Char('Comisión Pagada')
    reconocimiento_pagado = fields.Char('Reconocimiento Pagado')
    tipo_de_activacion = fields.Char('Tipo de Activación')
    con_equipo = fields.Char('Con Equipo')
    cfm = fields.Char('CFM')
    cfm_con_iva = fields.Float('CFM con IVA', help='Valor a pagar por la venta según tabla')
    cfm_sin_iva = fields.Float('CFM con IVA', help='Valor a pagar sin IVA por la venta según tabla')
    mes_de_liquidacion = fields.Integer('Mes de liquidación')
    esquemas_ids = fields.Many2many('gestor.comisiones.team')

    def _get_costo_cfm(self):
        for registros in self:
            for detalle_precios in registros.env['gestor.precio.planes.team'].search([('name', '=', registros.plan_id.name)]).detalle_precios_planes_ids:
                raise ValidationError(detalle_precios)


class AltoValor(models.Model):
    _name = 'gestor.alto.valor.team'
    _description = 'Define el valor para alto valor'

    valor_inferior = fields.Integer('Valor inferior', help='Valor definido como tope inferior')
    valor_superior = fields.Integer('Valor superior', help='Valor definido como tope superior')


class RepositoriocomisionesTEAM(models.Model):
    _name = 'gestor.repositorio.comisiones.team'
    _description = 'Repositorio comisiones TEAM'
    _order = 'fecha_pago_comision desc, padre_id'

    hogar_id = fields.Many2one('gestor.captura.hogar.detalle.agrupado.team')
    padre_id = fields.Many2one('hr.employee', string='Padre', help='Valor a pagar a director o coordinador')
    vendedor = fields.Char(related='hogar_id.captura_hogar_id.id_asesor.name', string='Vendedor')
    valor_comision = fields.Float('Valor Comisión')
    esquema_id = fields.Many2one('gestor.comisiones.team')
    tipo_pago = fields.Selection([('valor', 'Por Valor Fijo'),
                                  ('porcentaje', 'Porcentaje')],
                                 related='esquema_id.tipo_pago')
    valor1 = fields.Float('Valor 1', related='esquema_id.mes1')
    planillas_hogar_id = fields.Integer('Planillas_id')
    planillas_biometrias_id = fields.Integer('biometrias_id')
    comision_pagada = fields.Boolean('Comisión Pagada', track_visibility='onchange')
    # fecha_pago_comision = fields.Date('Fecha de pago', track_visibility='onchange')
    usuario_pagador = fields.Many2one('res.users', string='Usuario Pagador', help='Usuario que proceso el pago', track_visibility='onchange')
    cuenta = fields.Char(related='hogar_id.captura_hogar_id.cuenta', string='Cuenta')
    ot = fields.Char(related='hogar_id.captura_hogar_id.ot', string='OT')
    fecha_pago_comision = fields.Date(string='Fecha pago comisión')
    fecha_venta = fields.Date(related='hogar_id.captura_hogar_id.fecha', string='Fecha Venta', store=True)
    biometrias_id = fields.Many2one('gestor.biometrias.team', string='Biometrias ID')
    referido_id = fields.Many2one('gestor.referidos.team', string='Referidos ID')

    categoria_padre = fields.Many2one('hr.employee.category', string='Categoría (Padre)')
    # departamento_padre = fields.Many2one('hr.department', related='padre_id.department_id', string='Departamento (Padre)', store=True)
    cargo_padre = fields.Many2one('hr.job', string='Cago (Padre)')
    sucursal_padre = fields.Many2one('gestor.sucursales', string='Sucursal (Padre)')

    pagar_a = fields.Many2one('hr.employee', string='Pagar a')
    categoria_pagar_a = fields.Many2one('hr.employee.category', string='Categoría (Pagar a)')
    cargo_pagar_a = fields.Many2one('hr.job', string='Cago (Pagar a)')
    sucursal_pagar_a = fields.Many2one('gestor.sucursales', string='Sucursal (Pagar a)')
    tarifa_especial_id = fields.Many2one('gestor.tarifas.especiales.hogar', string='Tarifa Especial')
    tipo_comision = fields.Selection([('comision','Comisión'),
                                      ('incentivo', 'Incentivo'),
                                      ('descuento', 'Descuento'),
                                      ('biometria', 'Biometría')
                                      ],
                                     related='esquema_id.tipo_comision',
                                     store=True
                                     )
    captura_id = fields.Many2one('gestor.captura.hogar.team', string='Captura')

    _sql_constraints = [('unq_repositorio_comisiones_team_hogar_id_padre_id', 'UNIQUE (hogar_id, padre_id, esquema_id)',
                         'La venta ya fue pagada a este empleado!')]


class TipoCondicionesComisionesTEAM(models.Model):
    _name = 'gestor.tipo.condiciones.comisiones.team'
    _description = 'Tipo de Condiciones para la liquidación de las condiciones'

    name = fields.Char('Condición')
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [('unq_condiciones_tipo_comisiones_team_name', 'UNIQUE (name)',
                         'La comisión ya existe!')]


class TipoRegistroCapturaTEAM(models.Model):
    _name = 'gestor.tipo.registro.captura.team'
    _description = 'Tipo de registro'

    name = fields.Selection([('Digitada', 'Digitada'),
                             ('Instalada', 'Instalada')
                             ]
                            )


class PrioridadesComisionesTEAM(models.Model):
    _name = 'gestor.prioridades.comisiones.team'
    _inherit = ['mail.thread']
    _description = 'Condiciones para la liquidación de las condiciones (Prioridades)'
    # cambiar nombre por gestor.prioridades.comisiones.team

    servicios_selection = [('Doble','Doble'),
                            ('Doble DTH','Doble DTH'),
                            ('FOX','FOX'),
                            ('FOX+','FOX+'),
                            ('FULLPACK FOX','FULLPACK FOX'),
                            ('GOLDEN PREMIER','GOLDEN PREMIER'),
                            ('HBO','HBO'),
                            ('HOTPACK','HOTPACK'),
                            ('Sencillo','Sencillo'),
                            ('Sencillo DTH','Sencillo DTH'),
                            ('Triple','Triple'),
                            ('Triple DTH','Triple DTH'),
                            ('ULTRA WIFI','ULTRA WIFI'),
                            ('ULTRAWIFI','ULTRAWIFI'),
                            ('WIN PREMIUM','WIN PREMIUM'),
                            ('WIN+ PREMIUM SD','WIN+ PREMIUM SD')
                           ]

    name = fields.Many2one('gestor.comisiones.team')
    sequence = fields.Integer('Secuencia')
    tarifas_especiales_ids = fields.Many2many('gestor.tarifas.especiales.hogar', 'gestor_prioridades_tarifas_especiales_rel', string='Tarifas Especiales', track_visibility='onchange')
    tarifas_especiales_count = fields.Integer('Cantidad TE', compute='_cantidad_tarifas_especiales', track_visibility='onchange')
    convergencia = fields.Selection([('si', 'Si'), ('no', 'No')], string='Convergencia', track_visibility='onchange')
    categoria_tipo_plan_ids = fields.Many2many('gestor.categoria.tipo.planes.team', 'gestor_prioridades_categorias_tipo_plan_rel', track_visibility='onchange')
    tipo_plan_ids = fields.Many2many('gestor.tipo.plan.team', string='Tipo de plan', track_visibility='onchange')
    planes_ids = fields.Many2many('gestor.planes.team', 'gestor_prioridades_planes_rel', string='Planes', track_visibility='onchange')
    planes_ex_ids = fields.Many2many('gestor.planes.team', 'gestor_prioridades_planes_ex_rel', string='Planes Excluidos',
                                     help='Estos planes no estarán dentro de este esquema de comisión.', track_visibility='onchange')
    employees_ids = fields.Many2many('hr.employee', string='Empleados', track_visibility='onchange')
    sucursal_ids = fields.Many2many('gestor.sucursales', string='Sucursal (Vendedor)', track_visibility='onchange')
    job_ids = fields.Many2many('hr.job', string='Cargo', track_visibility='onchange')
    servicios = fields.Selection(selection=servicios_selection, string='Servicios', track_visibility='onchange')
    tipo_pago = fields.Selection([('valor', 'Por Valor Fijo'),
                                  ('porcentaje', 'Porcentaje')], default='valor', track_visibility='onchange')
    valor_pago = fields.Float('Pago 1', track_visibility='onchange')
    limite_ventas_ids = fields.One2many('gestor.limites.venta', 'name', string='Limite de Ventas', help='Topes de ventas', track_visibility='onchange')
    estado_venta = fields.Many2many('gestor.estados_ap.team', string='Estado de la Venta',
                                    track_visibility='onchange',
                                    help='Estado de la venta para las biometrías'
                                    )
    tipo_referido = fields.Selection([('natural', 'Natural'), ('qr', 'QR')], track_visibility='onchange')
    active = fields.Boolean('Activo', default=True, track_visibility='onchange')
    # tipo_biometria = fields.Selection([('comercial', 'Comercial'), ('administrativa', 'Administrativa')], track_visibility='onchange', default='comercial')
    tipo_biometria = fields.Selection([('comercial', 'Comercial')], track_visibility='onchange')
    fecha_inicio = fields.Date('Fecha Inicio', help='Fecha inicio de vigencia de la prioridad', track_visibility='onchange')
    fecha_fin = fields.Date('Fecha Fin', help='Fecha Final de la vigencia de la prioridad (si esta vací asume la fecha actual).', track_visibility='onchange')
    tipo_registro = fields.Many2many('gestor.tipo.registro.captura.team', 'gestor_prioridades_tipo_registro_rel')
    distrito_ids = fields.Many2many('gestor.distritos', string='Distrito', track_visibility='onchange')

    @api.onchange('tarifas_especiales_ids')
    def _cantidad_tarifas_especiales(self):
        self.tarifas_especiales_count = len(self.tarifas_especiales_ids)


# ####################### Eliminar para la real
# class CondicionesComisionesTEAM(models.Model):
#     _name = 'gestor.condiciones.comisiones.team'
#     _inherit = ['mail.thread']
#     _description = 'Condiciones para la liquidación de las condiciones'
#     # cambiar nombre por gestor.prioridades.comisiones.team
#
#     servicios_selection = [('Doble','Doble'),
#                             ('Doble DTH','Doble DTH'),
#                             ('FOX','FOX'),
#                             ('FOX+','FOX+'),
#                             ('FULLPACK FOX','FULLPACK FOX'),
#                             ('GOLDEN PREMIER','GOLDEN PREMIER'),
#                             ('HBO','HBO'),
#                             ('HOTPACK','HOTPACK'),
#                             ('Sencillo','Sencillo'),
#                             ('Sencillo DTH','Sencillo DTH'),
#                             ('Triple','Triple'),
#                             ('Triple DTH','Triple DTH'),
#                             ('ULTRA WIFI','ULTRA WIFI'),
#                             ('ULTRAWIFI','ULTRAWIFI'),
#                             ('WIN PREMIUM','WIN PREMIUM'),
#                             ('WIN+ PREMIUM SD','WIN+ PREMIUM SD')
#                            ]
#
#     name = fields.Many2one('gestor.comisiones.team')
#     sequence = fields.Integer('Secuencia')
#     tarifas_especiales_ids = fields.Many2many('gestor.tarifas.especiales.hogar', 'gestor_prioridades_tarifas_especiales_rel', string='Tarifas Especiales')
#     tarifas_especiales_count = fields.Integer('Cantidad TE', compute='_cantidad_tarifas_especiales', track_visibility='onchange')
#     convergencia = fields.Selection([('si', 'Si'), ('no', 'No')], string='Convergencia')
#     categoria_tipo_plan_ids = fields.Many2many('gestor.categoria.tipo.planes.team', 'gestor_prioridades_categorias_tipo_plan_rel')
#     tipo_plan_ids = fields.Many2many('gestor.tipo.plan.team', 'gestor_prioridades_tarifas_tipo_plan_rel', string='Tipo de plan', track_visibility='onchange')
#     planes_ids = fields.Many2many('gestor.planes.team', 'gestor_prioridades_planes_rel', string='Planes', track_visibility='onchange')
#     planes_ex_ids = fields.Many2many('gestor.planes.team', 'gestor_prioridades_planes_ex_rel', string='Planes Excluidos',
#                                      help='Estos planes no estarán dentro de este esquema de comisión.')
#     sucursal_ids = fields.Many2many('gestor.sucursales', string='Sucursal (Vendedor)')
#     job_ids = fields.Many2many('hr.job', string='Cargo')
#     servicios = fields.Selection(selection=servicios_selection, string='Servicios', track_visibility='onchange')
#     tipo_pago = fields.Selection([('valor', 'Por Valor Fijo'),
#                                   ('porcentaje', 'Porcentaje')], default='valor')
#     valor_pago = fields.Float('Valor')
#     limite_ventas_ids = fields.One2many('gestor.limites.venta', 'name', string='Limite de Ventas', help='Topes de ventas', track_visibility='onchange')
#     active = fields.Boolean('Activo', default=True)
#
#     @api.onchange('tarifas_especiales_ids')
#     def _cantidad_tarifas_especiales(self):
#         self.tarifas_especiales_count = len(self.tarifas_especiales_ids)
