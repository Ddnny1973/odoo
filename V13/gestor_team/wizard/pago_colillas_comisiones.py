from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import base64
import pandas as pd

import logging

_logger = logging.getLogger(__name__)

registros_empleados = []
# cur_detalle_agrupado = []


class GeneracionPlanillasWizard(models.TransientModel):
    _name = "gestor.generacion.planillas.wizard"
    _description = "Generación de Planillas de Comisiones"

    category_id = fields.One2many('hr.employee.category', 'planillas_wz_id', string='Categoría')
    category_id_ex = fields.Boolean('Excluyente', help='Las categorías seleccionadas son EXCLUYENTES', default=True)
    job_id = fields.One2many('hr.job', 'planillas_wz_id', string='Cargo')
    job_id_ex = fields.Boolean('Excluyente', help='Los cargos seleccionados son EXCLUYENTES', default=True)
    empleados_seleccionados_id = fields.One2many('hr.employee', 'planillas_wz_id', string='Empleados',
                                                 domain=['|', ('active', '=', True), ('active', '=', False)],
                                                 context={'active_test': False})
    referidos_ids = fields.One2many('gestor.referidos.team', 'planillas_wz_id', string='Referidos')
    excluir_empleados = fields.Boolean('Excluir Empleados')
    excluir_ventas_propias = fields.Boolean('Excluir Ventas Propias')
    sucursal_ids = fields.One2many('gestor.sucursales', 'planillas_wz_id', string='Sucursales')
    sucursal_ids_ex = fields.Boolean('Excluyente', help='Las sucursales seleccionadas son EXCLUYENTES', default=True)
    cur_empleados_ids = fields.One2many('hr.employee', 'planillas_hogar_wz_id',
                                        domain=['|', ('active', '=', True), ('active', '=', False)],
                                        context={'active_test': False})
    registros_count = fields.Integer(string='Cantidad de empleados')
    ventas_detalle_count = fields.Integer(string='Cantidad de Ventas')
    comisiones_count = fields.Integer(string='Cantidad de Ventas por comisión')
    hogar = fields.Boolean('Hogar', help='Liquidar Hogar')
    pyme = fields.Boolean('PYME', help='Liquidar PYME')
    movil = fields.Boolean('Móvil', help='Liquidar Móvil')
    equipos = fields.Boolean('Equipos', help='Liquidar Equipos')
    biometrias = fields.Boolean('Biometrías', help='Liquidar Biometrías')
    fecha_incial = fields.Date('Fecha inicial', required=True, default=fields.Date.today())
    fecha_final = fields.Date('Fecha final', required=True, default=fields.Date.today())
    detalle_agrupado_ids = fields.One2many('gestor.captura.hogar.detalle.agrupado.team', 'planillas_hogar_id', ondelete='restrict')
    cur_agrupado = fields.One2many('gestor.captura.hogar.detalle.agrupado.team', 'planillas_hogar_id', ondelete='restrict')
    capturas_hogar_agrupado_ids = fields.One2many('gestor.captura.hogar.detalle.agrupado.team', 'name_wz')
    cur_agrupado_2 = fields.Many2many('gestor.captura.hogar.detalle.agrupado.team', 'gestor_agrupado_planillas_wz_rel')
    comisiones_ids = fields.One2many('gestor.repositorio.comisiones.team', 'planillas_hogar_id')
    cur_comisiones = fields.Many2many('gestor.repositorio.comisiones.team', 'gestor_comisiones_planillas_wz_rel')
    biometrias_ids = fields.One2many('gestor.repositorio.comisiones.team', 'planillas_biometrias_id')
    aplicar = fields.Boolean('Aplicar Filtro', default=False)
    traer_pagadas = fields.Boolean('Traer Pagadas', default=False)
    # Filtros adicionales
    tipo_biometrias = fields.Boolean('Biometrías', help='Liquidar Biometrías', default=True)
    tipo_comision = fields.Boolean('Comisiones', help='Liquidar Biometrías', default=True)
    tipo_descuento = fields.Boolean('Descuentos', help='Liquidar Biometrías', default=True)
    tipo_incentivo = fields.Boolean('Incentivos', help='Liquidar Biometrías', default=True)
    marcar_pago = fields.Boolean('Marcar/Pagar', help='Marca las ventas como pagadas y aplica los descuentos.', default=False)
    fecha_pago = fields.Date('Fecha Pago', help='Fecha en que se realizó el pago.\nSi esta vacía usa la fecha inicial y final.')
    tarifa_especial_id_capturas = fields.One2many('gestor.tarifas.especiales.hogar', 'planillas_wz_id')
    # registros_empleados_ids = fields.Many2many('hr.employee', 'hr_employee_registros_wz_rel',
    #                                            domain=['|', ('active', '=', True), ('active', '=', False)],
    #                                            context={'active_test': False})

    @api.onchange('referidos_ids')
    def _referidos(self):
        self.cur_empleados_ids = None
        self.job_id = None
        self.sucursal_ids = None
        self.excluir_empleados = None
        self.solo_ventas_propias = None
        self.category_id = None

        self.hogar = True
        self.tipo_incentivo = True

        self.category_id_capturas = None
        self.job_id_capturas = None
        self.sucursal_ids_capturas = None
        self.tarifa_especial_id_capturas = None

    @api.onchange('aplicar')
    def _registros_count(self):
        del registros_empleados[:]
        # del cur_detalle_agrupado[:]
        if self.aplicar:
            filtro = []
            registros = 0
            filtro_tipos = []               # Filtro para los tipos de comisiónot
            filtro_repositorio = []
            filtro_x_ventas = []
            filtro_x_ventas_2 = []

            # ******************************************************************
            # Filtro de búsqueda por empleado
            if len(self.job_id) > 0:
                filtro += [('job_id', 'in', self.job_id.ids)]
            if len(self.category_id) > 0:
                if filtro:
                    filtro.insert(0, '|')
                filtro += [('category_id', 'in', self.category_id.ids)]
            if len(self.sucursal_ids) > 0:
                if filtro:
                    filtro.insert(0, '|')
                filtro += [('sucursal_id', 'in', self.sucursal_ids.ids)]
            if self.empleados_seleccionados_id:
                if self.excluir_empleados:
                    if filtro:
                        filtro.insert(0, '&')
                    filtro += [('id', 'not in', self.empleados_seleccionados_id.ids)]
                else:
                    if filtro:
                        filtro.insert(0, '|')
                    filtro += [('id', 'in', self.empleados_seleccionados_id.ids)]

            if filtro:
                self.cur_empleados_ids = self.env['hr.employee'].with_context(active_test=False).search(filtro)
                # for i in self.env['hr.employee'].with_context(active_test=False).search(filtro):
                #     registros_empleados.append(i.id)
            else:
                self.cur_empleados_ids = self.env['hr.employee'].with_context(active_test=False).search([('id', 'in', self.empleados_seleccionados_id)])
                # for i in self.cur_empleados_ids:
                #     registros_empleados.append(i.id)

            for i in self.cur_empleados_ids:
                registros_empleados.append(i._origin.id)

            self.registros_count = len(registros_empleados)

            # raise ValidationError(registros_empleados)
            # ******************************************************************
            # Filtros tipos de esquema
            if self.tipo_comision and self.tipo_incentivo and self.tipo_biometrias and self.tipo_descuento:
                filtro_tipos = []
            if not self.tipo_comision and not self.tipo_incentivo and not self.tipo_biometrias and not self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'comision'), ('esquema_id.tipo_comision', '!=', 'incentivo'),
                                 ('esquema_id.tipo_comision', '!=', 'biometria'), ('esquema_id.tipo_comision', '!=', 'descuento')]

            if not self.tipo_comision and self.tipo_incentivo and self.tipo_biometrias and self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'comision')]
            if self.tipo_comision and not self.tipo_incentivo and self.tipo_biometrias and self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'incentivo')]
            if self.tipo_comision and self.tipo_incentivo and not self.tipo_biometrias and self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'biometria')]
            if self.tipo_comision and self.tipo_incentivo and self.tipo_biometrias and not self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'descuento')]

            if not self.tipo_biometrias and not self.tipo_comision and not self.tipo_descuento and self.tipo_incentivo:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'biometria'), ('esquema_id.tipo_comision', '!=', 'comision'), ('esquema_id.tipo_comision', '!=', 'descuento')]
            if not self.tipo_biometrias and not self.tipo_comision and self.tipo_descuento and not self.tipo_incentivo:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'biometria'), ('esquema_id.tipo_comision', '!=', 'comision'), ('esquema_id.tipo_comision', '!=', 'incentivo')]
            if not self.tipo_biometrias and self.tipo_comision and not self.tipo_descuento and not self.tipo_incentivo:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'biometria'), ('esquema_id.tipo_comision', '!=', 'descuento'), ('esquema_id.tipo_comision', '!=', 'incentivo')]
            if self.tipo_biometrias and not self.tipo_comision and not self.tipo_descuento and not self.tipo_incentivo:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'comision'), ('esquema_id.tipo_comision', '!=', 'descuento'), ('esquema_id.tipo_comision', '!=', 'incentivo')]

            if not self.tipo_comision and self.tipo_incentivo and not self.tipo_biometrias and self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'comision'), ('esquema_id.tipo_comision', '!=', 'biometria')]
            if not self.tipo_comision and self.tipo_incentivo and self.tipo_biometrias and not self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'comision'), ('esquema_id.tipo_comision', '!=', 'descuento')]

            if self.tipo_comision and not self.tipo_incentivo and not self.tipo_biometrias and self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'incentivo'), ('esquema_id.tipo_comision', '!=', 'biometria')]
            if self.tipo_comision and not self.tipo_incentivo and self.tipo_biometrias and not self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'incentivo'), ('esquema_id.tipo_comision', '!=', 'descuento')]

            if self.tipo_comision and self.tipo_incentivo and not self.tipo_biometrias and not self.tipo_descuento:
                filtro_tipos += [('esquema_id.tipo_comision', '!=', 'biometria'), ('esquema_id.tipo_comision', '!=', 'descuento')]

            filtro_repositorio = [('padre_id.id', 'in', registros_empleados),  # self.with_context(active_test=False).registros_empleados_ids.ids
                                  ('hogar_id.captura_hogar_id.fecha', '>=', self.fecha_incial),
                                  ('hogar_id.captura_hogar_id.fecha', '<=', self.fecha_final),
                                  ('valor_comision', '!=', 0)
                                  ]

            # Filtro para referidos
            filtro_repositorio_2 = [('referido_id.id', 'in', self.referidos_ids.ids),
                                    ('hogar_id.captura_hogar_id.fecha', '>=', self.fecha_incial),
                                    ('hogar_id.captura_hogar_id.fecha', '<=', self.fecha_final),
                                    ('valor_comision', '!=', 0)
                                    ]

            # Filtro para captura_ids
            filtro_repositorio_3 = [('captura_hogar_id.fecha', '>=', self.fecha_incial),
                                    ('captura_hogar_id.fecha', '<=', self.fecha_final),
                                    ('captura_hogar_id.id_asesor', 'in', registros_empleados),
                                    ('valor_comision', '>', 0),
                                    ('comision_liquidada', '=', True)
                                    ]

            # Filtro para biometrías
            filtro_repositorio_4 = [('padre_id.id', 'in', registros_empleados),
                                    ('biometrias_id.fecha', '>=', self.fecha_incial),
                                    ('biometrias_id.fecha', '<=', self.fecha_final),
                                    ('valor_comision', '!=', 0),
                                    ('hogar_id', '!=', False),
                                    # ('biometrias_id.tipo_biometria', '=', 'administrativa')
                                    ]
            filtro_repositorio += filtro_tipos
            filtro_repositorio_2 += filtro_tipos

            # (filtro_x_ventas, filtro_repositorio, filtro_repositorio_2, filtro_tipos))
            captura_ids = []
            if self.hogar:
                if self.traer_pagadas:
                    if self.referidos_ids:
                        filtro_repositorio_2 += [('comision_pagada', '=', True)]
                        self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio_2)
                    else:
                        if not self.excluir_ventas_propias:
                            filtro_repositorio_3 += [('comision_pagada', '=', True)]
                            self.cur_agrupado_2 = self.env['gestor.captura.hogar.detalle.agrupado.team'].search(filtro_repositorio_3)
                        filtro_repositorio += [('comision_pagada', '=', True)]
                        self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio)

                else:
                    if self.referidos_ids:
                        filtro_repositorio_2 += [('comision_pagada', '=', False)]
                        self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio_2)
                    else:
                        if not self.excluir_ventas_propias:
                            filtro_repositorio_3 += [('comision_pagada', '=', False)]
                            self.cur_agrupado_2 = self.env['gestor.captura.hogar.detalle.agrupado.team'].search(filtro_repositorio_3)
                        filtro_repositorio += [('comision_pagada', '=', False)]
                        # raise ValidationError(filtro_repositorio)
                        self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio)

                # self.cur_agrupado_2 = captura_ids.ids
                self.ventas_detalle_count = len(self.cur_agrupado_2.ids)
                self.comisiones_count = len(self.cur_comisiones)
                # raise ValidationError('cur_comisiones hogar: ' + str(len(self.cur_comisiones)))
            if self.biometrias:
                if self.traer_pagadas:
                    # filtro_repositorio += [('comision_pagada', '=', True), ('biometrias_id.tipo_biometria', '=', 'administrativa')]
                    # filtro_repositorio += [('comision_pagada', '=', True)]
                    # self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio)

                    filtro_repositorio_4 += [('comision_pagada', '=', True)]
                    self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio_4)
                else:
                    # filtro_repositorio += [('comision_pagada', '=', False), ('biometrias_id.tipo_biometria', '=', 'administrativa')]
                    # filtro_repositorio += [('comision_pagada', '=', False)]
                    # raise ValidationError(filtro_repositorio)
                    # self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio)

                    filtro_repositorio_4 += [('comision_pagada', '=', False)]
                    self.cur_comisiones = self.env['gestor.repositorio.comisiones.team'].search(filtro_repositorio_4)

            # self.registros_count = len(registros_empleados)
            # self.cur_empleados_ids = self.env['hr.employee'].with_context(active_test=False).search([('id', 'in', registros_empleados)])
            # Buscando ajustes positivos
            ajustes_ids = self.env['descuentos.teams'].search([('tipodeprestamo', '=', 'Ajustes'),
                                                               ('saldo', '>', 0),
                                                               ('valoraplicar', '=', 0)
                                                              ])
            if captura_ids:
                self.cur_agrupado = captura_ids
            else:
                self.cur_agrupado = None
                self.ventas_detalle_count = 0
            # Cargando empleados
            for i in self.cur_agrupado.captura_hogar_id.id_asesor:
                registros_empleados.append(i.id)
            for i in self.cur_comisiones.hogar_id.captura_hogar_id.id_responsable:
                registros_empleados.append(i.id)
            for i in ajustes_ids:
                registros_empleados.append(i.name.id)

            self.cur_empleados_ids = self.env['hr.employee'].with_context(active_test=False).search([('id', 'in', registros_empleados)])
            self.registros_count = len(self.cur_empleados_ids)
        else:
            self.cur_empleados_ids = None # self.env['hr.employee'].search([('id', 'in', 0)])
            self.cur_agrupado_2 = None # self.env['gestor.captura.hogar.detalle.agrupado.team'].search([('id', 'in', 0)])
            self.cur_comisiones = None # self.env['gestor.repositorio.comisiones.team'].search([('id', '=', 0)])
            self.biometrias_ids = None # self.env['gestor.biometrias.team'].search([('id_gestor', 'in', [0])])
            self.ventas_detalle_count = 0
            self.registros_count = 0
            self.comisiones_count = 0
            del registros_empleados[:]
            # self.tipo_biometrias = True
            # self.tipo_comision = True
            # self.tipo_descuento = True
            # self.tipo_incentivo = True
        # raise ValidationError(self.cur_comisiones)

    # # @api.depends('category_id', 'job_id')
    # def _registros_count_ventas(self):
    #     self.ventas_detalle_count = len(self.cur_agrupado_2)

    def generar_planillas(self):
        _logger.info('Ejecutando')
        if len(registros_empleados) == 0:
            for i in self.cur_empleados_ids:
                registros_empleados.append(i.id)

            raise ValidationError('Ocurrió un error en la generación del filtro, desmarque la casilla Aplicar y vuelva nuevamente a seleccionarla.')

        res = {}
        fname = 'Planillas.xlsx'
        path = '/mnt/compartida/rp/' + fname

        # Aplicar descuentos
        df_descuentos = []
        df_descuentos_ls = []
        df_plano_contable = []
        df_plano_contabilidad = []
        df_encabezado = [{
                          'NIT PAGADOR': '9013064489',
                          'TIPO DE PAGO': '238',
                          'APLICACIÓN': 'I',
                          'SECUENCIA DE ENVÍO': 'A1',
                          'NRO CUENTA A DEBITAR': '55100046082',
                          'TIPO DE CUENTA A DEBITAR': 'S',
                          'DESCRIPCIÓN DEL PAGO': 'COMISION',
                          }]
        # raise ValidationError(registros_empleados)
        for employees_id in self.env['hr.employee'].with_context(active_test=False).search([('id', 'in', registros_empleados)]):
            total_aplicar = 0
            # raise ValidationError(employees_id)

            if self.biometrias and self.tipo_biometrias and not self.hogar and not self.tipo_comision and not self.tipo_descuento and not self.tipo_incentivo:
                # raise ValidationError('Entró a no pagar descuentos')
                descuentos_ids = []
            else:
                # raise ValidationError('Entró a pagar descuentos')
                if self.traer_pagadas:
                    # if employees_id.id == 20316:
                    #     raise ValidationError('Entro 01')
                    # raise ValidationError('Entró a pagar descuentos -- Pagadas is true')
                    descuentos_ids = self.env['descuentos.teams'].search([('name', '=', employees_id.id),
                                                                           ('cuotasaplicadas', '>', 0),
                                                                           ('pagos_aplicados_ids.fecha_aplicacion', '>=', self.fecha_incial),
                                                                           ('pagos_aplicados_ids.fecha_aplicacion', '<=', self.fecha_final)
                                                                           ])
                else:
                    # raise ValidationError('Entró a pagar descuentos -- Pagadas is false')
                    descuentos_ids = self.env['descuentos.teams'].search([('name', '=', employees_id.id),
                                                                           ('valoraplicar', '!=', 0),
                                                                           ('saldo', '!=', 0),
                                                                           ('cuotas', '>=', 0),
                                                                           ])

                # Este for estaba dentro del else anterior, unico cambio que se hizo
                for descuentos in descuentos_ids:
                    total_aplicar = round(descuentos.valoraplicar, 2)
                    # totalizar Ajustes

                    if not self.traer_pagadas:
                        if self.tipo_comision or self.tipo_descuento or self.tipo_incentivo and total_aplicar != 0:
                            if self.marcar_pago:
                                raise ValidationError('Entró a aplicar pagos')
                                if descuentos.saldo > 0:
                                    self.env['pagos.aplicados'].create({'name': descuentos.id,
                                                                        'valor_aplicado': total_aplicar,
                                                                        'fecha_aplicacion': fields.Date.today()
                                                                        }
                                                                       )

                                if descuentos.saldo < 0:
                                    self.env['pagos.aplicados'].create({'name': descuentos.id,
                                                                        'valor_aplicado': total_aplicar,
                                                                        'fecha_aplicacion': fields.Date.today()
                                                                        }
                                                                       )
                                descuentos.valoraplicar = 0
                            df_descuentos.append({'Nombre': descuentos.name.pagar_a.name or descuentos.name.name,
                                                  'Identificación': descuentos.name.pagar_a.identification_id or descuentos.name.identification_id,
                                                  'tipodeprestamo': descuentos.tipodeprestamo.name,
                                                  'valor_aplicado': total_aplicar,
                                                  'fecha_aplicacion': fields.Date.today(),
                                                  'N. Factura': descuentos.num_factura or '',
                                                  'sucursal': descuentos.name.pagar_a.sucursal_id.name or descuentos.name.sucursal_id.name,
                                                  }
                                                 )
                    else:
                        # if len(descuentos.pagos_aplicados_ids) == 1:
                        #     df_descuentos.append({'Nombre': descuentos.name.pagar_a.name or descuentos.name.name,
                        #                           'Identificación': descuentos.name.pagar_a.identification_id or descuentos.name.identification_id,
                        #                           'tipodeprestamo': descuentos.tipodeprestamo.name,
                        #                           'valor_aplicado': descuentos.pagos_aplicados_ids.valor_aplicado,
                        #                           'fecha_aplicacion': descuentos.pagos_aplicados_ids.fecha_aplicacion,
                        #                           'N. Factura': descuentos.num_factura or '',
                        #                           'sucursal': descuentos.name.pagar_a.sucursal_id.name or descuentos.name.sucursal_id.name,
                        #                           }
                        #                          )
                        # else:
                        for i in descuentos.pagos_aplicados_ids:
                            df_descuentos.append({'Nombre': descuentos.name.pagar_a.name or descuentos.name.name,
                                                  'Identificación': descuentos.name.pagar_a.identification_id or descuentos.name.identification_id,
                                                  'tipodeprestamo': descuentos.tipodeprestamo.name,
                                                  'valor_aplicado': round(i.valor_aplicado, 2),
                                                  'fecha_aplicacion': i.fecha_aplicacion,
                                                  'N. Factura': descuentos.num_factura or '',
                                                  'sucursal': descuentos.name.pagar_a.sucursal_id.name or descuentos.name.sucursal_id.name,
                                                  }
                                                 )

                    df_descuentos_ls.append(descuentos.name.id)

                    if descuentos.tipodeprestamo.name != 'Ajustes':
                        df_plano_contable.append({
                                                  'Nombre': descuentos.name.pagar_a.name or descuentos.name.name,
                                                  'Identificación': descuentos.name.pagar_a.identification_id or descuentos.name.identification_id,
                                                  'Valor Comisión': total_aplicar,
                                                  'IVA': total_aplicar * descuentos.name.iva / 100,
                                                  'Retención': - total_aplicar * descuentos.name.retencion / 100,
                                                  'RETEIVA': - total_aplicar * descuentos.name.iva / 100 * descuentos.name.reteiva / 100,
                                                  }
                                                 )

            # raise ValidationError(df_descuentos)

        # No se para que es este código
        # for empleados in self.env['descuentos.teams'].search([('saldo', '>', 0)]):
        #     valor_comision_ventas = 0
        #     for i in self.cur_agrupado_2:
        #         if i.captura_hogar_id.id_asesor.id == empleados.name.id:
        #             valor_comision_ventas += 1

        agrupado = []
        # Buscando ventas propias
        for i in self.cur_agrupado_2:
            # Marcando como pagado
            if not self.traer_pagadas and self.marcar_pago:
                i.comision_pagada = True
                i.fecha_pago_comision = datetime.now().date()
                i.usuario_pagador = self.env.user
                i.convergencia_pagada = i.captura_hogar_id.venta_convergente
                i.captura_hogar_id.valor_comision += i.valor_comision

            if i.captura_hogar_id.id_asesor.tipo_documento_titular == 'nit':
                tipo_identificacion = '3'
            else:
                tipo_identificacion = '1'

            agrupado.append({'Proceso': 'HOGAR',
                             'id': i.id,
                             'OT': i.captura_hogar_id.ot,
                             'Cuenta': i.captura_hogar_id.cuenta,
                             'Vendedor': i.captura_hogar_id.id_asesor.name,
                             'Cargo': i.captura_hogar_id.cargo,
                             'Responsable': i.captura_hogar_id.id_responsable.name,
                             'Sucursal': i.captura_hogar_id.sucursal_vendedor.name,
                             'Tipo de Plan': i.tipo_plan.name,
                             'Valor Comisión': i.valor_comision,
                             'Paquete': i.paquete_pvd,
                             'Servicio': i.servicio,
                             'fecha': i.captura_hogar_id.fecha,
                             'Estrato': i.estrato_claro,
                             'Comisión TEAM': i.comision_team,
                             'Tipo de Cobro': i.tipo_cobro,
                             'Tarifa': i.cod_tarifa.name or '',
                             'Pagar a': i.captura_hogar_id.id_asesor.pagar_a.name or i.captura_hogar_id.id_asesor.name, # Validar datos del pagar a
                             'Identificación': i.captura_hogar_id.id_asesor.identification_id,
                             'E-mail': i.captura_hogar_id.id_asesor.work_email,
                             'iva': i.captura_hogar_id.id_asesor.pagar_a.iva or i.captura_hogar_id.id_asesor.iva,
                             'retencion': i.captura_hogar_id.id_asesor.pagar_a.retencion or i.captura_hogar_id.id_asesor.retencion,
                             'reteiva': i.captura_hogar_id.id_asesor.pagar_a.reteiva or i.captura_hogar_id.id_asesor.reteiva,
                             'Fecha Inicial': self.fecha_incial,
                             'Fecha Final': self.fecha_final,
                             'Correo Responsable': i.captura_hogar_id.id_asesor.parent_id.work_email or '',
                             'Sucursal a Pagar': i.captura_hogar_id.sucursal_vendedor.name,
                             'Correo Monitor': i.captura_hogar_id.id_asesor.coach_id.work_email or '',
                             'Código del Banco': i.captura_hogar_id.id_asesor.pagar_a.banco_id.bic or i.captura_hogar_id.id_asesor.banco_id.bic or '',
                             'Tipo de cuenta': i.captura_hogar_id.id_asesor.tipo_cuenta or '',
                             'No Cuenta Beneficiario ': i.captura_hogar_id.id_asesor.pagar_a.cuenta_id or i.captura_hogar_id.id_asesor.cuenta_id or '',
                             'Nombre Beneficiario:': i.captura_hogar_id.id_asesor.pagar_a.nombre_titular or i.captura_hogar_id.id_asesor.pagar_a.name or i.captura_hogar_id.id_asesor.nombre_titular or i.captura_hogar_id.id_asesor.name or '',
                             'Tipo identificación beneficiario:': tipo_identificacion,
                             'Nit Beneficiario': i.captura_hogar_id.id_asesor.pagar_a.identificacion_titular or i.captura_hogar_id.id_asesor.pagar_a.identification_id or i.captura_hogar_id.id_asesor.identificacion_titular or i.captura_hogar_id.id_asesor.identification_id or '',
                             'Convergencia': i.convergencia_pagada or '',
                             'Tarifa Especial': i.captura_hogar_id.tarifa_especial_id.name or '',
                             }
                            )

        # raise ValidationError(df_descuentos_ls)
        if self.biometrias and self.tipo_biometrias and not self.hogar and not self.tipo_comision and not self.tipo_descuento and not self.tipo_incentivo:
            empleados_id_sin_comision = []
        else:
            if not self.traer_pagadas:
                empleados_id_sin_comision = self.env['descuentos.teams'].search([
                                                                                 # ('valoraplicar', '!=', 0),
                                                                                 # ('saldo', '!=', 0),
                                                                                 ('cuotas', '>', 0),
                                                                                 ('name', 'not in', self.cur_agrupado_2.captura_hogar_id.id_asesor.ids),
                                                                                 ('name', 'in', df_descuentos_ls)
                                                                                 ])
            else:
                empleados_id_sin_comision = self.env['descuentos.teams'].search([
                                                                                 ('cuotas', '>', 0),
                                                                                 ('name', 'not in', self.cur_agrupado_2.captura_hogar_id.id_asesor.ids),
                                                                                 ('name', 'in', df_descuentos_ls),
                                                                                 ('pagos_aplicados_ids.fecha_aplicacion', '>=', self.fecha_incial),
                                                                                 ('pagos_aplicados_ids.fecha_aplicacion', '<=', self.fecha_final)
                                                                                 ])

                existe_id = []

                for i in empleados_id_sin_comision.search([('tipodeprestamo', '=', 'Ajustes'), ('valoraplicar', '<', 0)]):
                    if i.name.tipo_documento_titular == 'nit':
                        tipo_identificacion = '3'
                    else:
                        tipo_identificacion = '1'

                    if i.name.name not in existe_id:
                        agrupado.append({'Proceso': 'DESCUENTOS/AJUSTES',
                                         'id': i.id,
                                         'OT': '',
                                         'Cuenta': '',
                                         'Vendedor': i.name.name,
                                         'Cargo': i.name.job_id.name,
                                         'Responsable': i.name.parent_id.name,
                                         'Sucursal': i.name.sucursal_id.name,
                                         'Tipo de Plan': '',
                                         'Valor Comisión': 0,
                                         'Paquete': '',
                                         'Servicio': '',
                                         'fecha': i.fecha_aplicacion,
                                         'Estrato': '',
                                         'Comisión TEAM': 0,
                                         'Tipo de Cobro': '',
                                         'Tarifa': '',
                                         'Pagar a': i.name.name,
                                         'Identificación': i.name.identification_id,
                                         'E-mail': i.name.work_email,
                                         'iva': i.name.pagar_a.iva or i.name.iva,
                                         'retencion': i.name.pagar_a.retencion or i.name.retencion,
                                         'reteiva': i.name.pagar_a.reteiva or i.name.reteiva,
                                         'Fecha Inicial': self.fecha_incial,
                                         'Fecha Final': self.fecha_final,
                                         'Correo Responsable': i.name.parent_id.work_email or '',
                                         'Sucursal a Pagar': i.name.sucursal_id.name,
                                         'Correo Monitor': i.name.coach_id.work_email or '',
                                         'Código del Banco': i.name.pagar_a.banco_id.bic or i.name.banco_id.bic or '',
                                         'Tipo de cuenta': i.name.pagar_a.tipo_cuenta or i.name.tipo_cuenta or '',
                                         'No Cuenta Beneficiario ': i.name.pagar_a.cuenta_id or i.name.cuenta_id or '',
                                         'Nombre Beneficiario:': i.name.pagar_a.nombre_titular or i.name.nombre_titular or i.name.name or '',
                                         'Tipo identificación beneficiario:': tipo_identificacion,
                                         'Nit Beneficiario': i.name.pagar_a.identificacion_titular or i.name.identificacion_titular or i.name.identification_id or '',
                                         'Convergencia': '',
                                         'Tarifa Especial': '',
                                         }
                                        )
                        existe_id.append(i.name.name)

        # Buscando comisiones o incentivos
        for i in self.cur_comisiones:
            if i.valor_comision != 0:
                if not self.traer_pagadas and self.marcar_pago:
                    # raise ValidationError('Entró a pagar')
                    i.comision_pagada = True
                    i.fecha_pago_comision = fields.Date.today()
                    i.usuario_pagador = self.env.user

                    # Marcando la biometría
                    i.biometrias_id.comision_pagada = True
                    i.biometrias_id.fecha_pago_comision = fields.Date.today()
                    i.biometrias_id.usuario_pagador = self.env.user

                if i.padre_id.tipo_documento_titular == 'nit':
                    tipo_identificacion = '3'
                else:
                    tipo_identificacion = '1'

                if self.referidos_ids:
                    proceso = 'REFERIDOS - INCENTIVOS'
                    agrupado.append({'Proceso': proceso.upper(),
                                     'id': i.hogar_id.id,
                                     'OT': i.hogar_id.captura_hogar_id.ot,
                                     'Cuenta': i.hogar_id.captura_hogar_id.cuenta,
                                     'Vendedor': i.hogar_id.captura_hogar_id.id_asesor.name,
                                     'Cargo': i.hogar_id.captura_hogar_id.cargo,
                                     'Responsable': i.hogar_id.captura_hogar_id.id_responsable.name,
                                     'Sucursal': i.hogar_id.captura_hogar_id.sucursal_vendedor.name,
                                     'Tipo de Plan': i.hogar_id.tipo_plan.name,
                                     'Valor Comisión': i.valor_comision,
                                     'Paquete': i.hogar_id.paquete_pvd,
                                     'Servicio': i.hogar_id.servicio,
                                     'fecha': i.hogar_id.captura_hogar_id.fecha,
                                     'Estrato': i.hogar_id.estrato_claro,
                                     'Comisión TEAM': i.hogar_id.comision_team,
                                     'Tipo de Cobro': i.hogar_id.tipo_cobro,
                                     'Tarifa': i.hogar_id.cod_tarifa.name,
                                     'Pagar a': i.referido_id.nombre_referido,
                                     'Identificación': i.referido_id.name,
                                     'E-mail': i.referido_id.correo_referido,
                                     'iva': 0,
                                     'retencion': 0,
                                     'reteiva': 0,
                                     'Fecha Inicial': self.fecha_incial,
                                     'Fecha Final': self.fecha_final,
                                     'Correo Responsable': '',
                                     'Sucursal a Pagar': '',
                                     'Correo Monitor': '',
                                     'Código del Banco': i.referido_id.banco_referido.bic or '',
                                     'Tipo de cuenta': i.referido_id.tipo_cuenta_referido or '',
                                     'No Cuenta Beneficiario ': i.referido_id.cuenta_referido or '',
                                     'Nombre Beneficiario:': i.referido_id.nombre_referido or '',
                                     'Tipo identificación beneficiario:': tipo_identificacion,
                                     'Nit Beneficiario': i.referido_id.name or '',
                                     'Convergencia': i.hogar_id.convergencia_pagada or '',
                                     'Tarifa Especial': i.hogar_id.captura_hogar_id.tarifa_especial_id.name or '',
                                     }
                                    )
                else:
                    proceso = i.esquema_id.tipo_comision or 'NO DEFINIDO'

                    agrupado.append({'Proceso': proceso.upper(),
                                     'id': i.hogar_id.id,
                                     'OT': i.hogar_id.captura_hogar_id.ot,
                                     'Cuenta': i.hogar_id.captura_hogar_id.cuenta,
                                     'Vendedor': i.hogar_id.captura_hogar_id.id_asesor.name,
                                     'Cargo': i.hogar_id.captura_hogar_id.cargo,
                                     'Responsable': i.hogar_id.captura_hogar_id.id_responsable.name,
                                     'Sucursal': i.hogar_id.captura_hogar_id.sucursal_vendedor.name,
                                     'Tipo de Plan': i.hogar_id.tipo_plan.name,
                                     'Valor Comisión': i.valor_comision,
                                     'Paquete': i.hogar_id.paquete_pvd,
                                     'Servicio': i.hogar_id.servicio,
                                     'fecha': i.hogar_id.captura_hogar_id.fecha,
                                     'Estrato': i.hogar_id.estrato_claro,
                                     'Comisión TEAM': i.hogar_id.comision_team,
                                     'Tipo de Cobro': i.hogar_id.tipo_cobro,
                                     'Tarifa': i.hogar_id.cod_tarifa.name,
                                     'Pagar a': i.padre_id.name,
                                     'Identificación': i.padre_id.identification_id,
                                     'E-mail': i.padre_id.work_email,
                                     'iva': i.hogar_id.captura_hogar_id.id_asesor.pagar_a.iva or i.hogar_id.captura_hogar_id.id_asesor.iva,
                                     'retencion': i.hogar_id.captura_hogar_id.id_asesor.pagar_a.retencion or i.hogar_id.captura_hogar_id.id_asesor.retencion,
                                     'reteiva': i.hogar_id.captura_hogar_id.id_asesor.pagar_a.reteiva or i.hogar_id.captura_hogar_id.id_asesor.reteiva,
                                     'Fecha Inicial': self.fecha_incial,
                                     'Fecha Final': self.fecha_final,
                                     'Correo Responsable': i.padre_id.parent_id.work_email or '',
                                     'Sucursal a Pagar': i.padre_id.parent_id.sucursal_id.name,
                                     'Correo Monitor': i.padre_id.coach_id.work_email or '',
                                     'Código del Banco': i.padre_id.pagar_a.banco_id.bic or i.padre_id.banco_id.bic or '',
                                     'Tipo de cuenta': i.padre_id.pagar_a.tipo_cuenta or i.padre_id.tipo_cuenta or '',
                                     'No Cuenta Beneficiario ': i.padre_id.pagar_a.cuenta_id or i.padre_id.cuenta_id or '',
                                     'Nombre Beneficiario:': i.padre_id.pagar_a.nombre_titular or i.padre_id.nombre_titular or i.padre_id.name or '',
                                     'Tipo identificación beneficiario:': tipo_identificacion,
                                     'Nit Beneficiario': i.padre_id.pagar_a.identificacion_titular or i.padre_id.identificacion_titular or i.padre_id.identification_id or '',
                                     'Convergencia': i.hogar_id.convergencia_pagada or '',
                                     'Tarifa Especial': i.hogar_id.captura_hogar_id.tarifa_especial_id.name or '',
                                     }
                                    )

                # crear acumulado de incentivos y comiciones responsable

                df_plano_contable.append({
                                          'Nombre': i.hogar_id.captura_hogar_id.id_asesor.name,
                                          'Identificación': i.hogar_id.captura_hogar_id.id_asesor.identification_id,
                                          'Valor Comisión': i.valor_comision,
                                          'IVA': i.valor_comision * i.hogar_id.captura_hogar_id.id_asesor.iva / 100,
                                          'Retención': - i.valor_comision * i.hogar_id.captura_hogar_id.id_asesor.retencion / 100,
                                          'RETEIVA': - i.valor_comision * i.hogar_id.captura_hogar_id.id_asesor.iva / 100 * i.hogar_id.captura_hogar_id.id_asesor.reteiva / 100,
                                          }
                                         )

        # Buscando Biometrías
        for i in self.biometrias_ids:
            # i._liquidar_biometria()
            if not self.traer_pagadas and self.marcar_pago:
                i.comision_pagada = True
                i.fecha_pago_comision = datetime.now().date()
                i.usuario_pagador = self.env.user

                # Marcando la biometría
                i.biometrias_id.comision_pagada = True
                i.biometrias_id.fecha_pago_comision = datetime.now().date()
                i.biometrias_id.usuario_pagador = self.env.user

            tipo_identificacion = '1'
            if i.biometrias_id.tipo_biometria == 'administrativa':
                agrupado.append({'Proceso': 'BIOMETRIA ADMINISTRATIVA',
                                 'id': i.biometrias_id.id,
                                 'OT': '', #i.biometrias_id.ot or '',  # i.captura.ot,
                                 'Cuenta': i.biometrias_id.name or '', # i.captura.cuenta,
                                 'Vendedor': i.biometrias_id.id_gestor.name, # i.id_gestor.name,
                                 'Cargo': i.biometrias_id.id_gestor.job_id.name, # i.cargo_vendedor.name,
                                 'Responsable': i.biometrias_id.id_gestor.parent_id.name, # i.id_responsable.name,
                                 'Sucursal': i.biometrias_id.id_gestor.sucursal_id.name, # i.sucursal_vendedor.name,
                                 'Tipo de Plan': '',
                                 'Valor Comisión': i.valor_comision,
                                 'Paquete': '',
                                 'Servicio': '',
                                 'fecha': i.biometrias_id.fecha,
                                 'Estrato': '',
                                 'Comisión TEAM': '',
                                 'Tipo de Cobro': '',
                                 'Tarifa': '',
                                 'Pagar a': i.biometrias_id.id_gestor.name,
                                 'Identificación': i.biometrias_id.id_gestor.identification_id,
                                 'E-mail': i.biometrias_id.id_gestor.work_email,
                                 'iva': i.biometrias_id.id_gestor.pagar_a.iva or i.biometrias_id.id_gestor.iva,
                                 'retencion': i.biometrias_id.id_gestor.pagar_a.retencion or i.biometrias_id.id_gestor.retencion,
                                 'reteiva': i.biometrias_id.id_gestor.pagar_a.reteiva or i.biometrias_id.id_gestor.reteiva,
                                 'Fecha Inicial': self.fecha_incial,
                                 'Fecha Final': self.fecha_final,
                                 'Correo Responsable': i.biometrias_id.id_gestor.parent_id.work_email or '',
                                 'Sucursal a Pagar': i.biometrias_id.id_gestor.sucursal_id.name,
                                 'Correo Monitor': i.biometrias_id.id_gestor.coach_id.work_email or '',
                                 'Código del Banco': i.biometrias_id.id_gestor.banco_id.bic or '',
                                 'Tipo de cuenta': i.biometrias_id.id_gestor.pagar_a.tipo_cuenta or i.biometrias_id.id_gestor.tipo_cuenta or '',
                                 'No Cuenta Beneficiario ': i.biometrias_id.id_gestor.pagar_a.cuenta_id or i.biometrias_id.id_gestor.cuenta_id or '',
                                 'Nombre Beneficiario:': i.biometrias_id.id_gestor.pagar_a.nombre_titular or i.biometrias_id.id_gestor.nombre_titular or i.biometrias_id.id_gestor.name or '',
                                 'Tipo identificación beneficiario:': tipo_identificacion,
                                 'Nit Beneficiario': i.biometrias_id.id_gestor.identificacion_titular or i.biometrias_id.id_gestor.identification_id or '',
                                 }
                                )

        df = pd.DataFrame(agrupado)
        df2 = pd.DataFrame(df_descuentos)

        writer = pd.ExcelWriter(path, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Comisiones')
        df2.to_excel(writer, sheet_name='Descuentos')
        # df3.to_excel(writer, sheet_name='Plano Contable')
        # df_encabezado.to_excel(writer, sheet_name='Plano contabilidad')
        # df4.to_excel(writer, sheet_name='Plano contabilidad')
        writer.save()

        # data = base64.encodestring(open(path, 'r').read())
        with open(path, "rb") as data_file:
            data = base64.b64encode(data_file.read())

        # attach_vals = {'name': fname, 'datas': data, 'datas_fname': fname}
        attach_vals = {'name': fname, 'datas': data}

        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
        return res
