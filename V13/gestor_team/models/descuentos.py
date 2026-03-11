# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date
import locale
import odoo.addons.decimal_precision as dp

import pymssql
import pandas as pd

_logger = logging.getLogger(__name__)

param_dic = {
            'server': 'team.soluciondigital.com.co',
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


class TipoPrestamo(models.Model):
    _name = 'tipo.descuento'
    _description = 'Tipo de descuento'
    _order = 'sequence'

    name = fields.Char('Tipo', help='Tipo de descuento')
    cuotas = fields.Integer('Cuotas por defecto', default=1)
    saldo_stok = fields.Boolean('Saldo en Stok', help='Determina si el saldo lo controla Gestor o Stok')
    sequence = fields.Integer('Secuencia')

    _sql_constraints = [('unq_tipo_descuento', 'UNIQUE (name)',
                         'El tipo de descuento ya existe'),
                        ]


class PeriodosLiquidacion(models.Model):
    _name = 'gestor.periodos.liquidacion'
    _description = 'Registra el período de liquidación en el que trabaja un usuario'
    _order = 'fecha_inicio'
    _reg_name = 'fecha_inicio'

    fecha_inicio = fields.Date('Inicio', help='Fecha inicio del período a liquidar')
    fecha_fin = fields.Date('Fin', help='Fecha final del período a liquidar')
    name = fields.Char('Usuario', related='create_uid.name')

    def get_periodo(self):
        for reg in self:
            reg.name = 'Desde ' + str(reg.fecha_inicio) + ' hasta ' + str(reg.fecha_fin)


class DescuentosTeams(models.Model):
    _name = 'descuentos.teams'
    _inherit = ['mail.thread']
    _description = 'Descuentos a empleados o colaboradores TEAMS'
    _order = 'name'

    # def _get_periodo(self):
    #     periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])
    #     return periodo.name

    name = fields.Many2one('hr.employee', string='Empleado', required=True, index=True)
    identificacion = fields.Char(string='Identificación', related='name.identification_id', index=True, store=True)
    categoria_vendedor = fields.Char(string='Categoría Vendedor', related='name.category_id.name', index=True, store=True)
    tipodeprestamo = fields.Many2one('tipo.descuento', string='Tipo de descuento', index=True)
    valorprestamo = fields.Float('Valor del documento', required=True, track_visibility='onchange')
    fecha_aplicacion = fields.Date('Fecha', help='Fecha en que se creó el documento', required=True)
    cuotas = fields.Integer('Número de cuotas')
    cuotasaplicadas = fields.Integer('Cuotas aplicadas', compute='get_saldo')
    # saldo = fields.Float('Saldo', compute='get_saldo')
    saldo = fields.Float('Saldo', default=0, index=True, track_visibility='onchange', digits=dp.get_precision('Saldos'))
    account = fields.Many2one('account.account', string='Cuenta')
    tercero = fields.Many2one('res.partner', string='Tercero')
    interes = fields.Float('% Interés', (3,2), help="Porcentaje que se aplicará al Préstamo")
    valorcuota = fields.Float('Valor Cuotas', required=True)
    concepto = fields.Text('Concepto', help='Información sobre lo que ocaciona el descuento', track_visibility='onchange')
    pagos_aplicados_ids = fields.One2many('pagos.aplicados', 'name')
    valoraplicar = fields.Float('Valor Aplicar', required=True,
                                help='Valor a aplicar próxima cuota', track_visibility='onchange', digits=dp.get_precision('Saldos'))
    # total_aplicar = fields.Float('Total Aplicar', compute='get_total_aplicar',
    #                              help='Valor total a aplicar próxima cuota')
    total_aplicar = fields.Float('Total Aplicar', help='Valor total a aplicar próxima cuota')
    id_factura_stok = fields.Integer('ID Factura Sotk')
    id_detalle_factura_stok = fields.Integer('ID Detalle Factura Sotk')
    num_factura = fields.Text('Num Fatura', help='Número de fatura Stok (si no existe debe colocar 0)', required='True', copy=False, index=True)
    # fecha_inicio = fields.Date('Inicio', help='Fecha inicio del período a liquidar', default=_get_fechas_inicial)
    # fecha_fin = fields.Date('Fin', help='Fecha final del período a liquidar', default=_get_fechas_fin)
    fecha_inicio = fields.Date('Inicio', help='Fecha inicio del período a liquidar', compute='_get_fechas_inicial')
    fecha_fin = fields.Date('Fin', help='Fecha final del período a liquidar', compute='_get_fechas_fin')
    total_aplicar_global = fields.Float('Total a Aplicar', compute='get_total_aplicar', digits=dp.get_precision('Saldos'))
    comision_a_pagar_global = fields.Float('Comisión a pagar', compute='get_total_aplicar', digits=dp.get_precision('Saldos'))
    # comision_generada = fields.Float('Comisión Generada',
    #                                  help='Valor Comisiones generadas listas para liquidar (pagar)')
    comision_generada = fields.Float('Comisión Generada',
                                     help='Valor Comisiones generadas listas para liquidar (pagar)',
                                     compute='_get_comision_generada', digits=dp.get_precision('Saldos'))
    comision_generada_total = fields.Float('Comisión Generada total',
                                           help='Valor Comisiones generadas incluyendo impuestos',
                                           compute='_get_comision_generada', digits=dp.get_precision('Saldos'))
    comision_a_pagar = fields.Float('Comisión a Pagar',
                                    help='Valor Comisiones generadas incluyendo los descuentos a aplicar', digits=dp.get_precision('Saldos'))
    comision = fields.Float('Comisión Capturas',
                            help='Valor Comisiones generadas a partir de las capturas (ventas propias)')
    comision_incentivos = fields.Float('Comisión Incentivos',
                                       help='Valor Comisiones generadas a partir de los incentivos', digits=dp.get_precision('Saldos'))
    comision_responsable = fields.Float('Comisión Responsable',
                                       help='Valor Comisiones generadas a partir de las ventas de los hijos del responsable', digits=dp.get_precision('Saldos'))
    iva = fields.Float('IVA', related='name.iva')
    retencion = fields.Float('Retención', related='name.retencion')
    reteiva = fields.Float('ReteIVA', related='name.reteiva')
    # valor_iva = fields.Float('Valor IVA', default=0)
    # valor_retencion = fields.Float('Valor Retención', default=0)
    # valor_reteiva = fields.Float('Valor ReteIVA', default=0)
    valor_iva = fields.Float('Valor IVA', compute='_get_comision_generada')
    valor_retencion = fields.Float('Valor Retención', compute='_get_comision_generada')
    valor_reteiva = fields.Float('Valor ReteIVA', compute='_get_comision_generada')
    active = fields.Boolean('Activo', default=True)
    captura_id = fields.Many2one('gestor.captura.hogar.team', string='OT', index=True)
    aplicaciones = fields.Char('Fechas de aplicación', compute='_get_fechas_aplicacion')
    estado = fields.Char('Estado')

    # _sql_constraints = [('unq_descuento', 'UNIQUE (name, tipodeprestamo, fecha_aplicacion, num_factura)',
    #                      'El descuento ya existe, por favor verifique - 2'),
    #                     # ('chk_comision_a_pagar', 'CHECK (comision_a_pagar>0)',
    #                     #  'La comisión a pagar no puede ser negativa!')
    #                     ]

    def _get_fechas_inicial(self):
        periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])
        self.fecha_inicio = periodo.fecha_inicio or '2021-01-01'

    def _get_fechas_fin(self):
        periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])
        self.fecha_fin = periodo.fecha_fin or '2022-12-31'

    def _get_fechas_aplicacion(self):
        for reg in self:
            aplicaciones = ''
            for i in reg.pagos_aplicados_ids:
                # valor = locale.format('%.0f', i.valor_aplicado, grouping=True, monetary=True)
                # valor = locale.format('%d', i.valor_aplicado, 1)
                valor = '{:,}'.format(round(i.valor_aplicado,0)).replace(',','.')
                # raise ValidationError(valor)
                aplicaciones += 'Valor aplicado: ' + valor + '(' + str(i.fecha_aplicacion) +')\n'
            reg.aplicaciones = aplicaciones

    def _get_comision_generada(self):
        for reg in self:
            comision = reg.comision
            comision_incentivos = reg.comision_incentivos
            comision_responsable = reg.comision_responsable
            comision_generada = comision + comision_incentivos + comision_responsable
            valor_iva = comision_generada * reg.iva
            valor_retencion = (comision + comision_responsable) * reg.retencion
            valor_reteiva = valor_iva * reg.reteiva
            reg.comision_generada = comision_generada
            reg.valor_iva = valor_iva
            reg.valor_retencion = valor_retencion
            reg.valor_reteiva = valor_reteiva
            reg.comision_generada_total = comision_generada + valor_iva - valor_retencion - valor_reteiva

    @api.constrains('comision_a_pagar', 'name', 'total_aplicar',  'active') # 'valoraplicar',
    def valida_comision_a_pagar(self):
        for reg in self:

            lista_empleados = []
            lista_empleados.append(reg.name.id)
            if reg.fecha_inicio is False:
                periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])
                fecha_inicio = periodo.fecha_inicio or '2020-01-01'
                fecha_fin = periodo.fecha_fin or fields.Date.today()
            else:
                fecha_inicio = reg.fecha_inicio
                fecha_fin = reg.fecha_fin
            # self.env.cr.commit()
            # reg._cr.execute("""
            #                     select f_descuentos_2(%s, %s, %s, 1);
            #                  """,
            #                 (lista_empleados, fecha_inicio, fecha_fin,)
            #                 )

    def get_saldo(self):
        for reg in self:
            saldo = 0
            cuotas = 0
            for i in reg.pagos_aplicados_ids:
                saldo += i.valor_aplicado
                cuotas += 1
            if reg.tipodeprestamo.saldo_stok is False:
                if reg.tipodeprestamo.name == 'Ajustes' and reg.valorprestamo < 0:
                    reg.saldo = reg.valorprestamo + saldo
                else:
                    reg.saldo = reg.valorprestamo - saldo
            reg.cuotasaplicadas = cuotas

    def get_total_aplicar(self):
        for registros in self:
            registros.total_aplicar_global = registros.total_aplicar

    # @api.onchange('valoraplicar', 'name', 'cuotas', 'tipodeprestamo')
    # @api.constrains('name', 'cuotas', 'tipodeprestamo')
    # @api.onchange('valoraplicar')
    # def get_comision_a_pagar(self):
    #     for reg in self:
    #         _logger.info('Entró a get_comision_a_pagar ')
    #         _logger.info('Entró a get_comision_a_pagar creando descuento por biometría')
    #
    #         lista_empleados = []
    #         lista_empleados.append(reg.name.id)
    #         if reg.fecha_inicio is False:
    #             periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])
    #             fecha_inicio = periodo.fecha_inicio or '2021-01-01'
    #             fecha_fin = periodo.fecha_fin or '2021-01-01'
    #         else:
    #             fecha_inicio = reg.fecha_inicio
    #             fecha_fin = reg.fecha_fin
            # if len(lista_empleados) >= 1 and lista_empleados[0]:
            # raise ValidationError(reg.valoraplicar)
            # reg.valoraplicar = valoraplicar_nuevo
            # self.env.cr.commit()
            # reg._cr.execute("""
            #                     select f_descuentos_2(%s, %s, %s, 1);
            #                  """,
            #                 (lista_empleados, fecha_inicio, fecha_fin,)
            #                 )

                # registros.valor_iva = (registros.comision + registros.comision_responsable) * registros.iva
                # registros.valor_retencion = registros.comision * registros.retencion
                # registros.valor_reteiva = registros.valor_iva * registros.reteiva
                #
                # comision_a_pagar = registros.comision_generada + registros.valor_iva - registros.valor_retencion - registros.valor_reteiva
                # if comision_a_pagar < valoraplicar_origen:
                #     valoraplicar_origen = comision_a_pagar
                #     reg._origin.valoraplicar = valoraplicar_origen
                # else:
                #     reg._origin.valoraplicar = valoraplicar_origen
                #
                # # total_aplicar = total - valoraplicar_origen + registros.valoraplicar
                # # total_aplicar = valoraplicar_origen
                # registros.total_aplicar = total_aplicar
                # registros.total_aplicar_global = total_aplicar
                # registros.comision_a_pagar = comision_a_pagar

    @api.onchange('tipodeprestamo')
    def get_numerocuotas(self):
        self.cuotas = self.tipodeprestamo.cuotas

    @api.onchange('fecha_aplicacion')
    def get_fechafin(self):
        if self.fecha_aplicacion:
            self.fecha_fin = self.fecha_aplicacion

    # @api.constrains('name', 'pagos_aplicados_ids')
    @api.onchange('valorprestamo', 'cuotas', 'pagos_aplicados_ids')
    def get_valor_cuota(self):
        if self.cuotas == 0 and self.saldo != 0:
            self.valorcuota = self.saldo
            # self.valoraplicar = self.saldo
        elif self.cuotas == 0 and self.saldo == 0:
            self.valorcuota = self.valorprestamo
            # self.valoraplicar = self.valorprestamo
        else:
            self.valorcuota = self.valorprestamo / self.cuotas
            # self.valoraplicar = self.valorprestamo / self.cuotas


