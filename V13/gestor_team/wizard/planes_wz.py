import logging
import pyodbc
import pymssql
import pandas as pd

from odoo.exceptions import ValidationError
from odoo.exceptions import Warning
from odoo import models

_logger = logging.getLogger(__name__)


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


class ActualizarPlanesClaroWizard(models.TransientModel):
    _name = "gestor.actualizar.planes.wizard"
    _description = "Actualizar planes desde TIPS II"

    def actualizar_tipo_planes(self):
        # direccion_servidor = 'team.soluciondigital.com.co'
        nombre_bd = 'TipsII'
        # nombre_usuario = 'procesos'
        # password = 'TeamC02020*'
        # nombre_usuario = 'sa'
        # password = 'Soluciondig2015*'

        try:
            conn = connect(param_dic)
            with conn.cursor() as cursor:
                # Desactivar todos los planes
                # self.env.cr.execute("""update gestor_tipo_plan_team set activo=False;""")
                # Consultamos la lista de planes
                sql = """select a.codigo,
                                       a.nombre,
                                       a.tipodeproducto as cod_tipoproducto,
                                       b.nombre as tipoproducto,
                                       a.visibilidadactual
                                   from plnTiposDePlan AS a
                                   join ventiposdeproducto as b on a.TipoDePlanilla=b.codigo
                               """
                tipo_plan = pd.read_sql_query(sql, conn)
                # Recorrer y validar plan y actualizar
                for i in tipo_plan.index:
                    tipo_codigo = tipo_plan['codigo'][i]
                    nombre = tipo_plan['nombre'][i]
                    tipo_producto = tipo_plan['cod_tipoproducto'][i]
                    tipo_name = tipo_plan['tipoproducto'][i]
                    VisibilidadActual = tipo_plan['visibilidadactual'][i]

                    if VisibilidadActual == 1:
                        activo = True
                    else:
                        activo = False
                    tipo_existente = self.env['gestor.tipo.plan.team'].search([('name', '=', nombre)])
                    count = self.env['gestor.tipo.plan.team'].search_count([('name', '=', nombre)])
                    if count != 0:
                        tipo_existente.name = nombre
                        tipo_existente.activo = activo
                        tipo_existente.tipo_producto = tipo_name
                    else:
                        self.env['gestor.tipo.plan.team'].create({'codigo_id': tipo_codigo,
                                                                  'name': nombre,
                                                                  'tipo_producto': tipo_name,
                                                                  'activo': activo,
                                                                  })
            self.env.cr.commit()
            # _logger.info('Terminó')
        except Exception as e:
            print("Ocurrió un error al conectar a SQL Server: %s", nombre_bd, e)
            raise ValidationError(e)

    def actualizar_equipos_stok(self):
        # direccion_servidor = 'team.soluciondigital.com.co'
        nombre_bd = 'TipsII'
        # nombre_usuario = 'procesos'
        # password = 'TeamC02020*'
        # nombre_usuario = 'sa'
        # password = 'Soluciondig2015*'

        try:
            conn = connect(param_dic)
            with conn.cursor() as cursor:
                # Desactivar todos los planes
                # Consultamos la lista de planes
                sql = """SELECT [Tipo De Producto] AS [tipo_de_producto]
                              ,[Estado] AS [estado]
                              ,[Nombre] AS [nombre]
                              ,[Serializado] AS [serializado]
                          FROM [Stok].[dbo].[Gtor_Equipos]
                    """
                equipos = pd.read_sql_query(sql, conn)
                # Recorrer y validar equipo
                for i in equipos.index:
                    tipo_producto = equipos['tipo_de_producto'][i]
                    estado = equipos['estado'][i]
                    nombre = equipos['nombre'][i]
                    serializado = equipos['serializado'][i]
                    equipo_existente = self.env['gestor.equipos.stock'].search([('name', '=', nombre)])
                    count = self.env['gestor.equipos.stock'].search_count([('name', '=', nombre)])
                    if count != 0:
                        equipo_existente.estado = estado
                        equipo_existente.serializado = serializado
                    else:
                        self.env['gestor.equipos.stock'].create({'name': nombre,
                                                                  'estado': estado,
                                                                  'serializado': serializado,
                                                                  })
                    self.env.cr.commit()
            # _logger.info('Terminó')
        except Exception as e:
            print("Ocurrió un error al conectar a SQL Server: %s", nombre_bd, e)
            raise ValidationError(e)

    def actualizar_equipos_TIPS(self):
        # direccion_servidor = 'team.soluciondigital.com.co'
        nombre_bd = 'TipsII'
        # nombre_usuario = 'procesos'
        # password = 'TeamC02020*'
        # nombre_usuario = 'sa'
        # password = 'Soluciondig2015*'

        try:
            conn = connect(param_dic)
            with conn.cursor() as cursor:
                # Desactivar todos los planes
                # Consultamos la lista de planes
                sql = """SELECT [Equipo] AS [equipo]
                              ,[Id] AS [id]
                          FROM [TipsII].[dbo].[Gtor_TipsEquipos]
                    """
                equipos = pd.read_sql_query(sql, conn)
                # Recorrer y validar equipo
                for i in equipos.index:
                    nombre = equipos['equipo'][i]
                    id_tips = equipos['id'][i]
                    equipos_tips_existente = self.env['gestor.equipos.tips'].search([('id_tips', '=', id_tips),
                                                                                     '|', ('active', '=', False), ('active', '=', True)])
                    # count = self.env['gestor.equipos.tips'].search_count([('id_tips', '=', 10)])
                    # raise ValidationError(equipos_tips_existente.name)
                    if len(equipos_tips_existente) != 0:
                        equipos_tips_existente.active = True
                        equipos_tips_existente.name = nombre
                    else:
                        # raise ValidationError('Nombre: ' + nombre + ' id_tips: ' + str(id_tips))
                        self.env['gestor.equipos.tips'].create({'name': nombre,
                                                                'id_tips': id_tips,
                                                                })

            self.env.cr.commit()
            # _logger.info('Terminó')
        except Exception as e:
            print("Ocurrió un error al conectar a SQL Server: %s", nombre_bd, e)
            raise ValidationError(e)

    def actualizar_planes(self):
        # Actualizando tipo de planes
        planes_actualizados = 0
        planes_creados = 0
        self.actualizar_equipos_stok()
        self.actualizar_equipos_TIPS()
        self.actualizar_tipo_planes()

        try:
            conn = connect(param_dic)
            sql = """
                    SELECT tp.Nombre AS [tipo_de_plan],
                        p.Nombre AS [plan],
                        p.codigo,
                        p.CodigoInterno,
                        p.VisibilidadActual,
                        cp.nombre AS [clasificacion]
                    FROM dbo.plnPlanes AS p INNER JOIN
                        dbo.plnTiposDePlan AS tp ON p.TipoDePlan = tp.Codigo INNER JOIN
                        dbo.plnClasificacionesDePlan cp On p.ClasificacionDePlan = cp.codigo
                    ;
                """
            # where p.VisibilidadActual = 1
            planes = pd.read_sql_query(sql, conn)
            # Desactivar todos los planes
            # self.env.cr.execute("""update gestor_planes_team set activo=False;""")
            # Recorrer y validar plan y actualizar
            _logger.info('Planes a actualizar: ' + str(len(planes)))

            for i in planes.index:
                plan_name = planes['plan'][i]
                tipo_plan = planes['tipo_de_plan'][i]
                codigo = planes['CodigoInterno'][i]
                codigo_interno = planes['codigo'][i]
                clasificacion = planes['clasificacion'][i]
                VisibilidadActual = planes['VisibilidadActual'][i]
                if VisibilidadActual == 1:
                    activo = True
                else:
                    activo = False
                plan_existente = self.env['gestor.planes.team'].search([('name', '=', plan_name)])
                count = self.env['gestor.planes.team'].search_count([('name', '=', plan_name)])
                # Buscando tipo de plan
                tipo_plan_id = self.env['gestor.tipo.plan.team'].search([('name', '=', tipo_plan)]).id or False

                if count != 0:
                    plan_existente.tipo_plan = tipo_plan_id
                    plan_existente.activo = activo
                    plan_existente.codigo = codigo
                    plan_existente.codigo_id = int(codigo_interno)
                    plan_existente.clasificacion = clasificacion
                    planes_actualizados += 1
                else:
                    self.env['gestor.planes.team'].create({'name': plan_name,
                                                           'tipo_plan': tipo_plan_id,
                                                           'activo': activo,
                                                           'codigo': codigo,
                                                           'codigo_id': codigo_interno,
                                                           'clasificacion': clasificacion
                                                           })
                    planes_creados += 1
                self.env.cr.commit()
            _logger.info('Planes actualizados: ' + str(planes_actualizados) +
                         'Planes creados: ' + str(planes_creados))

        except Exception as e:
            error = "Error al actualizar los planes: {0}".format(e)
            raise ValidationError(error)
