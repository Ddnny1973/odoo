import logging
from pyexpat import model
from odoo import models, fields, api
from datetime import datetime, timedelta

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EstadoAntesDePago(models.Model):
    _name = 'gestor.estados_ap.team'
    _description = 'Estados antes del pago TEAM'

    name = fields.Char('Estado')
    comisiones_wz_id = fields.Integer('Planillas WZ', help='Planillas de liquidación hogar')

    _sql_constraints = [('unq_estado_ap_team_name', 'UNIQUE (name)',
                         'El Estado ya existe ya existe!')]


class EstadoPosterioAlPago(models.Model):
    _name = 'gestor.estados_pp.team'
    _description = 'Estados Posterior al pago TEAM'

    name = fields.Char('Estado')

    _sql_constraints = [('unq_estado_pp_team_name', 'UNIQUE (name)',
                         'El Estado ya existe!')]


estado_posterior_al_pago_claro_old = 1
#estado_posterior_al_pago_claro_old_name = None
#estado_pp_nombre = None


class CapturaHogar(models.Model):
    _name = 'gestor.captura.hogar.team'
    _inherit = ['mail.thread']
    _description = 'Captura Datos Hogar'

    def get_tarifa_especial(self):
        empleado_id = self.env['hr.employee'].search([('user_id', '=', self.vendedor.id)])
        fecha = self.fecha
        tarifa_especial_id = False
        if fecha:
            reg = self.env['gestor.tarifas.especiales.hogar.historico'].search([('empleado_id', '=', empleado_id.id),
                                                                                ('fecha_inicio', '<=', fecha)], limit=1)
            tarifa_especial_id = reg.name
        return tarifa_especial_id

    def get_categoria(self):
        empleado_id = self.env['hr.employee'].search([('user_id', '=', self.vendedor.id)])
        fecha = self.fecha
        categoria_id = empleado_id.category_id
        if fecha:
            reg = self.env['gestor.hr.categoria.historico'].search([('empleado_id', '=', empleado_id.id),
                                                                    ('fecha_inicio', '<=', fecha)], limit=1)
            if len(reg) > 0:
                categoria_id = reg.name
        return categoria_id

    name = fields.Integer('Nombre')
    cuenta = fields.Char('Cuenta', help='Número de cuenta', required=True, track_visibility='onchange')
    ot = fields.Char('OT', help='Orden de trabajo', required=True, track_visibility='onchange')
    fecha = fields.Date('Fecha', track_visibility='onchange')
    id_cliente = fields.Char('CC/NIT Cliente', help='Cédula / NIT', required=True)
    nombre_cliente = fields.Char('Nombre Cliente', help='Nombre del cliente', required=True)
    # estrato = fields.Selection([('1', '1'),
    #                             ('2', '2'),
    #                             ('3', '3'),
    #                             ('4', '4'),
    #                             ('5', '5'),
    #                             ('6', '6')])
    tel_cliente = fields.Char('Tel Cliente', help='Teléfono de contacto del cliente',required=True)  
    estado_venta = fields.Many2one('gestor.estados_ap.team',
                                   help='Estado de la venta antes del pago de Claro',
                                   track_visibility='onchange')
    idasesor = fields.Char('ID asesor', groups="base.group_user")
    nombreasesor = fields.Char('Nombre Asesor')
    cantserv = fields.Float('Cantidad de Servicios')
    area = fields.Char('Área')
    zona = fields.Char('Zona')
    poblacion = fields.Char('Población')
    d_distrito = fields.Char('Distrito')
    tercero = fields.Char('Tercero')
    punto = fields.Char('Punto')
    renta_global = fields.Char('Renta GLOBAL')
    grupo = fields.Char('Grupo')
    categoria = fields.Char('Categoría')
    fecha = fields.Date('Fecha')
    tipo_registro = fields.Char('Tipo de Registro', help='Digitado/Instalado', track_visibility='onchange')
    canal2 = fields.Char('Canal')
    no_contrato = fields.Char('N. contrato')
    estrato = fields.Char('estrato', readonly=True)
    paquete_global = fields.Char('Paquete GLOBAL')
    gv_area = fields.Char('GV Área')
    cod_tarifa = fields.Char('Cod. Tarifa')
    visor_movil = fields.Char('Visor Móvil')
    val_identidad = fields.Char('Val. Identidad')
    serial_captor = fields.Char('Serial Captor')
    estado_posterior_al_pago_claro = fields.Many2one('gestor.estados_pp.team', track_visibility='onchange')
    # estado_posterior_al_pago_claro_old = fields.Many2one('gestor.estados_pp.team')
    vendedor = fields.Many2one('res.users',
                               'Vendedor TEAM',
                               default=lambda self: self.env.user,
                               help='Vendedor que realiza la venta.',
                               track_visibility='onchange',
                               domain=['|', ('active', '=', True), ('active', '=', False)],
                               context={'active_test': False})
    detalle_captura_hogar_ids = fields.One2many('gestor.captura.hogar.detalle.team', 'captura_hogar_id')
    detalle_agrupado_captura_hogar_ids = fields.One2many('gestor.captura.hogar.detalle.agrupado.team', 'captura_hogar_id')
    id_responsable = fields.Many2one('hr.employee', string='Responsable')
    id_asesor = fields.Many2one('hr.employee',
                                index=True,
                                default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)]).id
                                )
    cargo = fields.Char(related='id_asesor.job_id.name', string='Cargo', store=True)
    # venta_convergente = fields.Boolean('Venta convergente', readonly=True)
    venta_convergente = fields.Char('Venta convergente', readonly=True)
    mintic = fields.Char('MINTIC/ESPECIAL', readonly=True)
    year = fields.Integer('Año')
    mes = fields.Char('Mes')
    digitador = fields.Many2one('res.users',
                                'Digitador TEAM',
                                default=lambda self: self.env.user,
                                help='Vendedor que realiza la venta.')
    referido = fields.Boolean('Referido')
    referido_existente = fields.Boolean('Referido Existente', default=False)
    cedula_referido = fields.Char('N. Identificación')
    nombre_referido = fields.Char('Nombre', help='Nombre completo')
    telefono_referido = fields.Char('N. Celular/Fijo', help='Teléfono de contacto')
    correo_referido = fields.Char('email', help='Correo electrónico de contacto')
    banco_referido = fields.Many2one('res.bank',
                                     help='Entidad bancaria.')
    tipo_cuenta_referido = fields.Selection([('ahorros', 'Ahorros'), ('corriente', 'Corriente')])
    tipo_referido = fields.Selection([('natural', 'Natural'), ('qr', 'QR')])
    cuenta_referido = fields.Char('N- Cuenta', help='Número de cuenta del referido donde se le va a realizar la consignación, el titular debe ser la misma cédula del referido')
    nombre_vendedor = fields.Char(related='id_asesor.name')
    identificacion_vendedor = fields.Char(related='id_asesor.identification_id', string='Identificación (Vendedor)', store=True)
    # categoria_vendedor = fields.Many2one('hr.employee.category', related='id_asesor.category_id', string='Categoría (Vendedor)', store=True)
    categoria_vendedor = fields.Many2one('hr.employee.category', string='Categoría (Vendedor)')
    departamento_vendedor = fields.Many2one('hr.department', related='id_asesor.department_id', string='Departamento (Vendedor)', store=True)
    cargo_vendedor = fields.Many2one('hr.job', related='id_asesor.job_id', string='Cargo (Vendedor)', store=True)
    sucursal_vendedor = fields.Many2one('gestor.sucursales', related='id_asesor.sucursal_id', string='Sucursal (Vendedor)', store=True)
    especial_hogar = fields.Boolean(related='id_asesor.especial_hogar', store=True)
    tarifa_especial_id = fields.Many2one('gestor.tarifas.especiales.hogar', string='Tarifa Especial')
    active = fields.Boolean('Activo', default=True, track_visibility='onchange')
    valor_comision = fields.Float('Valor comisión', default=0)
    comision_pagada = fields.Boolean('Comisión Pagada', track_visibility='onchange')
    fecha_pago_comision = fields.Date('Fecha de pago', track_visibility='onchange')
    usuario_pagador = fields.Many2one('res.users', string='Usuario Pagador', help='Usuario que proceso el pago', track_visibility='onchange')
    comision_liquidada = fields.Boolean('Comisión Liquidada', track_visibility='onchange')
    fecha_liquidacion_comision = fields.Date('Fecha de liquidación', track_visibility='onchange')
    usuario_liquidador = fields.Many2one('res.users', string='Usuario Liquidador', help='Usuario que proceso la liquidación', track_visibility='onchange')
    tipo_de_producto = fields.Char('Tipo de Producto')
    log_estados = fields.Text('Log cambios de estado')
    contar_servicios = fields.Integer('Conteo servicios', 
                                       help="Servicios prncipales, DTH y MINTIC del periodo")

    _sql_constraints = [('unq_captura_hogar_team_cuenta_ot', 'UNIQUE (cuenta, ot)',
                         'La cuenta y la OT ya estan ingresadas, por favor verifique!')]

    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('name', False):
                # Only goes off when the custom_search is in the context values.
                name = str(record.name)
                result.append((record.id, "{}".format(name)))
            else:
                ot = str(record.ot)
                result.append((record.id, ot))
        return result

    @api.onchange('cedula_referido')
    def get_referido(self):
        # raise ValidationError(self.cedula_referido)
        for reg in self:
            referido_id = reg.env['gestor.referidos.team'].search([('name', '=', reg.cedula_referido)])
            if referido_id:
                reg.nombre_referido = referido_id.nombre_referido
                reg.telefono_referido = referido_id.telefono_referido
                reg.correo_referido = referido_id.correo_referido
                reg.banco_referido = referido_id.banco_referido
                reg.tipo_cuenta_referido = referido_id.tipo_cuenta_referido
                reg.cuenta_referido = referido_id.cuenta_referido
                reg.referido_existente = True
            else:
                reg.nombre_referido = None
                reg.telefono_referido = None
                reg.correo_referido = None
                reg.banco_referido = None
                reg.tipo_cuenta_referido = None
                reg.cuenta_referido = None
                reg.referido_existente = False

    @api.constrains('id_cliente', 'tel_cliente', 'cuenta', 'ot')
    def _valida_campos(self):
        if self.id_cliente:
            try:
                x = float(self.id_cliente)
            except Exception as e:
                raise ValidationError('EL campo de ID Cliente solo debe contener dígitos numéricos, por favor verifique! \nEn caso de ser un NIT ingresarlo sin dígito de verificación.')
        if self.tel_cliente:
            try:
                x = float(self.tel_cliente)
            except Exception as e:
                raise ValidationError('EL campo de Teléfono solo debe contener dígitos numéricos, por favor verifique!\nUse el siguiente formato de telefono 9999999999')
        if self.cuenta:
            try:
                x = float(self.cuenta)
            except Exception as e:
                raise ValidationError('EL campo de Cuenta solo debe contener dígitos numéricos, por favor verifique!')
        if self.ot:
            try:
                x = int(self.ot)
            except Exception as e:
                raise ValidationError('EL campo de OT solo debe contener dígitos numéricos, por favor verifique!')

    # @api.constrains('vendedor')
    @api.onchange('vendedor')
    def get_responsable(self):
        if self.vendedor:
            for reg in self:
                empleado = reg.env['hr.employee'].with_context(active_test=False).search([('user_id', '=', reg.vendedor.id)])
                reg.id_responsable = empleado.parent_id.id
                reg.nombreasesor = empleado.name
                reg.id_asesor = empleado.id
                reg.tarifa_especial_id = self.get_tarifa_especial()
                reg.categoria_vendedor = self.get_categoria()

    def _actualizar_usuarios(self):
        # Actualiza el usuario creador de acuerdo al vendedor existente.
        self.env.cr.execute("""update gestor_captura_hogar_team set create_uid=vendedor where vendedor!=create_uid;""")
        self.env.cr.execute("""update gestor_captura_pyme_team set create_uid=vendedor where vendedor!=create_uid;""")

    def _actualizaciones_automaticas_biometrias(self):
        # Actualiza diferentes datos de las ventas
        self.env.cr.execute("""select actualizaciones_automaticas();""")
        self.env.cr.execute("""select actualizaciones_automaticas_recalculo_adicionales();""")

    def _actualizar_recalculos(self):
        # Recalcula ventas pendientes
        # self.env.cr.execute("""select actualizaciones_automaticas_recalculo();""")
        self.env.cr.execute("""select  f_recalcular_liquidacion_comisiones_hogar(ot, cuenta)
                               from gestor_captura_hogar_team a
                               where (a.ot, a.cuenta) in (select ot, cuenta from gestor_hogar_team)
                               and id not in (select captura_hogar_id from gestor_captura_hogar_detalle_agrupado_team where captura_hogar_id is not null);
                            """)

    def _actualizar_recalculos_nulos(self):
        # Recalcula ventas pendientes que no cargan detalle agrupado
        # self.env.cr.execute("""select actualizaciones_automaticas_recalculos_nulos();""")
        self.env.cr.execute("""select  f_recalcular_liquidacion_comisiones_hogar(a.ot, a.cuenta)
                                from gestor_captura_hogar_team a
                                where a.id not in (select captura_hogar_id from gestor_captura_hogar_detalle_agrupado_team where captura_hogar_id is not null)
                                and a.fecha >'2022-06-01';
                            """)
        
    def _actualizaciones_post_load(self):
        # Recalcula ventas pendientes
        # self.env.cr.execute("""select actualizaciones_automaticas_recalculo();""")
        self.env.cr.execute("""REFRESH MATERIALIZED VIEW v_recursividad_inversa WITH DATA;
                               REFRESH MATERIALIZED VIEW v_recursividad_inversa_historico WITH DATA;
                               REFRESH MATERIALIZED VIEW v_conteo_registros_vinculados_zonificacion WITH DATA;
                            """)

    def _actualizaciones_vistasmaterializadas(self):
        self.env.cr.execute("""select actualizaciones_post_load();""")

    @api.onchange('estado_venta')
    def _actualiza_estado_ap(self):
        for cuentas_hogar_ids in self.env['gestor.hogar.team'].search([('ot', '=', self.ot),
                                                                       ('cuenta', '=', self.cuenta)]
                                                                      ):
            cuentas_hogar_ids.estado_ap = self.estado_venta

    # @api.onchange('ot', 'cuenta')
    @api.constrains('ot', 'cuenta')
    def get_user(self):
        # self.vendedor = self.env.user
        if self.env.user and self.ot:
            # se debe usar el histórico
            empleado = self.env['hr.employee'].search([('user_id', '=', self.vendedor.id)])
            self.idasesor = empleado.identification_id
            # raise ValidationError(self.fecha)
            responsable_historico = self.env['hr.responsable.historico'].search([('empleado_id', '=', empleado.id)])
            responsable_id = None
            for i in responsable_historico:
                fecha_fin = i.fecha_fin or fields.Date.today()
                fecha_inicio = i.fecha_inicio or fields.Date.today()
                fecha = self.fecha or fields.Date.today()
                if fecha >= fecha_inicio and fecha <= fecha_fin:
                    responsable_id = i.name
            self.id_responsable = responsable_id or empleado.parent_id.id
            self.nombreasesor = empleado.name
            self.id_asesor = empleado.id
            # Buscando información de la OT
            if self.ot and self.cuenta:
                ot = self.ot
                cuenta = self.cuenta
                self.env.cr.execute("""select * from gestor_v_hogar
                                        where ot=%s and cuenta=%s
                                        order by fecha desc
                                        limit 1
                                    """,
                                    (self.ot, self.cuenta))
                if self.env.cr.rowcount > 0:
                    # registros_ids = self.env.cr.dictfetchall()
                    for registros in self.env.cr.dictfetchall():
                        self.paquete_global = registros['paquete_global']
                        self.tipo_registro = registros['tipo_registro']
                        self.venta_convergente = registros['venta_convergente']
                        self.mintic = registros['mintic']
                        self.tercero = registros['tercero']
                        self.punto = registros['punto']
                        self.grupo = registros['grupo']
                        self.categoria = registros['categoria']
                        self.canal2 = registros['canal2']
                        self.cantserv = registros['cantserv']
                        self.punto = registros['punto']
                        self.area = registros['area']
                        self.zona = registros['zona']
                        self.d_distrito = registros['d_distrito']
                        self.poblacion = registros['poblacion']
                        self.renta_global = registros['renta_global']
                        self.no_contrato = registros['no_contrato']
                        self.estrato = registros['estrato']
                        self.gv_area = registros['gv_area']
                        self.cod_tarifa = registros['cod_tarifa']
                        self.visor_movil = registros['visor_movil']
                        self.serial_captor = registros['serial_captor']
                        self.estado_venta = registros['estado_venta']
                        self.detalle_captura_hogar_ids.mintic = registros['mintic']
                        self.fecha = registros['fecha']   # fields.Date.today()
                        self.estrato = registros['estrato']
                        if registros['estado_ap']:
                            self.estado_venta = registros['estado_ap']
                        else:
                            tipo_registro = registros['tipo_registro']
                            # raise ValidationError(tipo_registro)

                    #####################
                    # Este código se reemplaza por las actualizaciones automáticas que se ejecutan cada 5 minutos
                    # capturas_ = self.env['gestor.captura.hogar.team'].search([('cuenta', '=', cuenta)])
                    # if len(capturas_) == 1:
                    #     biometrias_ = self.env['gestor.biometrias.team'].search([('name', '=', cuenta)], limit=1)
                    #     biometrias_.captura = capturas_.id
                    #     biometrias_.existe_gestor = True
                    #####################
                else:
                    self.paquete_global = False
                    self.tipo_registro = False
                    self.venta_convergente = False
                    self.mintic = False
                    self.tercero = False
                    self.punto = False
                    self.grupo = False
                    self.categoria = False
                    self.canal2 = False
                    self.cantserv = False
                    self.punto = False
                    self.area = False
                    self.zona = False
                    self.d_distrito = False
                    self.poblacion = False
                    self.renta_global = False
                    self.no_contrato = False
                    self.estrato = False
                    self.gv_area = False
                    self.cod_tarifa = False
                    self.visor_movil = False
                    self.serial_captor = False
                    self.estado_venta = False
                    self.detalle_captura_hogar_ids.mintic = False
                    self.fecha = False
                    self.estrato = False
            
            
            
    @api.constrains('name', 'cedula_referido')
    def _grabar_referido(self):
        # Creando nuevo referido
        for reg in self:
            if reg.referido_existente is False and reg.referido:
                referido_new = []
                # raise ValidationError('Entró. Referido existente: ' + str(reg.referido_existente))
                if reg.env['gestor.referidos.team'].search_count([('name', '=', reg.cedula_referido)]) == 0:
                    referido_new.append({'name': reg.cedula_referido,
                                         'nombre_referido': reg.nombre_referido.capitalize(),
                                         'telefono_referido': reg.telefono_referido,
                                         'correo_referido': reg.correo_referido.lower(),
                                         'banco_referido': reg.banco_referido.id,
                                         'tipo_cuenta_referido': reg.tipo_cuenta_referido,
                                         'cuenta_referido': reg.cuenta_referido,
                                         })
                    # raise ValidationError(referido_new)
                    new_id = reg.env['gestor.referidos.team'].create(referido_new)

                    esquema_id = reg.env['gestor.comisiones.team'].search([('all_referidos', '=', True)])
                    # raise ValidationError(esquema_id.id)
                    esquema_id.referidos_ids = esquema_id.referidos_ids + new_id

    def recalcular_liquidacion_comisiones(self):
        # raise ValidationError('Entró. OT: %s, Cuenta: %s' % (self.ot, self.cuenta))
        self.env.cr.execute("""
                                select f_recalcular_liquidacion_comisiones_hogar(%s, %s)
                            """,
                            (self.ot, self.cuenta))

    def mantenimiento_repositorio(self):
        # raise ValidationError('Entró. OT: %s, Cuenta: %s' % (self.ot, self.cuenta))
        self.env.cr.execute("""
                                select mantenimiento_repositorio()
                            """)
        # self.env.cr.commit()

    def pagar_liquidacion_comisiones(self):
        # raise ValidationError(datetime.now().date())
        if self.valor_comision > 0:
            self.comision_pagada = True
            self.fecha_pago_comision = datetime.now().date()
            self.usuario_pagador = self.env.user
            self.estado_posterior_al_pago_claro = 1

    def liquidacion_comisiones(self):
        # raise ValidationError(datetime.now().date())
        if self.valor_comision > 0:
            self.comision_liquidada = True
            self.fecha_liquidacion_comision = datetime.now().date()
            self.usuario_liquidador = self.env.user
            
    
        
  
