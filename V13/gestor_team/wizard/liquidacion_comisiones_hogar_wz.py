from odoo import models, fields, api
# from odoo.exceptions import ValidationError
# from datetime import datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class LiquidacioncomisionesHogarWizard(models.TransientModel):
    _name = "gestor.liquidacion.comisiones.hogar.wizard"
    _description = "Procesos de liquidación de Comisiones HOGAR"

    # def _get_default(self):
    #     # No se logra el resultado, no coloca el valor por defecto.
    #     self._ids = 2
    def get_default_categoria(self):
        return [1, 2, 3]

    def get_default_tipo_plan(self):
        return [24, 51, 28]

    def get_default_estado_venta(self):
        return [2]

    fecha_inicial = fields.Date('Fecha inicial')
    fecha_final = fields.Date('Fecha final')

    categoria_ids = fields.One2many('hr.employee.category', 'comisiones_wz_id', string='Categoría', default=get_default_categoria)
    job_id = fields.One2many('hr.job', 'comisiones_wz_id', string='Cargo')
    # empleados_ids = fields.Many2many('hr.employee', string='Empleados')
    empleados_ids = fields.One2many('hr.employee', 'liquidacion_wz_id',
                                    string='Empleados',
                                    domain=['|', ('active', '=', True), ('active', '=', False)])
    excluir_empleados = fields.Boolean('Excluir Empleados')
    sucursal_ids = fields.One2many('gestor.sucursales', 'name', string='Sucursales')
    estado_venta = fields.Many2one('gestor.estados_ap.team',
                                   help='Estado de la venta antes del pago de Claro', default=2)
    estado_venta_ids = fields.One2many('gestor.estados_ap.team', 'comisiones_wz_id',
                                       help='Estado de la venta antes del pago de Claro', default=get_default_estado_venta)
    estado_posterior_al_pago_claro = fields.Many2one('gestor.estados_pp.team')
    capturas_hogar_ids = fields.One2many('gestor.captura.hogar.team', 'name')
    capturas_hogar_agrupado_ids = fields.One2many('gestor.captura.hogar.detalle.agrupado.team', 'name_wz')
    aplicar = fields.Boolean('Aplicar Filtro', default=False)
    registros_count = fields.Integer(string='Cantidad de Capturas')
    registros_agrupados_count = fields.Integer(string='Cantidad de registros Agrupados')
    registros_comision_cero_count = fields.Integer(string='Cantidad de registros con comisión 0')
    empleados_count = fields.Integer('Cantidad de empleados', help='Cantidad de empleados seleccionados')
    registros_a_pagar = fields.Integer(string='Cantidad de registros a Liquidar')
    registros_liquidados = fields.Boolean('Traer registros liquidados')
    # tipo_plan_id = fields.Many2one('gestor.tipo.plan.team')
    tipo_plan_ids = fields.One2many('gestor.tipo.plan.team', 'plan_id_wz', string='Tipo de Plan', default=get_default_tipo_plan)
    accion = fields.Selection([('recalcular', 'Recalcular'), ('liquidar', 'Liquidar')], string='Acción', default='liquidar')
    sw_comision_ventas = fields.Boolean('Comisión Ventas', help='Incluir en descuentos', default=True)
    sw_comision_responsable = fields.Boolean('Comisión Responsable', help='Incluir en descuentos', default=True)
    sw_comision_incentivo = fields.Boolean('Comisión Incentivo', help='Incluir en descuentos', default=True)

    @api.onchange('aplicar')
    def _registros_count(self):
        conteo = 0
        conteo_comision_cero = 0
        # self.capturas_hogar_ids =
        # registros = self.env['gestor.captura.hogar.team'].search([('fecha', '<', '2000-01-01')])
        if self.aplicar:
            filtro = []
            filtro_2 = []
            filtro_3 = []
            registros = 0

            # raise ValidationError(self.empleados_ids.with_context(active_test=False).search([()]))

            # empleados = self.with_context(active_test=False).empleados_ids
            #
            # raise ValidationError(empleados)

            filtro_agrupado = []

            if len(self.job_id) > 0:
                filtro_2 += [('job_id', 'in', self.job_id.ids)]
            if len(self.categoria_ids) > 0:
                if filtro_2:
                    filtro_2.insert(0, '|')
                filtro_2 += [('category_id', 'in', self.categoria_ids.ids)]
            if len(self.sucursal_ids) > 0:
                if filtro_2:
                    filtro_2.insert(0, '|')
                filtro_2 += [('sucursal_id', 'in', self.sucursal_ids.ids)]
            if self.with_context(active_test=False).empleados_ids:
                if self.excluir_empleados:
                    filtro_2 += [('id', 'not in', self.with_context(active_test=False).empleados_ids.ids)]
                else:
                    if filtro_2:
                        filtro_2.insert(0, '|')
                    filtro_2 += [('id', 'in', self.with_context(active_test=False).empleados_ids.ids)]
            if filtro_2:
                filtro_2 += ['|', ('active', '=', True), ('active', '=', False)]
                empleados_ids = self.env['hr.employee'].with_context(active_test=False).search(filtro_2)

                filtro += [('vendedor', 'in', empleados_ids.user_id.ids)]
                _logger.info('Filtro empleado')
                _logger.info(filtro)
            else:
                empleados_ids = self.env['hr.employee'].with_context(active_test=False).search([()])
                filtro += [('vendedor', 'in', empleados_ids.user_id.ids)]
                _logger.info('Filtro empleado')
                _logger.info(filtro)

            if self.tipo_plan_ids:
                filtro += [('detalle_agrupado_captura_hogar_ids.tipo_plan', 'in', self.tipo_plan_ids.ids)]
                filtro_agrupado += [('tipo_plan', '=', self.tipo_plan_ids.ids)]
            filtro += [('fecha', '>=', self.fecha_inicial)]
            filtro += [('fecha', '<=', self.fecha_final)]
            filtro += [('estado_venta', '=', self.estado_venta_ids.ids)]
            # raise ValidationError(self.tipo_plan_ids.ids)

            # _logger.info('Filtro a aplicar')
            # _logger.info(filtro)
            # raise ValidationError(filtro_2)
            self.capturas_hogar_ids = self.env['gestor.captura.hogar.team'].search(filtro)
            capturas_ids = self.env['gestor.captura.hogar.team'].search(filtro)
            self.capturas_hogar_ids = capturas_ids

            # raise ValidationError(capturas_ids)

            # filtro_agrupado += [('captura_hogar_id', 'in', self.capturas_hogar_ids.ids)]
            filtro_agrupado += [('captura_hogar_id', 'in', capturas_ids.ids)]
            filtro_agrupado += [('comision_pagada', '=', False)]
            if self.accion == 'liquidar':
                filtro_agrupado += [('valor_comision', '>', 0)]

            # raise ValidationError(filtro_agrupado)

            self.capturas_hogar_agrupado_ids = self.env['gestor.captura.hogar.detalle.agrupado.team'].search(filtro_agrupado)

            filtro_3 = filtro + [('valor_comision', '=', 0)]
            conteo_comision_cero = self.capturas_hogar_ids.search_count(filtro_3)
            # conteo_comision_cero = 999
            # self.capturas_hogar_ids = registros
            self.registros_count = len(self.capturas_hogar_ids)
            self.registros_agrupados_count = len(self.capturas_hogar_agrupado_ids)
            self.registros_comision_cero_count = conteo_comision_cero
            self.registros_a_pagar = conteo - conteo_comision_cero
            self.empleados_count = len(empleados_ids)
            self.empleados_encontrados_ids = empleados_ids
        else:
            self.registros_count = 0
            self.registros_agrupados_count = 0
            self.registros_comision_cero_count = 0
            self.registros_a_pagar = 0
            self.empleados_count = 0
            self.capturas_hogar_ids = None # self.env['gestor.captura.hogar.team'].search([('vendedor', 'in', 0)])
            self.capturas_hogar_agrupado_ids = None # self.env['gestor.captura.hogar.detalle.agrupado.team'].search([('captura_hogar_id', 'in', self.capturas_hogar_ids.ids)])

        # Actualizando período de consulta por usuario
        periodo = self.env['gestor.periodos.liquidacion'].search([('create_uid', '=', self.env.user.id)])

        if periodo:
            periodo.fecha_inicio = self.fecha_inicial
            periodo.fecha_fin = self.fecha_final
        else:
            self.env['gestor.periodos.liquidacion'].create({'fecha_inicio': self.fecha_inicial,
                                                            'fecha_fin': self.fecha_final, })

    def pagar_capturas(self):
        # raise ValidationError(len(self.capturas_hogar_ids))
        for reg in self.capturas_hogar_ids:
            reg.pagar_liquidacion_comisiones()

    def liquidar_capturas(self):
        # Buscando empleados
        filtro_2 = []
        if len(self.job_id) > 0:
            filtro_2 += [('job_id', 'in', self.job_id.ids)]
        if len(self.categoria_ids) > 0:
            if filtro_2:
                filtro_2.insert(0, '|')
            filtro_2 += [('category_id', 'in', self.categoria_ids.ids)]
        if len(self.sucursal_ids) > 0:
            if filtro_2:
                filtro_2.insert(0, '|')
            filtro_2 += [('sucursal_id', 'in', self.sucursal_ids.ids)]
        if self.with_context(active_test=False).empleados_ids:
            if self.excluir_empleados:
                filtro_2 += [('id', 'not in', self.with_context(active_test=False).empleados_ids.ids)]
            else:
                if filtro_2:
                    filtro_2.insert(0, '|')
                filtro_2 += [('id', 'in', self.with_context(active_test=False).empleados_ids.ids)]
        if filtro_2:
            empleados_ids = self.env['hr.employee'].with_context(active_test=False).search(filtro_2)
        else:
            empleados_ids = self.env['hr.employee'].with_context(active_test=False).search([()])

        #####

        for reg in self.capturas_hogar_agrupado_ids:
            # raise ValidationError(reg.id)
            # reg.liquidacion_comisiones()
            if reg.valor_comision > 0:
                reg.comision_liquidada = True
                reg.fecha_liquidacion_comision = fields.Date.today()    # datetime.now().date()
                reg.usuario_liquidador = self.env.user

        if self.fecha_inicial and self.fecha_final:
            # La función f_liquidacion_padres_hogar_2 usa array para buscar el valor de la comisión y el esquema, esto reduce los cálculos
            # pues solo hace la búsqueda una sola vez y devuelve tanto el valor como el esquema ID.
            # La función f_liquidacion_padres_hogar usa el método tradicional que busca el valor y luego repite la consulta para buscar el esquema ID
            # sql = """
            #         select f_liquidacion_padres_hogar_2({0}, {1}, '{2}', '{3}')
            #       """.format(0, 0, self.fecha_inicial, self.fecha_final)
            # self.env.cr.execute(sql)

            self._cr.execute("""
                                select f_liquidacion_padres_hogar_2(0, 0, %s, %s)
                             """, (self.fecha_inicial, self.fecha_final)
                             )

            self._cr.execute("""
                                select f_descuentos_2(%s, %s, %s, 0, %s, %s, %s);
                             """,
                             (empleados_ids.ids,
                              self.fecha_inicial,
                              self.fecha_final,
                              self.sw_comision_ventas,
                              self.sw_comision_responsable,
                              self.sw_comision_incentivo)
                             )
            # self.env.cr.commit()

    def recalcular_liquidacion(self):
        for reg in self.capturas_hogar_ids:
            reg.recalcular_liquidacion_comisiones()
