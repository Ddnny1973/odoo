import logging
from odoo import models, fields, api
from datetime import datetime, timedelta

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CapturaBiometrias(models.Model):
    _name = 'gestor.biometrias.team'
    _inherit = ['mail.thread']
    _description = 'Captura Biometrías'

    # select administrativo - comercial (defecto)

    name = fields.Char('Número de cuenta', help='Debe estar en HOGAR para ser válida', track_visibility=True)
    captura = fields.Many2one('gestor.captura.hogar.team', string='OT', domain="[('cuenta', '=', name)]", track_visibility=True)
    captura_2 = fields.Many2one('gestor.captura.hogar.espejo.team', string='OT', domain="[('cuenta', '=', name)]", track_visibility=True)
    existe_claro = fields.Boolean('Existe en CLARO', help='Valida si la cuenta está en los archivos de Claro')
    existe_gestor = fields.Boolean('Existe en CAPTURA', help='Valida si la cuenta está en el sistema de gestión de ventas Gestor-ERP')
    id_gestor = fields.Many2one('hr.employee',
                                string='Gestor',
                                index=True,
                                default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)]).id,
                                required=True, track_visibility=True
                                )
    id_responsable = fields.Many2one('hr.employee', string='Responsable', related='id_gestor.parent_id', store=True)
    departamento_vendedor = fields.Many2one('hr.department', related='id_gestor.department_id', string='Departamento (Gestor)', store=True)
    cargo_vendedor = fields.Many2one('hr.job', related='id_gestor.job_id', string='Cago (Gestor)', store=True)
    sucursal_vendedor = fields.Many2one('gestor.sucursales', related='id_gestor.sucursal_id', string='Sucursal (Gestor)', store=True)
    id_vendedor = fields.Many2one('hr.employee',
                                string='Vendedor',
                                index=True,
                                help='Vendedor que solicitó la gestión biométrica',
                                track_visibility=True
                                )
    cliente = fields.Text('Cliente', track_visibility=True)
    tipo_identificacion = fields.Selection([('cc', 'CC'), ('nit', 'NIT')], track_visibility=True)
    identificacion = fields.Char('Idetificacion', track_visibility=True, help='Si es NIT, sin digito de verificación')
    dv = fields.Char('DV', track_visibility=True, help='Si es NIT, Dígito de verificación')
    valor_comision = fields.Float('Valor comisión', default=0)
    comision_pagada = fields.Boolean('Comisión Pagada', track_visibility='onchange')
    fecha_pago_comision = fields.Date('Fecha de pago', track_visibility='onchange')
    usuario_pagador = fields.Many2one('res.users', string='Usuario Pagador', help='Usuario que proceso el pago', track_visibility='onchange')
    planillas_hogar_id = fields.Integer('Planillas_id')
    fecha = fields.Date('Fecha', track_visibility='onchange', default=fields.Date.context_today)
    esquema_id = fields.Many2one('gestor.comisiones.team', string='Esquema', track_visibility='onchange', compute='_get_esquema')
    active = fields.Boolean('Activo', default=True)
    tipo_biometria = fields.Selection([('administrativa', 'Administrativa'), ('comercial', 'Comercial')], default='comercial', required=True, track_visibility='onchange')
    comision_liquidada = fields.Boolean('Comisión Liquidada', track_visibility='onchange')
    estado_venta = fields.Many2one('gestor.estados_ap.team',
                                   related='captura.estado_venta',
                                   help='Estado de la venta antes del pago de Claro',
                                   store=True)

    def _get_esquema(self):
        for reg in self:
            esquema = reg.env['gestor.comisiones.team'].search([('employees_ids', '=', reg.id_gestor.id)], limit=1)
            # raise ValidationError(esquema)
            reg.esquema_id = esquema.id

    @api.constrains('name', 'identificacion', 'dv')
    def _valida_campos(self):
        if self.name:
            try:
                x = float(self.name)
            except Exception as e:
                raise ValidationError('EL campo de CUENTA solo debe contener dígitos numéricos, por favor verifique!')
        if self.identificacion:
            try:
                x = float(self.identificacion)
            except Exception as e:
                raise ValidationError('EL campo de CEDULA solo debe contener dígitos numéricos, por favor verifique!')
        if self.dv:
            try:
                x = float(self.dv)
            except Exception as e:
                raise ValidationError('EL campo de DIGITO DE VERIFICACIÓN (DV) solo debe contener dígitos numéricos, por favor verifique!')

    @api.constrains('name')
    @api.onchange('name')
    def _get_estado_cuenta(self):
        for reg in self:
            # ots_captura = reg.env['gestor.captura.hogar.espejo.team'].search([('cuenta', '=', reg.captura_2.id)])

            if reg.tipo_biometria == 'comercial':
                if reg.env['gestor.hogar.team'].search([('cuenta', '=', reg.name)]):
                    reg.existe_claro = True
                else:
                    reg.existe_claro = False
                # if ots_captura:
                #     reg.existe_gestor = True
                #     if len(ots_captura) == 1:
                #         reg.id_vendedor = ots_captura.id_asesor
                #         reg.cliente = ots_captura.nombre_cliente
                #         reg.identificacion = ots_captura.id_cliente
                #         reg.tipo_identificacion = 'cc'
                #         # reg.fecha = ots_captura.fecha
                #     else:
                #         reg.captura_2 = None
                #         reg.id_vendedor = None
                #         reg.cliente = None
                #         reg.identificacion = None
                #         reg.tipo_identificacion = None
                # else:
                #     reg.existe_gestor = False
                #     reg.captura_2 = None
                #     reg.id_vendedor = None
                #     reg.cliente = None
                #     reg.identificacion = None
                #     reg.tipo_identificacion = None
                reg.id_vendedor = None
                # reg.fecha = fields.Date.today()

    @api.constrains('name')
    def _registro_unico(self):
        for reg in self:
            if reg.captura_2:
                # raise ValidationError('Fecha: ' + str(reg.fecha) + ' Captura_2: ' + str(reg.captura_2.id) + ' id_gestor: ' + str(reg.id_gestor.id) + ' Cuenta: ' + reg.name)
                registros_ids = reg.env['gestor.biometrias.team'].search([('name', '=', reg.name),
                                                                          ('fecha', '=', reg.fecha),
                                                                          # ('id_gestor', '=', reg.id_gestor.id),
                                                                          ('captura_2', '=', reg.captura_2.id)])
                if len(registros_ids) > 1:
                    # raise ValidationError(registros_ids.captura_2)
                    raise ValidationError('Ya existe una biometría para esa cuenta con el mismo gestor, la misma fecha y la misma OT.')
            else:
                registros_ids = reg.env['gestor.biometrias.team'].search([('name', '=', reg.name),
                                                                             ('fecha', '=', reg.fecha),
                                                                             # ('id_gestor', '=', reg.id_gestor.id),
                                                                             ('captura_2', '=', False)])
                if len(registros_ids) > 1:
                    # raise ValidationError(registros_ids.captura_2)
                    raise ValidationError('Ya existe una biometría para esa cuenta con el mismo gestor, la misma fecha y sin OT.')

    @api.constrains('name', 'captura_2')
    def _liquidar_biometria(self):
        for reg in self:
            ots_captura = reg.env['gestor.captura.hogar.espejo.team'].search([('id', '=', reg.captura_2.id)])
            if ots_captura:
                reg.existe_gestor = True
                # reg.captura = ots_captura.id_captura
                reg.id_vendedor = ots_captura.id_asesor

            if reg.existe_gestor and reg.existe_claro:
                # Creando Descuentos
                tipo_descuento = self.env['tipo.descuento'].search([('name', '=', 'Biometría')])
                # raise ValidationError('tipo descuento: ' + tipo_descuento.name + ' cuotas: ' + str(tipo_descuento.cuotas or '0') + '\nVendedor: ' + reg.id_vendedor.name)
                descuentos = []
                if reg.id_gestor.descuento_biometria > 0 and tipo_descuento:
                    # Revisar porque se incluyó el filtro por categoría o tarifa especial
                    # if reg.id_vendedor.category_id.name != 'Vinculado' or reg.id_vendedor.tarifa_especial_id.name == 'EXTERNOS':
                    # Validando si el descuento ya existente
                    if reg.env['descuentos.teams'].search_count([('name', '=',reg.id_vendedor.id),
                                                                 ('tipodeprestamo', '=', tipo_descuento.id),
                                                                 ('fecha_aplicacion', '=', reg.fecha),
                                                                 ('num_factura', '=', reg.captura.ot)]) == 0:
                        descuentos.append({'name': reg.id_vendedor.id,
                                           'tipodeprestamo': tipo_descuento.id,
                                           'valoraplicar': reg.id_gestor.descuento_biometria,
                                           'valorprestamo': reg.id_gestor.descuento_biometria,
                                           'valorcuota': reg.id_gestor.descuento_biometria / tipo_descuento.cuotas,
                                           'fecha_aplicacion': reg.fecha,
                                           'num_factura': reg.captura_2.ot,
                                           'concepto': 'Descuento por biometría: ' + reg.name,
                                           'cuotas': tipo_descuento.cuotas,
                                           'captura_id': ots_captura.id_captura,
                                           'saldo': reg.id_gestor.descuento_biometria,
                                           })
                        reg.env['descuentos.teams'].create(descuentos)

    @api.constrains('captura_2')
    @api.onchange('captura_2')
    def _get_datos_ot(self):
        for reg in self:
            ots_captura = self.env['gestor.captura.hogar.espejo.team'].search([('id', '=', reg.captura_2.id)])
            self.id_vendedor = ots_captura.id_asesor
            reg.cliente = ots_captura.nombre_cliente
            reg.identificacion = ots_captura.id_cliente
            reg.tipo_identificacion = 'cc'
            reg.fecha = ots_captura.fecha or fields.Date.today()
            reg.captura=ots_captura.id_captura

    @api.onchange('identificacion')
    def _get_datos_cliente(self):
        for reg in self:
            cliente = reg.env['gestor.clientes.team'].search([('identificacion', '=', reg.identificacion)])
            if cliente:
                reg.cliente = cliente.name
                reg.tipo_identificacion = cliente.tipo_identificacion

    def _actualizacion_masiva(self):
        for i in self.env['gestor.biometrias.team'].search([('comision_pagada', '=', False)]):
            # i._get_estado_cuenta()
            # i._get_datos_ot()
            i._liquidar_biometria()


class CapturaBiometriasClaro(models.Model):
    _name = 'gestor.biometrias.claro'
    _description = 'Biometrías CLARO'

    cliente = fields.Char('Cliente')
    sucursal = fields.Char('Sucursal')
    nuip_sucursal = fields.Char('Nuip_Sucursal')
    nut = fields.Char('Nut')
    fecha = fields.Datetime('Fecha')
    documento = fields.Char('Documento')
    respuesta = fields.Char('Respuesta')
    usercod = fields.Char('Usercod')
    sucursalid = fields.Char('Sucursalid')
    operationid = fields.Char('Operationid')
    userip = fields.Char('Userip')
    usermac = fields.Char('Usermac')
    estado = fields.Char('Estado')
    proceso = fields.Char('Proceso')

    _sql_constraints = [('unq_biometrias_claro_nut', 'UNIQUE (nut)',
                         'El NUT de la biometría ya existe!')]