# self.task_id.message_post(subject="Field value in One2many Changed", body=body, message_type='comment', author_id= self.env.user.partner_id.id)
# body should be like this : body = "Field Name : Old Value --> New Value"
    
    @api.onchange('estado_posterior_al_pago_claro')
    def _ol_values(self):

        global estado_posterior_al_pago_claro_old
        global estado_posterior_al_pago_claro_old_name
        global estado_pp_nombre
        
        estado_posterior_al_pago_claro_old = self._origin.estado_posterior_al_pago_claro.id or None
        estado_posterior_al_pago_claro_old_name = self.env['gestor.estados_pp.team'].search([('id', '=', estado_posterior_al_pago_claro_old)])
        estado_pp_nombre =estado_posterior_al_pago_claro_old_name.name
        #raise ValidationError(estado_pp_nombre)
    
    @api.constrains('estado_posterior_al_pago_claro')
    def generar_descuento(self):
        descuentos = []
        
        global estado_posterior_al_pago_claro_old
        global estado_posterior_al_pago_claro_old_name
        global estado_pp_nombre
               
        estado_posterior_al_pago_claro_old = estado_posterior_al_pago_claro_old
        estado_posterior_al_pago_claro_old_name = self.env['gestor.estados_pp.team'].search([('id', '=', estado_posterior_al_pago_claro_old)])
        estado_pp_nombre = estado_posterior_al_pago_claro_old_name.name
        #raise ValidationError(estado_pp_nombre)
        # raise ValidationError('Paso 001')
        for reg in self:
            
            tipo_descuento = reg.env['tipo.descuento'].search([('name', '=', 'Ajustes')])
            descuento_existente_id = reg.env['descuentos.teams'].search([('num_factura', '=', 'Ajuste - ' + reg.ot)])
            descuento_existente_id_repo = reg.env['descuentos.teams'].search([('num_factura', '=', 'Ajuste Repositorio - ' + reg.ot)])
            descuento_existente_id_dev = reg.env['descuentos.teams'].search([('num_factura', '=', 'Ajuste Reintegro - ' + reg.ot)])
            descuento_existente_id_repo_dev = reg.env['descuentos.teams'].search([('num_factura', '=', 'Ajuste Reintegro Repositorio - ' + reg.ot)])
            # raise ValidationError('Paso 002')
            # raise ValidationError(descuento_existente_id)
            if (not estado_posterior_al_pago_claro_old or estado_posterior_al_pago_claro_old == 1) and reg.estado_posterior_al_pago_claro.id > 1:
                # raise ValidationError('Paso 003')
                if descuento_existente_id:
                    descuento_existente_id.concepto = 'Ajuste por cambio de estado posterior al pago: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')'
                elif descuento_existente_id_repo:
                    descuento_existente_id_repo.concepto = 'Ajuste por cambio de estado posterior al pago repositorio: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')'
                if descuento_existente_id:
                    descuento_existente_id_dev.concepto = 'Ajuste por cambio de estado posterior al pago, devolución: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')'
                elif descuento_existente_id_repo:
                    descuento_existente_id_repo_dev.concepto = 'Ajuste por cambio de estado posterior al pago repositorio, devolución: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')'

                else:
                    descuentos.append({'name': reg.id_asesor.id,
                                       'tipodeprestamo': tipo_descuento.id,
                                       'valoraplicar': -reg.valor_comision,
                                       'valorprestamo': -reg.valor_comision,
                                       'valorcuota': -reg.valor_comision,
                                       'fecha_aplicacion': fields.Date.today(),
                                       # 'num_factura': 'Ajuste - ' + reg.estado_posterior_al_pago_claro.name + ' - ' + reg.ot,
                                       'num_factura': 'Ajuste - ' + reg.ot,
                                       'concepto': 'Ajuste por cambio de estado posterior al pago: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')',
                                       'cuotas': 1,
                                       })
                    # buscando incetivos pagados
                    for i in self.env['gestor.repositorio.comisiones.team'].search([('captura_id', '=', reg.id),
                                                                          ('tipo_comision', 'in', ('comision', 'incentivo'))
                                                                          ]):
                        descuentos.append({'name': i.padre_id.id,
                                           'tipodeprestamo': tipo_descuento.id,
                                           'valoraplicar': -i.valor_comision,
                                           'valorprestamo': -i.valor_comision,
                                           'valorcuota': -i.valor_comision,
                                           'fecha_aplicacion': fields.Date.today(),
                                           # 'num_factura': 'Ajuste - ' + reg.estado_posterior_al_pago_claro.name + ' - ' + reg.ot,
                                           'num_factura': 'Ajuste repositorio - ' + reg.ot,
                                           'concepto': 'Ajuste por cambio de estado posterior al pago: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')',
                                           'cuotas': 1,
                                           })
                    reg.env['descuentos.teams'].create(descuentos)
                    # raise ValidationError('Paso 009, descuento creado: ' + 'Ajuste repositorio (' + str(i.id)+ ') - ' + reg.ot)
            elif (descuento_existente_id and not descuento_existente_id_dev) and (reg.estado_posterior_al_pago_claro.id == 1 or reg.estado_posterior_al_pago_claro.id is False):
                
                descuentos.append({'name': reg.id_asesor.id,
                                   'tipodeprestamo': tipo_descuento.id,
                                   'valoraplicar': reg.valor_comision,
                                   'valorprestamo': reg.valor_comision,
                                   'valorcuota': reg.valor_comision,
                                   'fecha_aplicacion': fields.Date.today(),
                                   'num_factura': 'Ajuste Reintegro - ' + reg.ot,
                                   #'concepto': 'Ajuste por reintegro de estado posterior al pago: ' + reg.estado_posterior_al_pago_claro.name + ' --> a Normal ' + reg.cuenta + '(' + reg.ot + ')',
                                   'concepto': 'Ajuste por reintegro de estado posterior al pago: ' + estado_pp_nombre + ' a Normal --> ' + reg.cuenta + '(' + reg.ot + ')',
                                   #'concepto': 'Ajuste por reintegro de estado posterior al pago: a Normal --> ' + reg.cuenta + '(' + reg.ot + ')',
                                   'cuotas': 1,
                                   })
                # Devolución repositorio
                for i in self.env['gestor.repositorio.comisiones.team'].search([('captura_id', '=', reg.id),
                                                                      ('tipo_comision', 'in', ('comision', 'incentivo'))
                                                                      ]):
                    
                    if descuento_existente_id_repo:
                        #raise ValidationError(descuento_existente_id_repo)
                        descuentos.append({'name': i.padre_id.id,
                                        'tipodeprestamo': tipo_descuento.id,
                                        'valoraplicar': i.valor_comision,
                                        'valorprestamo': i.valor_comision,
                                        'valorcuota': i.valor_comision,
                                        'fecha_aplicacion': fields.Date.today(),
                                        # 'num_factura': 'Ajuste - ' + reg.estado_posterior_al_pago_claro.name + ' - ' + reg.ot,
                                        'num_factura': 'Ajuste reintegro repositorio - ' + reg.ot,
                                        'concepto': 'Ajuste por cambio de estado posterior al pago: ' + (estado_pp_nombre) + ' --> ' + reg.cuenta + '(' + reg.ot + ')',
                                        'cuotas': 1,
                                        })
                reg.env['descuentos.teams'].create(descuentos)
            else:
                if descuento_existente_id and reg.estado_posterior_al_pago_claro.id > 1:
                    descuento_existente_id.concepto = 'Ajuste por cambio de estado posterior al pago: ' + reg.estado_posterior_al_pago_claro.name + ' --> ' + reg.cuenta + '(' + reg.ot + ')'


