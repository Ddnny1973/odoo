from odoo import models, fields, api
from odoo.exceptions import ValidationError

import pymssql

import logging

_logger = logging.getLogger(__name__)

# 'server': 'team.soluciondigital.com.co',
param_dic = {
            'server': '20.119.218.50',
            'database': 'TipsII',
            'user': 'sa',
            'password': 'Soluciondig2015'
            }


def connect(params_dic):
    """ Connect to the PostgreSQL database server """
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


class ActualizarVentasTipsWizard(models.TransientModel):
    _name = "gestor.actualizar.ventas.wizard"
    _description = "Actualizar las Ventas en TIPS"

    fechas = fields.Boolean('Actualizar Fechas')
    plan = fields.Boolean('Actualizar Plan')
    actualizar_plan_especifico = fields.Boolean('Actualizar Plan Específico', help='Modifica TODAS las ventas seleccionadas a un plan TIPS específico')
    actualizar_plan_especifico_plan = fields.Many2one('gestor.planes.team')
    imei = fields.Boolean('Actualizar IMEI')
    min = fields.Boolean('Actualizar MIN')
    tipo_de_plan = fields.Boolean('Actualizar Tipo de Plan')
    actualizar_equipo = fields.Boolean('Actualizar Equipo')
    actualizar_tipo_linea = fields.Boolean('Actualizar Tipo Línea')
    ventas_ids = fields.One2many('gestor.cruce.ventas.tips', 'venta_id')
    filtro_plan = fields.Selection([('ok', 'ok'),
                                    ('no ok', 'No coincidente'),
                                    ('No coincidente plan choque', 'No coincidente plan choque'),
                                    ('Ok pero con error en tipo de Plan', 'Ok pero con error en tipo de Plan'),
                                    ('Venta no encontrada en RP', 'Venta no encontrada en RP')])
    filtro_tipo_plan = fields.Selection([('ok', 'ok'),
                                         ('no ok', 'No coincidente'),
                                         ('Tipo de plan No encontrado en RP', 'Tipo de plan No encontrado en RP')])

    filtro_imei = fields.Selection([('ok', 'ok'), ('no ok', 'No coincidente')])
    filtro_min = fields.Selection([('ok', 'ok'), ('no ok', 'No coincidente')])
    filtro_equipo = fields.Selection([('ok', 'ok'), ('no ok', 'No coincidente')])
    filtro_fecha = fields.Selection([('ok', 'ok'), ('no ok', 'No coincidente')])
    filtro_tipo_plan_rp = fields.Char('Tipo Plan RP', help='Ingrese el nombre que aparece en RP')
    plan_rp = fields.Many2one('gestor.lineas.planes.team', string='Tipo Plan RP', help='Ingrese el nombre que aparece en RP', )
    filtro_tipo_plan_rp_indefinido = fields.Boolean('Tipo Plan RP Indefinido', help='Si esta seleccionado traerá la información donde el Tipo de Plan en RP este Indefinido')
    filtro_tipo_plan_tips = fields.Many2many('gestor.tipo.plan.team', help='Ingrese el tipo de plan que aparece en TIPS')
    filtro_encontrado_rp = fields.Selection([('Encontrada', 'Encontrada'), ('No encontrada en RP', 'No encontrada en RP')])
    filtro_por_nombre_plan_tips = fields.Many2one('gestor.planes.team',
                                                  string='Plan TIPS',
                                                  help='Ingrese el nombre del plan que aparece en TIPS')
    filtro_nombre_plan_tips = fields.Many2many('gestor.planes.team', 'name',
                                              string='Excluir Planes TIPS',
                                              help='Ingrese el nombre del plan que aparece en TIPS que NO debe estar en la actualización')
    # filtro_nombre_plan_tips_2 = fields.Many2one('gestor.planes.team',
    #                                           string='Excluir Planes TIPS',
    #                                           help='Ingrese el nombre del plan que aparece en TIPS que NO debe estar en la actualización')
    aplicar = fields.Boolean('Aplicar Filtro', default=False)
    registros_count = fields.Integer(string='Cantidad de registros', compute='_registros_count')
    filtro_tipo_linea = fields.Many2one('gestor.tipo.lineas.planes.team')

    @api.onchange('plan_rp')
    def _get_plan_rp(self):
        self.filtro_tipo_plan_rp = self.plan_rp.name

    def action_update(self):
        prefijo = False
        # lineas_insertar = [('insert into @Ventas(Id,PlanId,Min,Iccid,Imei,Fecha,CoId,TipoDeActivacionId,EquipoId,TipoDeLineaId) VALUES ')]
        instruccion_insertar = 'Declare @Ventas dbo.TipsTduDatosParaCambioDeVentas; \ninsert into @Ventas(Id,PlanId,Min,Iccid,Imei,Fecha,CoId,TipoDeActivacionId,EquipoId,TipoDeLineaId,UsuarioModificadorId) VALUES \n'
        lineas_insertar = ''
        contador = 0
        # _logger.info('Registros a actualizar: ' + str(len(self.ventas_ids)))
        for registros in self.ventas_ids:
            # id_ventas = self.env['gestor.cruce.ventas.tips'].search([('id', '=', registros.id)])
            id_ventas = registros
            # _logger.info('Venta a actualizar: ' + str(id_ventas.venta_id_tips) + ' ID de la venta: ' + str(id_ventas.id) + ' Resgistro interno Venta_id: ' + str(id_ventas.venta_id))
            # raise ValidationError(plan_id)
            if self.plan:
                lineas_ids = self.env['gestor.lineas.planes.team'].search([('name', '=', registros.tipo_de_plan_rp)])
                if registros.nombre_plan_rp.find('-') > 0:
                    plan_tips = registros.nombre_plan_rp.split('-')
                    cod_plan = plan_tips[1].strip()

                    for tipo_plan_id in self.env['gestor.tipo.plan.team'].search([('linea_ids', '=', lineas_ids.id)]):
                        if tipo_plan_id.name.upper() in ('UPGRADE', 'UPGRADE ESPECIAL', 'UPGRADE SINERGIA'):
                            prefijo = 'Up'
                        elif tipo_plan_id.name.upper() in ('PORTACIÓN', 'PORTACION', 'PORTACION ESPECIAL', 'PORTACION SINERGIA'):
                            prefijo = 'PORTA'
                        else:
                            prefijo = ''
                    if prefijo == '':
                        # raise ValidationError('entró sin prefijo')
                        plan_id = self.env['gestor.planes.team'].search([('codigo', '=', cod_plan),
                                                                        ('name', 'not ilike', 'Up'),
                                                                        ('name', 'not ilike', 'PORTA'),
                                                                        ('activo', '=', True)])
                    else:
                        plan_id = self.env['gestor.planes.team'].search([('codigo', '=', cod_plan),
                                                                        # ('name', 'ilike', prefijo),
                                                                        ('activo', '=', True)])
                else:
                    if registros.nombre_plan_rp.upper().count('KIT') > 0:
                        if registros.nombre_plan_rp.upper().count('CONTADO') > 0:
                            plan_id = self.env['gestor.planes.team'].search([('name', 'ilike', 'Plan Kit Prepago'),
                                                                             ('activo', '=', True)])
                        elif registros.nombre_plan_rp.upper().count('FINANCIADO') > 0:
                            plan_id = self.env['gestor.planes.team'].search([('name', 'ilike', 'Kit prepago Financiado'),
                                                                             ('activo', '=', True)])
                        else:
                            raise ValidationError('No se pudo definir el código del plan en TIPS. \nPlan en RP: ' + registros.nombre_plan_rp)
                    elif registros.nombre_plan_rp.upper().count('REPO') > 0:
                        plan_id = self.env['gestor.planes.team'].search([('name', 'ilike', 'Reposicion 12 cuotas'),
                                                                         ('activo', '=', True)])
                    else:
                        raise ValidationError('No se pudo definir el código del plan en TIPS. \nPlan en RP: ' + registros.nombre_plan_rp)

                if len(plan_id) > 1:
                    nombre_planes = ''
                    for i in plan_id:
                        nombre_planes = i.name + ' \n' + nombre_planes
                    raise ValidationError('El plan aparaece repetido en TIPS: \n' + nombre_planes)
                # _logger.info(plan_id)
                # raise ValidationError(plan_id.codigo_id)
                id_ventas.write({'nombre_plan_tips': plan_id.name,
                                'plan_tips_id': plan_id.id})
            if self.fechas:
                id_ventas.write({'fecha_tips': registros.fecha_rp})
            if self.imei:
                id_ventas.write({'imei_tips': registros.imei_rp})
            if self.min:
                id_ventas.write({'min_tips': registros.min_rp})
            if self.actualizar_tipo_linea:
                # raise ValidationError(id_ventas.tipo_de_plan_rp)
                gestor_lineas_planes_team = self.env['gestor.lineas.planes.team'].search([('name', '=', id_ventas.tipo_de_plan_rp)])
                # gestor_tipo_lineas_planes_team = self.env['gestor.tipo.lineas.planes.team'].search([])
                # raise ValidationError(gestor_tipo_lineas_planes_team)
                id_tips = 'null'
                for i in self.env['gestor.tipo.lineas.planes.team'].search([]):
                    if gestor_lineas_planes_team.id in i.lineas_planes_ids.ids:
                        id_ventas.write({'tipo_linea': i.name})
                        id_tips = i.id_tips
            else:
                id_tips = 'null'
            if self.actualizar_equipo:
                equipo_stok_id = self.env['gestor.equipos.stock'].search([('name', '=', registros.equipo_stok)], limit=1)
                equipo_tips = self.env['gestor.equipos.tips'].search([('nombre_equipo_stock', 'in', equipo_stok_id.id)], limit=1)
                # if registros.min_tips == '3116070483':
                #     raise ValidationError(equipo_tips)
                id_ventas.write({'equipo': equipo_tips.id})
                if registros.equipo.id_tips == 0:
                    actualizar_equipo = 'null'
                else:
                    actualizar_equipo = str(registros.equipo.id_tips)
            else:
                actualizar_equipo = 'null'
            if self.min:
                id_ventas.write({'min_tips': registros.min_rp})
            # id_ventas.actualizar_venta_tips()
            # lineas_insertar += [('(' + str(30) + ',' +      # registros.ventas_ids.id
            #                     str(registros.plan_tips_id.codigo_id) +',' +
            #                     registros.min_tips+', null, ' + registros.imei_tips + ',' + str(registros.fecha_tips) + ', null, ' +
            #                     ', null, ' + str(25) + ')')]     # self.equipo.id_tips
            if contador == 0:
                coma = ''
            else:
                coma = ','
            contador += 1

            # Buscar usuario TIPSII del usuario que esta haciendo el cambio, sino tiene usuario TIPSII, detener proceso o colocar 0
            user_id = self.env.user.id
            empleado_id = self.env['hr.employee'].search([('user_id', '=', user_id)])
            usaurio_tips = empleado_id.user_id_tips or 0
            # raise ValidationError(usaurio_tips)
            lineas_insertar = lineas_insertar + coma + '(' + \
                                                       str(registros.venta_id_tips) + ',' + \
                                                       str(registros.plan_tips_id.codigo_id) + ',' + \
                                                       registros.min_tips + \
                                                       ', null, ' + \
                                                       registros.imei_tips + ',' + \
                                                       '\'' + str(registros.fecha_tips) + '\'' \
                                                       ', null, ' + \
                                                       'null, ' + \
                                                       actualizar_equipo + \
                                                       ', ' + str(id_tips) + \
                                                       ', ' + str(usaurio_tips) + \
                                                       ') \n'

        lineas_insertar = instruccion_insertar + lineas_insertar + ';\nExec pro_ext_Gtor_ModificarVentasMasivamente @Ventas;'
        # raise ValidationError(lineas_insertar)

        conn = connect(param_dic)
        cursor = conn.cursor()
        # raise ValidationError(lineas_insertar)
        cursor.execute(lineas_insertar)
        conn.commit()

    @api.depends('aplicar')
    def _registros_count(self):
        conteo = 0
        filtro = []
        filtro1 = []
        filtro2 = []
        filtro3 = []
        filtro4 = []
        filtro5 = []
        filtro6 = []
        filtro7 = []
        filtro8 = []
        filtro9 = []
        filtro10 = []
        filtro11 = []
        filtro12 = []
        filtro13 = []

        # Construyendo el filtro
        if self.filtro_plan == 'ok':
            filtro1 = [('revision_del_plan', '=', 'OK')]
        elif self.filtro_plan == 'no ok':
            filtro1 = [('revision_del_plan', '=', 'No coincidente')]
        elif self.filtro_plan == 'Ok pero con error en tipo de Plan':
            filtro1 = [('revision_del_plan', '=', 'Ok pero con error en tipo de Plan')]
        elif self.filtro_plan == 'Venta no encontrada en RP':
            filtro1 = [('revision_del_plan', '=', 'Venta no encontrada en RP')]
        elif self.filtro_plan == 'No coincidente plan choque':
            filtro1 = [('revision_del_plan', '=', 'No coincidente plan choque')]
        if self.filtro_tipo_plan == 'ok':
            filtro2 = [('revision_tipo_de_plan', '=', 'OK')]
        elif self.filtro_tipo_plan == 'no ok':
            filtro2 = [('revision_tipo_de_plan', '!=', 'OK')]
        if self.filtro_imei == 'ok':
            filtro3 = [('revision_imei', '=', 'OK')]
        elif self.filtro_imei == 'no ok':
            filtro3 = [('revision_imei', '!=', 'OK')]
        if self.filtro_min == 'ok':
            filtro4 = [('revision_min', '=', 'OK')]
        elif self.filtro_min == 'no ok':
            filtro4 = [('revision_min', '!=', 'OK')]
        if self.filtro_equipo == 'ok':
            filtro5 = [('revision_equipo', '=', 'OK')]
        elif self.filtro_equipo == 'no ok':
            filtro5 = [('revision_equipo', '!=', 'OK')]
        if self.filtro_fecha == 'ok':
            filtro6 = [('revision_fecha', '=', 'OK')]
        elif self.filtro_fecha == 'no ok':
            filtro6 = [('revision_fecha', '!=', 'OK')]
        if self.filtro_encontrado_rp == 'Encontrada':
            filtro12 = [('encontrada_rp', '=', 'Encontrada')]
        elif self.filtro_fecha == 'no ok':
            filtro12 = [('encontrada_rp', '!=', 'No encontrada en RP ')]
        if self.fechas:
            filtro7 = [('fecha_rp', '!=', False)]
        if self.filtro_tipo_plan_rp:
            filtro8 = [('tipo_de_plan_rp', '=', self.filtro_tipo_plan_rp.upper())]
        if self.filtro_tipo_plan_rp_indefinido:
            filtro8 = ['|', ('tipo_de_plan_rp', '=', False), ('tipo_de_plan_rp', '=', '')]
        if self.filtro_tipo_plan_tips:
            nombretiposPlanes = []
            for tipoplan in self.filtro_tipo_plan_tips:
                nombretiposPlanes.append(tipoplan.name)
            filtro9 = [('tipo_de_plan_tips', 'in', nombretiposPlanes)]
        if self.filtro_nombre_plan_tips:
            nombrePlanes = []
            for plan in self.filtro_nombre_plan_tips:
                nombrePlanes.append(plan.name)
            filtro10 = [('nombre_plan_tips', 'not in', nombrePlanes)]
        if self.filtro_por_nombre_plan_tips:
            filtro11 = [('plan_tips_id', '=', self.filtro_por_nombre_plan_tips.id)]
        if self.filtro_tipo_linea:
            filtro13 = [('tipo_linea', '=', self.filtro_tipo_linea.name)]

        filtro = filtro1 + filtro2 + filtro3 + filtro4 + filtro5 + filtro6 + filtro7 + filtro8 + filtro9 + filtro10 + filtro11 + filtro12 + filtro13
        # raise ValidationError(filtro)
        # coincidente,tipo_de_plan_rp,!=,true,tipo_de_plan_tips,in,Postpago,encontrada_rp,=,Encontrada
        # coincidente,tipo_de_plan_rp,!=,false,tipo_de_plan_tips,in,Postpago,encontrada_rp,=,Encontrada
        if filtro and self.aplicar:
            self.ventas_ids = self.env['gestor.cruce.ventas.tips'].search(filtro)
            # self.ventas_ids = self.env['gestor.cruce.ventas.tips'].search([('tipo_de_plan_tips', '=', 'Cesión')])
            conteo = len(self.ventas_ids)
            # raise ValidationError(filtro)
        self.registros_count = conteo

    def action_filtrar(self):
        self.ventas_ids = self.env['gestor.cruce.ventas.tips'].search([('revision_del_plan', '=', 'ok'),
                                                                       ('revision_tipo_de_plan', '!=', 'ok')])
        # raise ValidationError(len(self))
