from odoo import models, fields, api
from odoo.exceptions import ValidationError
from operator import attrgetter
import pandas as pd
import os
import pymssql

import logging

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


class LiquidacionComisionesWizard(models.TransientModel):
    _name = "gestor.liquidacion.comisiones.wizard"
    _description = "Cambiar responsables de forma masiva"

    employee_id = fields.Many2one('hr.employee',
                                  string='Empleado a liquidar')
    fecha_inicio = fields.Date('Fecha inicio', help='Fecha desde donde se va a buscar información en TIPS')
    fecha_fin = fields.Date('Fecha fin', default=fields.Date.context_today)

    def consulta_tips(self):
        ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_rp_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
        ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'
        try:
            # Consultando datos de TEPS
            conn = connect(param_dic)
            sql = """
                      SELECT *
                      FROM [TipsII].[dbo].[Gtor_Ventas]
                      where fecha between '{0}' and '{1}'
                  """.format(self.fecha_inicio, self.fecha_fin)
            consulta_mssql = pd.read_sql_query(sql, conn)
            total_registros_tips = len(consulta_mssql.index)
            exportacion_name = ruta_odoo + 'consulta_comisiones_mssql.txt'
            importacion_name = ruta_bd + 'consulta_comisiones_mssql.txt'
            if os.path.isfile(exportacion_name):
                os.remove(exportacion_name)
            consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
            print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
            # Probar con tabla temporar en postgres por temas de rendimiento
            self.env.cr.execute("""truncate table gestor_consulta_comisiones_ventas_tips_tmp""")
            self.env.cr.execute("""copy gestor_consulta_comisiones_ventas_tips_tmp from %s DELIMITER ',' csv HEADER;""",
                                (importacion_name,)
                                )
            self.env.cr.execute("""select load_comisiones_ventas_tips();""")
            self.env.cr.commit()
        except Exception as e:
            # Atrapar error
            print("Ocurrió un error al conectar a SQL Server: %s", e)
            raise ValidationError(e)

    def liquidar(self):
        # self.env['gestor.cruce.rp.wizard'].consulta_tips(self.fecha_inicio, self.fecha_fin)
        tipo_plan_ids = self.employee_id.comisiones_ids.tipo_plan_ids
        planes_ids = self.env['gestor.planes.team'].search([('tipo_plan', 'in', tipo_plan_ids.ids)])
        total_a_pagar = 0
        contador_ventas = 0
        contador_esquemas = 0
        contador_categoria = 0
        contador_sucursal = 0

        # total_ventas = self.env['gestor.consulta.ventas.tips'].search([('vendedor_id', '=', self.employee_id.identification_id),
        #                                                                  ('plan_id', 'in', planes_ids.ids)])
        # raise ValidationError(len(total_ventas))
        # for ventas_ids in self.env['gestor.consulta.comisiones.tips'].search([('vendedor_id', '=', self.employee_id.identification_id),
        #                                                                       ('plan_id', 'in', planes_ids.ids),
        #                                                                       ('venta_id', '=', '1315254')]):
        for ventas_ids in self.env['gestor.consulta.comisiones.tips'].search([]):         # 'venta_id', '=', '1320525'
            valor = 0
            contador_ventas += 1

            # fecha_venta = ventas_ids.fecha
            precio_plan = self.env['gestor.precio.planes.team'].search([('name', '=', ventas_ids.plan_id.id)])  # Validar por fecha del precio del plan
            # precio_con_iva = precio_plan.detalle_precios_planes_ids.cfm_con_iva
            # precio_sin_iva = precio_plan.detalle_precios_planes_ids.cfm_sin_iva
            plan = ventas_ids.plan_id
            tipo_plan = ventas_ids.plan_id.tipo_plan
            categoria_tipo_plan = ventas_ids.plan_id.tipo_plan.categoria_id
            mes_liquidacion = ventas_ids.mes_de_liquidacion + 1

            empleado = ventas_ids.empleado_id
            cargo = ventas_ids.cargo
            categoria_empleado = self.env['hr.employee.category'].search([('name', '=', ventas_ids.categoria_empleado)])
            responsable = ventas_ids.responsable
            # canal_empleado = self.env['crm.team'].search([('name', '=', ventas_ids.canal_empleado)])

            sucursal = self.env['gestor.sucursales'].search([('name', '=', ventas_ids.sucursal)])

            esquemas_aplicables = []
            esquemas_a_pagar = []

            for esquemas in self.env['gestor.comisiones.team'].search([]):
                grupo_empleado = True
                grupo_sucursales = True
                grupo_topes = True
                grupo_planes = True
                grupo_excepciones = True
                # ----- Revisando Grupo Empleados -----
                # Evaluación por Responsable
                if esquemas.por_responsable:
                    if responsable not in esquemas.por_responsable:
                        grupo_empleado = False

                # Evaluación por empleado
                if esquemas.employees_ids:
                    if empleado not in esquemas.employees_ids:
                        grupo_empleado = False

                # Evaluación por Cargo de empleado
                if esquemas.job_ids:
                    if cargo not in esquemas.job_ids:
                        grupo_empleado = False

                # Evaluación por Categoría del empleado
                if esquemas.categoria_empleado_ids:
                    if categoria_empleado not in esquemas.categoria_empleado_ids:
                        grupo_empleado = False

                # Evaluación por Canal del empleado
                # if esquemas.canales_ids:
                    # if canal_empleado in esquemas.canales_ids:
                    #     grupo_empleado = 1

                # ----- Revisando Grupo Sucursales -----
                # Evaluación por Sucursal
                if esquemas.sucursales_ids:
                    if sucursal not in esquemas.sucursales_ids:
                        grupo_sucursales = False

                # ----- Revisando Grupo Topes -----
                # Evaluación por Topes
                # if sucursal in esquemas.sucursales_ids:
                #     # raise ValidationError('Sucursal: ' + sucursal + '\nSucursal Esquema: ' + esquemas.sucursales_ids.name)
                #     grupo_topes = 1
                grupo_topes = True

                # ----- Revisando Grupo Planes -----
                # Evaluación por Plan
                if esquemas.planes_ids:
                    if plan not in esquemas.planes_ids:
                        grupo_planes = False

                # Evaluación por Categoría tipo Plan
                if esquemas.categoria_tipo_plan_ids:
                    if categoria_tipo_plan not in esquemas.categoria_tipo_plan_ids:
                        grupo_planes = False

                # Evaluación por tipo Plan
                if esquemas.tipo_plan_ids:
                    if tipo_plan not in esquemas.tipo_plan_ids:
                        grupo_planes = False

                # _logger.info('Esquema que se evalúa: ' + esquemas.name +
                #              ' grupo empleado: ' + str(grupo_empleado) + ' Empleado: ' + empleado.name +
                #              ' Grupo Planes: ' + str(grupo_planes) + ' Plan: ' + plan.name +
                #              ' Grupo sucursales: ' + str(grupo_sucursales) + '\nGrupo Topes: ' + str(grupo_topes))

                if grupo_empleado and grupo_planes and grupo_sucursales:
                    esquemas_aplicables.append(esquemas)
            # raise ValidationError(esquemas_aplicables)
            valor_a_pagar = 0
            esquemas_obligatorios = []
            esquemas_totales = [0,]
            for i in esquemas_aplicables:
                if i.pago_obligado:
                    esquemas_obligatorios.append(i)
                    _logger.info('Nombre esquema obligado: ' + i.name)
                else:
                    esquemas_a_pagar.append(i)
                    _logger.info('Nombre esquema a pagar: ' + i.name)

            for reg in esquemas_obligatorios:
                _logger.info('Entrando a registros obligatorios: ' + str(reg.name))
                tipo_pago = reg['tipo_pago']
                mes_seleccionado = 'mes' + str(mes_liquidacion)
                valor = reg[mes_seleccionado]
                cfm_sin_iva = self.env['gestor.detalle.precios.planes.team'].search([('precio_detalle_id', '=', precio_plan.id),
                                                                                     ('fecha_inicio', '<=', ventas_ids.fecha),
                                                                                     ('fecha_fin', '>=', ventas_ids.fecha)
                                                                                     ], limit=1)
                if tipo_pago == 'valor':
                    valor_a_pagar = valor_a_pagar + valor
                else:
                    valor_a_pagar = valor_a_pagar + valor * cfm_sin_iva.cfm_sin_iva / 100
                esquemas_totales.append(reg['id'])

            _logger.info('Valor a pagar obligatorio: ' + str(valor_a_pagar))
            if esquemas_a_pagar:
                for reg in max(esquemas_a_pagar, key=attrgetter('secuencia')):
                    if reg.pago_obligado is False:
                        tipo_pago = reg['tipo_pago']
                        mes_seleccionado = 'mes' + str(mes_liquidacion)
                        valor = reg[mes_seleccionado]
                        cfm_sin_iva = self.env['gestor.detalle.precios.planes.team'].search([('precio_detalle_id', '=', precio_plan.id),
                                                                                             ('fecha_inicio', '<=', ventas_ids.fecha),
                                                                                             ('fecha_fin', '>=', ventas_ids.fecha)
                                                                                             ], limit=1)
                        if tipo_pago == 'valor':
                            valor_a_pagar = valor_a_pagar + valor
                            _logger.info('Valor a pagos normales: ' + str(valor))
                        else:
                            valor_a_pagar = valor_a_pagar + valor * cfm_sin_iva.cfm_sin_iva / 100
                            _logger.info('Valor a pagos normales: ' + str(valor * cfm_sin_iva.cfm_sin_iva / 100))
                        esquemas_totales.append(reg['id'])
                        # raise ValidationError('Tipo de pago: ' + tipo_pago + '\nValor: ' + str(valor) +
                        #                       '\nprecio del plan sin IVA: ' + str(cfm_sin_iva.cfm_sin_iva) +
                        #                       '\nValor a pagar: ' + str(valor_a_pagar))
                _logger.info('Valor a pagar total: ' + str(valor_a_pagar))

            ventas_ids.valor_a_pagar = valor_a_pagar
            # ventas_ids.esquemas_ids = (0, 0, esquemas_totales[id])