class CapturaHogarDetalle(models.Model):
    _name = 'gestor.captura.hogar.detalle.team'
    _inherit = ['mail.thread']
    _description = 'Captura el detalle de Datos Hogar'
    _order = 'venta'

    captura_hogar_id = fields.Many2one('gestor.captura.hogar.team')
    fecha = fields.Char('Fecha')
    tipored = fields.Char('Tipo Red')
    division = fields.Char('División')
    renta = fields.Char('Renta')
    venta = fields.Char('Venta')
    paquete = fields.Char('Paquete')
    paquete_pg = fields.Char('Paquete PG')
    paquete_pvd = fields.Char('Paquete PVD')
    cod_campana = fields.Char('Cod. Campaña')
    mintic = fields.Char('MINTIC')
    tipo_de_producto = fields.Char('Tipo de producto')
    tipo_plan_id = fields.Many2one('gestor.tipo.plan.team')  # domain --> tipo_producto='Hogar'
    estrato_claro = fields.Integer('Estrato Claro', help='Estrato reportado por Claro')
    cod_tarifa = fields.Many2one('gestor.codigo.tarifa.hogar')
    petar = fields.Char('PETAR', related='cod_tarifa.petar')
    valor_comision = fields.Float('Valor comisión')
    servicio = fields.Char('Servicio', related='cod_tarifa.servicio')
    serviciointernet_id = fields.Many2one('gestor.servicios.internet.team', string='Servicios de Internet')
    # tipo_plan_modificado_id = fields.Many2one('gestor.tipo.plan.team')