class PagosAplicados(models.Model):
    _name = 'pagos.aplicados'
    _description = 'Tipo de descuento'

    name = fields.Many2one('descuentos.teams')
    valor_aplicado = fields.Float('Valor Cuota', required=True)
    fecha_aplicacion = fields.Date('Fecha de aplicación', required=True)
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [('unq_pago_aplicado', 'UNIQUE (name, fecha_aplicacion, active)',
                         'El pago ya existe')]

    @api.constrains('name')
    def get_saldo(self):
        for reg in self:
            if reg._origin:
                # raise validationerror(reg._origin.tipodeprestamo.name)
                saldo = reg.env['descuentos.teams'].search([('id', '=', reg._origin.name.id)])
                valor_aplicado = 0
                cuotas = 0
                for i in saldo.pagos_aplicados_ids:
                    valor_aplicado += i.valor_aplicado
                    cuotas += 1
                if not saldo.tipodeprestamo.saldo_stok:
                    if saldo.tipodeprestamo.name == 'Ajustes' and saldo.valorprestamo < 0:
                        saldo.saldo = saldo.valorprestamo + valor_aplicado
                    else:
                        saldo.saldo = saldo.valorprestamo - valor_aplicado
                # if round(saldo.saldo, 0) < 0 and (reg.name.tipodeprestamo != 13 and round(reg.name.valorprestamo, 0) > 0):
                #     raise ValidationError('El saldo del descuento no puede ser negativo para el empleado ' +
                #                           reg.name.name.name +
                #                           '\nNúmero de factura: ' + reg.name.num_factura +
                #                           '\nFecha: ' + str(reg.name.fecha_aplicacion) +
                #                           '\nSaldo final: ' + str(saldo.saldo)
                #                           )


class Employee(models.Model):
    _inherit = ['hr.employee']
    prestamos = fields.One2many('descuentos.teams', 'name', string='Préstamos')