class CapturaHogarResumenPago(models.Model):
    _name = 'gestor.captura.hogar.detalle.agrupado.team'
    _description = 'Detalle Captura Hogar Agrupado'
    _rec_name = 'captura_hogar_id'
    _inherit = ['mail.thread']

    captura_hogar_id = fields.Many2one('gestor.captura.hogar.team')
    tipo_plan = fields.Many2one('gestor.tipo.plan.team')
    renta_total = fields.Float('Renta')
    estrato_claro = fields.Integer('Estrato Claro', help='Estrato reportado por Claro') # desde aquí
    cod_tarifa = fields.Many2one('gestor.codigo.tarifa.hogar', required='True', index=True)
    petar = fields.Char('PETAR', related='cod_tarifa.petar')
    valor_comision = fields.Float('Valor comisión')
    servicio = fields.Char('Servicio')
    base_liquidacion_id = fields.Many2one('gestor.base.liquidacion.hogar', string='Base')
    # convergencia = fields.Char('Convergencia', related='base_liquidacion_id.convergencia')
    # convergencia = fields.Char('Convergencia', related='cod_tarifa.convergencia')
    convergencia = fields.Char('Convergencia', related='captura_hogar_id.venta_convergente')
    comision_claro = fields.Float('% Comisión claro', related='base_liquidacion_id.comision_claro')
    comision_team = fields.Float('% Comisión TEAM', related='base_liquidacion_id.comision_team')
    tipo_cobro = fields.Selection(([('porcentaje', 'Porcentaje'),
                                   ('fijo', 'Fijo'),
                                   ('fijo mintic', 'Fijo MINTIC'),
                                   ('porcentaje mintic', 'Porcentaje MINTIC')]),
                                  related='base_liquidacion_id.tipo_cobro')
    detalle_agrupado_hogar_id = fields.Integer('Detalle_id')
    planillas_hogar_id = fields.Integer('planillas_hogar_id')
    # comision_director = fsields.Float('Director', compute='busqueda_esquema_comision')
    comision_padre = fields.Float('Padre', help='Valor de comisi{on correspondiente al empleado analizado con todos sus hijos}')
    comision_liquidada = fields.Boolean('Comisión Liquidada', track_visibility='onchange', default=False)
    fecha_liquidacion_comision = fields.Date('Fecha de liquidación', track_visibility='onchange')
    usuario_liquidador = fields.Many2one('res.users', string='Usuario Liquidador', help='Usuario que proceso la liquidación', track_visibility='onchange')
    comision_pagada = fields.Boolean('Comisión Pagada', track_visibility='onchange', default=False)
    fecha_pago_comision = fields.Date('Fecha de pago', track_visibility='onchange')
    usuario_pagador = fields.Many2one('res.users', string='Usuario Pagador', help='Usuario que proceso el pago', track_visibility='onchange')
    name_wz = fields.Integer('WZ')
    ot = fields.Char(string='OT', related='captura_hogar_id.ot', store=True)
    cuenta = fields.Char(string='Cuenta', related='captura_hogar_id.cuenta', store=True)
    estado_venta = fields.Many2one('gestor.estados_ap.team',
                                   help='Estado de la venta antes del pago de Claro',
                                   related='captura_hogar_id.estado_venta', track_visibility='onchange')
    vendedor = fields.Many2one('res.users', related='captura_hogar_id.vendedor', store=True)
    fecha_captura = fields.Date(string='Fecha', related='captura_hogar_id.fecha', store=True)
    tiene_descuento = fields.Boolean(string='Descuentos', help='Valida si tiene saldos para descontar', compute='_valida_descuentos', store=True)
    tiene_descuento_tmp = fields.Boolean(string='Descuentos', help='Valida si tiene saldos para descontar', compute='_valida_descuentos')
    paquete_pvd = fields.Char('Paquete PVD')
    estado_venta_2 = fields.Many2one('gestor.estados_ap.team',
                                   help='Estado de la venta antes del pago de Claro',
                                   related='captura_hogar_id.estado_venta', track_visibility='onchange')
    convergencia_pagada = fields.Char('Convergencia pagada')
    serviciointernet_id = fields.Many2one('gestor.servicios.internet.team', string='Servicios de Internet')
    contar_servicios = fields.Integer('Conteo servicios', 
                                       help="Servicios prncipales y mintic")

    _sql_constraints = [('unq_captura_hogar_detalle_agrupado_', 'UNIQUE (captura_hogar_id, tipo_plan, servicio, cod_tarifa, renta_total)',
                         'La cuenta y la OT ya estan ingresadas, por favor verifique!')]

    def _contar_servicios(self):
        for reg in self:
            fecha = reg._origin.captura_hogar_id.fecha.strftime('%Y-%m-%d')
            inicio_mes = reg._origin.captura_hogar_id.fecha.strftime('%Y-%m-01')
            year = reg._origin.captura_hogar_id.fecha.strftime('%Y')
            mes = reg._origin.captura_hogar_id.fecha.strftime('%m')
            vendedor = reg._origin.captura_hogar_id.id_asesor.id
            cuenta = reg._origin.cuenta

            # reg.env.cr.execute("select sum(case when servicio='Sencillo' then 1 when servicio='Doble' then 2 when servicio='Triple' then 3 else 0 end ) as servicios from v_ventas_recursivas_para_conteo where vendedor = " + str(vendedor) + " and extract(YEAR FROM fecha) = " + str(year) + " and extract(MONTH FROM fecha) = " + str(mes))
            # res = self.env.cr.fetchone()
            # servicios = res[0]
            reg.contar_servicios = 9999 #servicios
    
    def liquidacion_comisiones(self):
        # raise ValidationError(datetime.now().date())
        if self.valor_comision > 0:
            self.comision_liquidada = True
            self.fecha_liquidacion_comision = datetime.now().date()
            self.usuario_liquidador = self.env.user

    def _valida_descuentos(self):
        for reg in self:
            if reg.env['descuentos.teams'].search_count([('name', '=', reg.captura_hogar_id.id_asesor.ids)]) > 0:
                reg.tiene_descuento = True
                reg.tiene_descuento_tmp = True
            else:
                reg.tiene_descuento = False
                reg.tiene_descuento_tmp = False

    def busqueda_esquema_comision_padre(self, padre):
        for reg in self:
            lf_precio = 0
            # li_empleado = self.vendedor.id
            # lc_tipo_plan = self.tipo_plan
            # lc_mintic = self.mintic

            ln_tiene_mintic = reg.env['gestor.comisiones.team'].search_count([('employees_ids', 'in', (padre)),
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
                comisiones = reg.env['gestor.comisiones.team'].search([('employees_ids', 'in', (padre)),
                                                                        ('tipo_plan_ids', 'in', (41))
                                                                        ])
                lf_precio = comisiones.mes1
            else:
                comisiones = reg.env['gestor.comisiones.team'].search([('employees_ids', 'in', (padre)),
                                                                        ('tipo_plan_ids', 'in', (reg.tipo_plan.id))
                                                                        ])
                lf_precio = comisiones.mes1
            _logger.info('A pagar por registro: ' + str(lf_precio))
            # raise ValidationError(padre)
            reg.comision_padre = lf_precio


class HogarTEAM(models.Model):
    _name = 'gestor.hogar.team'
    _inherit = ['mail.thread']
    _description = 'Claro Hogar TEAM'

    name = fields.Char('Orden', help='Orden de venta')
    cuenta = fields.Char('Cuenta', help='Orden de venta')
    ot = fields.Char('OT')
    idasesor = fields.Char('ID Asesor', help='Asesor Claro')
    nombreasesor = fields.Char('Nombre Asesor', help='Nombre asesor Claro')
    vendedor_id = fields.Many2one('hr.employee', string='Vendedor')
    paquete = fields.Char('Paquete', help='Paquete Claro')
    producto_id = fields.Many2one('product.product', help='Paquete vendido TEAM')
    estrato_claro = fields.Char('Estrato Claro', help='Estrato reportado por Claro')
    cantserv = fields.Char('Cant. Serv. Claro', help='Cantidad de servicios reportados por CLARO')
    cant_servicios = fields.Char('Cantidad de Servicios', help='Cantidad de servicios de la venta')
    tipo_red = fields.Char('Tipo Red', help='Tipo de RED reportada por Claro. Ej. FTT, BIDIRECCIONAL')
    division = fields.Char('División')
    area = fields.Char('Àrea')
    zona = fields.Char('Zona')
    poblacion = fields.Char('Población')
    d_distrito = fields.Char('Distrito')
    tercero = fields.Char('Tercero Punto')
    punto = fields.Char('Punto')
    renta = fields.Char('Renta')
    grupo = fields.Char('Grupo')
    categoria = fields.Char('Categoría')
    # fecha = fields.Char('Fecha')
    fecha = fields.Date('Fecha', help='Fecha reportada por Claro')
    fecha_venta = fields.Date('Fecha Venta', help='Fecha reportada por Claro')
    # venta = fields.Char('Venta')
    venta = fields.Char('Venta', help='Venta reportada por Claro')
    tipo_venta = fields.Char('Tipo de Venta', help='Ej. Servicios Principales, Upgrade, Migración')
    tipo_registro = fields.Char('tipo_registro', help='Tipo de registro reportado por Claro. Ej. Digitada, Instalada')
    # tipo_registro = fields.Char('Tipo Registro')
    canal2 = fields.Char('Canal 2')
    no_contrato = fields.Char('No. Contrato')
    estrato = fields.Char('Estrato', help='Estrato reportado en la venta')
    paquete_pg = fields.Char('Paquete PG')
    paquete_pvd = fields.Char('Paquete PVD')
    cod_campana = fields.Char('Cod. Campaña')
    mintic = fields.Char('MINTIC')
    tipo_de_producto = fields.Char('Tipo de Producto')
    gv_area = fields.Char('GV-Area')
    cod_tarifa = fields.Char('Cod. Tarifa')
    venta_convergente = fields.Char('Venta convergente')
    visor_movil = fields.Char('Visor móvil')
    val_identidad = fields.Char('Validación de Identidad')
    serial_captor = fields.Char('Serial Captor')
    estado_ap = fields.Many2one('gestor.estados_ap.team', string='Estado Antes del Pago', help='Ej. Legalizado, Carrusel, Fraude', track_visibility='onchange')
    estado_pp = fields.Many2one('gestor.estados_pp.team',  string='Estado Posterior al Pago', help='Ej. Pago devuelto, A Pagar,  Pagado', track_visibility='onchange')
    procesamiento_uid = fields.Many2one('res.users', string='Usuario último procesamiento')
    procesamiento_date = fields.Datetime('Fecha último procesamiento')
    year = fields.Integer('Año')
    mes = fields.Char('Mes')

    _sql_constraints = [('unq_gestor_hogar_team', 'UNIQUE (cuenta, ot, paquete, tipo_registro, renta)',
                         'La cuenta y la OT ya estan ingresadas, por favor verifique!')]

    @api.onchange('estado_ap')
    def _actualiza_estado_ap(self):
        for reg in self:
            for cuentas_ids in reg.env['gestor.hogar.team'].search([('ot', '=', reg.ot),
                                                                    ('cuenta', '=', reg.cuenta)]
                                                                   ):
                cuentas_ids.estado_ap = reg.estado_ap
            for cuentas_captura_ids in reg.env['gestor.captura.hogar.team'].search([('ot', '=', reg.ot),
                                                                                    ('cuenta', '=', reg.cuenta)]
                                                                                  ):
                cuentas_captura_ids.estado_venta = reg.estado_ap

    @api.onchange('estado_pp')
    def _actualiza_estado_pp(self):
        for reg in self:
            for cuentas_ids in reg.env['gestor.hogar.team'].search([('ot', '=', reg.ot),
                                                                    ('cuenta', '=', reg.cuenta)]
                                                                   ):
                cuentas_ids.estado_pp=reg.estado_pp


class CodigoMintic(models.Model):
    _name = 'gestor.codigo.mintic.team'
    _description = 'Código MINTIC'

    name = fields.Char('Código')
    descripcion = fields.Char('Descripción')
    id_codigo = fields.Char('ID código')


class CodigoPetar(models.Model):
    _name = 'gestor.codigo.petar.team'
    _description = 'Código PETAR MINTIC'

    name = fields.Char('Código')
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [('unq_codigo_codigo_petar_mintic__name', 'UNIQUE (name)',
                         'El código ya existe!')]


class ServiciosInternet(models.Model):
    _name = 'gestor.servicios.internet.team'
    _description = 'Servicios con Internet'

    name = fields.Char('Servicio')
    # base_liquidacion_id = fields.Many2one('gestor.base.liquidacion.hogar')
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [('unq_gestor.servicios.internet.team_name', 'UNIQUE (name)',
                         'El código ya existe!')]


class CodigoTarifaHogar(models.Model):
    _name = 'gestor.codigo.tarifa.hogar'
    _inherit = ['mail.thread']
    _description = 'Códigos de tarifa HOGAR'

    name = fields.Char('Código', track_visibility='onchange', index=True)
    red = fields.Char('Red', track_visibility='onchange')
    convergencia = fields.Char('Convergencia', track_visibility='onchange')
    megas = fields.Integer('Megas', track_visibility='onchange')
    estrato = fields.Integer('Estrato', track_visibility='onchange')
    servicio = fields.Char('Servicio', track_visibility='onchange')
    petar = fields.Char('PETAR', track_visibility='onchange')
    valor = fields.Float('Valor', track_visibility='onchange')
    tope = fields.Float('Tope', track_visibility='onchange')
    # desde = fields.Date('Inicio', help='Inicio de la vigencia de la tarifa')
    # hasta = fields.Date('Hasta', help='Fin de vigencia de la tarifa')
    inicio = fields.Date('Inicio', help='Inicio de la vigencia de la tarifa', track_visibility='onchange', copy=False)
    fin = fields.Date('Fin', help='Fin de vigencia de la tarifa', track_visibility='onchange', copy=False)

    _sql_constraints = [('unq_codigo_tarifa_hogar_team_name', 'UNIQUE (name, inicio, fin)',
                         'El código ya existe para esa vigencia!')]


class BasesDeLiquidacionHogar(models.Model):
    _name = 'gestor.base.liquidacion.hogar'
    _description = 'Bases de liquidación de HOGAR'
    _rec_name = 'servicio'

    servicio = fields.Char('Servicio')
    estrato = fields.Integer('Estrato')
    convergencia = fields.Char('Convergencia')
    comision_claro = fields.Float('% Comisión claro')
    comision_team = fields.Float('% Comisión TEAM')
    diferencia = fields.Float('Diferencia')
    # tipo_asesor = fields.Char('Tipo de Asesor')
    tipo_asesor = fields.Many2one('gestor.tarifas.especiales.hogar', string='Tipo Asesor')
    inicio = fields.Date('Inicio', help='Inicio de la vigencia de la tarifa')
    fin = fields.Date('Fin', help='Fin de vigencia de la tarifa')
    tipo_cobro = fields.Selection([('porcentaje', 'Porcentaje'),
                                   ('fijo', 'Fijo'),
                                   ('fijo mintic', 'Fijo MINTIC'),
                                   ('porcentaje mintic', 'Porcentaje MINTIC')])
    sucursal = fields.Many2one('gestor.sucursales')
    tipo_referido = fields.Selection([('natural', 'Natural'), ('qr', 'QR')])
    tipo_red = fields.Selection([('FTT', 'FTT'), ('OTRO', 'OTRO')], help='Tipo de RED reportada por Claro. Ej. FTT, BIDIRECCIONAL')
    serviciointernet_id = fields.Many2one('gestor.servicios.internet.team', string='Servicios de Internet')
    tope = fields.Integer('Tope')
    petar = fields.Char('PETAR')
    empleados_ids = fields.One2many('hr.employee', 'base_liquidacion_id', string='Empleado')
    poblacion_id = fields.Many2one('gestor.poblaciones.team', string='Población')

    _sql_constraints = [('unq_base_liquidacion_hogar_team_name', 'UNIQUE (servicio, red, estrato, convergencia, tipo_asesor, inicio, fin, tipo_cobro, sucursal)',
                         'La base ya existe para esa vigencia!')]


class HrTarifasEspeciales(models.Model):
    _name = 'gestor.tarifas.especiales.hogar'
    _description = 'Tarifas especiales'

    name = fields.Char('Tarifa Especial', help='Nombre de la tarifa especial')
    mostrar = fields.Boolean('Activo', default=True, help='Muestra el valor en empleados')
    condiciones_id = fields.Many2one('gestor.condiciones.comisiones.team')
    planillas_wz_id = fields.Integer('Planillas WZ', help='Planillas de liquidación hogar')


class LiqServiciosAdicionales(models.Model):
    _name = 'gestor.liquidacion.servicios.adicionales'
    _description = 'Repositorio liquidación servicios adicionales'

    cuenta = fields.Char('Cuenta', help='Orden de venta')
    ot = fields.Char('OT')
    servicio = fields.Char('Servicio')
    comision = fields.Char('Comisión', help='Comisión servicios adicionales')

    _sql_constraints = [
                        ('unq_liq_servicios_adicionales', 'UNIQUE (cuenta, ot, servicio)',
                         'Esta venta ya tiene ese servicio asociado!')
                        ]


class CapturaHogarEspejo(models.Model):
    _name = 'gestor.captura.hogar.espejo.team'
    _description = 'Captura Datos Hogar Espejo para biometrías'

    name = fields.Integer('Nombre')
    cuenta = fields.Char('Cuenta', help='Número de cuenta')
    ot = fields.Char('OT', help='Orden de trabajo')
    fecha = fields.Date('Fecha')
    id_cliente = fields.Char('CC/NIT Cliente', help='Cédula / NIT')
    nombre_cliente = fields.Char('Nombre Cliente', help='Nombre del cliente')
    id_asesor = fields.Integer('ID asesor')
    id_captura = fields.Integer('Nombre')

    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('name', False):
                # Only goes off when the custom_search is in the context values.
                name = str(record.name)
                result.append((record.id, "{}".format(name)))
            else:
                ot = str(record.ot)
                result.append((record.id, ot))
        return result


class Referidos(models.Model):
    _name = 'gestor.referidos.team'
    _description = 'Tabla de referidos para la gestión de Hogar'

    name = fields.Char('N. Identificación', index=True, required='True' )
    nombre_referido = fields.Char('Nombre', help='Nombre completo', required='True')
    telefono_referido = fields.Char('N. Celular/Fijo', help='Teléfono de contacto', required='True')
    correo_referido = fields.Char('email', help='Correo electrónico de contacto', required='True')
    banco_referido = fields.Many2one('res.bank', help='Entidad bancaria.', required='True')
    tipo_cuenta_referido = fields.Selection([('ahorros', 'Ahorros'), ('corriente', 'Corriente')], required='True')
    cuenta_referido = fields.Char('N- Cuenta', help='Número de cuenta del referido donde se le va a realizar la consignación, el titular debe ser la misma cédula del referido', required='True')
    planillas_wz_id = fields.Integer(string='Planillas de Liquidación Referidos')

    _sql_constraints = [
                        ('unq_referidos_name', 'UNIQUE (name)',
                         'El referido ya existe')
                        ]

    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('name', False):
                # Only goes off when the custom_search is in the context values.
                name = str(record.name)
                result.append((record.id, "{}".format(name)))
            else:
                nombre_referido = str(record.nombre_referido)
                result.append((record.id, nombre_referido))
        return result
