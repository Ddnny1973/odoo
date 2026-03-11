import logging
import pymssql
import pandas as pd
import os

from odoo.exceptions import ValidationError
from odoo import models

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


class ActualizarSaldoEnCarteraWizard(models.TransientModel):
    _name = "gestor.cartera.wizard"
    _description = "Actualizar Saldo en cartera desde STOK"

    def actualizar_Saldo_cartera(self):
        ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_rp_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
        ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'

        try:
            # Consultando datos de STOCK
            conn = connect(param_dic)
            sql = """
                    SELECT  [Sucursal]
                            ,sum([SaldoEnCartera])
                    FROM [Stok].[dbo].[Gtor_Cartera]
                    group by [Sucursal]
                  """
            consulta_mssql = pd.read_sql_query(sql, conn)
            total_registros_tips = len(consulta_mssql.index)
            exportacion_name = ruta_odoo + 'consulta_mssql.txt'
            importacion_name = ruta_bd + 'consulta_mssql.txt'
            if os.path.isfile(exportacion_name):
                os.remove(exportacion_name)
            consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
            print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
            # Probar con tabla temporar en postgres por temas de rendimiento
            self.env.cr.execute("""truncate table gestor_cartera_team""")
            self.env.cr.execute("""copy gestor_cartera_team (name, saldo)from %s DELIMITER ',' csv HEADER;""",
                                (importacion_name,)
                                )
            self.env.cr.execute("""update gestor_cartera_team set create_uid=%s, create_date=now();""", (self.env.uid,))
            self.env.cr.commit()
        except Exception as e:
            # Atrapar error
            print("Ocurrió un error al conectar a SQL Server: %s", e)
            raise ValidationError(e)

        # Creando tabla temporal para descuentos
        try:
            # Consultando datos de STOCK
            conn = connect(param_dic)
            sql = """
                    SELECT * FROM [Stok].[dbo].[Gtor_saldos_descuentos]
                  """
            consulta_mssql = pd.read_sql_query(sql, conn)
            total_registros_tips = len(consulta_mssql.index)
            exportacion_name = ruta_odoo + 'consulta_mssql.txt'
            importacion_name = ruta_bd + 'consulta_mssql.txt'
            if os.path.isfile(exportacion_name):
                os.remove(exportacion_name)
            consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
            print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
            # Probar con tabla temporar en postgres por temas de rendimiento
            self.env.cr.execute("""truncate table gestor_cartera_stok_tmp""")
            self.env.cr.execute("""copy gestor_cartera_stok_tmp (cliente,
                                                                 tipoidentificacion,
                                                                 identificacion,
                                                                 fecha,
                                                                 descuento,
                                                                 saldo,
                                                                 detalle,
                                                                 idfactura,
                                                                 numfactura,
                                                                 PrecioVentaDetalle) from %s DELIMITER ',' csv HEADER;""",
                                (importacion_name,)
                                )

            self.env.cr.execute("""update descuentos_teams set active=False
                                   where tipodeprestamo in (select id from tipo_descuento where saldo_stok is true)
                                """)
            self.env.cr.execute("""insert into descuentos_teams
                                    (name, tipodeprestamo, fecha_aplicacion, id_factura_stok, id_detalle_factura_stok,
                                    valorprestamo, valorcuota, valoraplicar, saldo, num_factura, cuotas, active)
                                    select
                                    (select id from hr_employee where identification_id=identificacion) as name,
                                    (select id from tipo_descuento where name=descuento) as tipodeprestamo,
                                    fecha as fecha_aplicacion,
                                    idfactura as id_factura_stok,
                                    avg(detalle) as id_detalle_factura_stok,
                                    avg(saldo) as valorprestamo,
                                    avg(saldo) as valorcuota,
                                    0 valoraplicar,
                                    avg(saldo),
                                    numfactura as num_factura,
                                    (select cuotas from tipo_descuento where name=descuento) as tipodeprestamo,
                                    True as Activo
                                    from gestor_cartera_stok_tmp a
                                    where identificacion in (select identification_id from hr_employee)
                                    group by identificacion, descuento, fecha, numfactura, idfactura
                                    ON CONFLICT (name, tipodeprestamo, fecha_aplicacion, num_factura)
                                    DO UPDATE SET valorprestamo = EXCLUDED.valorprestamo,
                                                  valorcuota = EXCLUDED.valorcuota,
                                                  valoraplicar = 0,
                                                  saldo = EXCLUDED.saldo,
                                                  active = True;
                                """
                                )
            # self.env.cr.execute("""update gestor_cartera_team set create_uid=%s, create_date=now();""", (self.env.uid,))
            self.env.cr.commit()
        except Exception as e:
            # Atrapar error
            print("Ocurrió un error al conectar a SQL Server: %s", e)
            raise ValidationError(e)

        # try:
        #     conn = connect(param_dic)
        #     with conn.cursor() as cursor:
        #         # Desactivar todos los planes
        #         # Consultamos la lista de planes
        #         sql = """
        #                 SELECT * FROM [Stok].[dbo].[Gtor_saldos_descuentos]
        #               """
        #         descuentos = pd.read_sql_query(sql, conn)
        #         # Recorrer y validar equipo
        #         for i in descuentos.index:
        #             cliente = descuentos['CLIENTE'][i]
        #             tipo_identificacion = descuentos['TIPOIDENTIFICACION'][i]
        #             identificacion = descuentos['IDENTIFICACION'][i]
        #             fecha = descuentos['FECHA'][i]
        #             descuento = descuentos['DESCUENTO'][i]
        #             saldo = descuentos['SALDO'][i]
        #             # id_cxc = descuentos['id_cxc'][i]
        #             id_factura = descuentos['IDFACTURA'][i]
        #             id_detalle_factura = descuentos['DETALLE'][i]
        #             num_factura = descuentos['NUMFACTURA'][i]
        #             precio_venta_detalle = descuentos['PrecioVentaDetalle'][i]
        #             # id_producto = descuentos['id_producto'][i]
        #
        #             empleado_id = self.env['hr.employee'].search([('identification_id', '=', identificacion),
        #                                                           '|', ('active', '=', True), ('active', '=', False) ])
        #             tipo_prestamo = self.env['tipo.descuento'].search([('name', '=', descuento)])
        #
        #             descuento_existente = self.env['descuentos.teams'].search([('name', '=', empleado_id.id),
        #                                                                        ('tipodeprestamo', '=', tipo_prestamo.id),
        #                                                                        ('fecha_aplicacion', '=', fecha),
        #                                                                        ('id_factura_stok', '=', id_factura),
        #                                                                        ('id_detalle_factura_stok', '=', id_detalle_factura)])
        #
        #             # count = self.env['descuentos.teams'].search_count([('name', '=', empleado_id.id),
        #             #                                                    ('tipodeprestamo', '=', tipo_prestamo.id),
        #             #                                                    ('fecha_aplicacion', '=', fecha),
        #             #                                                    ('id_factura_stok', '=', id_factura),
        #             #                                                    ('id_detalle_factura_stok', '=', id_detalle_factura)])
        #
        #             if len(descuento_existente) != 0:
        #                 descuento_existente.valorprestamo = precio_venta_detalle
        #                 descuento_existente.valorcuota = precio_venta_detalle
        #                 descuento_existente.valoraplicar = 0
        #                 descuento_existente.saldo = saldo
        #             else:
        #                 if len(empleado_id) != 0:
        #                     self.env['descuentos.teams'].create({'name': empleado_id.id,
        #                                                          'tipodeprestamo': tipo_prestamo.id,
        #                                                          'fecha_aplicacion': fecha,
        #                                                          'id_factura_stok': id_factura,
        #                                                          'id_detalle_factura_stok': id_detalle_factura,
        #                                                          'valorprestamo': precio_venta_detalle,
        #                                                          'valorcuota': precio_venta_detalle,
        #                                                          'valoraplicar': 0,
        #                                                          'saldo': saldo,
        #                                                          'num_factura': num_factura,
        #                                                          })
        #
        #         self.env.cr.commit()
        #     # _logger.info('Terminó')
        # except Exception as e:
        #     print("Ocurrió un error al conectar a SQL Server: %s", e)
        #     raise ValidationError(e)
    def actualizar_Empleados_TIPSS(self):
        for reg in self:
            ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_rp_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
            ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'

            try:
                # Consultando datos de STOCK
                conn = connect(param_dic)
                sql = """
                        SELECT [UsuarioId]
                              ,[NombreDeUsuario]
                              ,[Nombre]
                              ,[Identificacion]
                        FROM [TipsII].[dbo].[Gtor_ListadoDeUsuarios]
                      """
                consulta_mssql = pd.read_sql_query(sql, conn)
                total_registros_tips = len(consulta_mssql.index)
                exportacion_name = ruta_odoo + 'consulta_mssql.txt'
                importacion_name = ruta_bd + 'consulta_mssql.txt'
                if os.path.isfile(exportacion_name):
                    os.remove(exportacion_name)
                consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
                print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
                self.env.cr.execute("""TRUNCATE TABLE gestor_listadodeusuarios_tips""")
                self.env.cr.execute("""copy gestor_listadodeusuarios_tips (user_id, nombre_usuario, nombre, identificacion) from %s DELIMITER ',' csv HEADER;""",
                                    (importacion_name,)
                                    )
                self.env.cr.execute("""update hr_employee a set user_id_tips=(select user_id from gestor_listadodeusuarios_tips b where a.identification_id = b.identificacion limit 1);""")
                self.env.cr.commit()
            except Exception as e:
                # Atrapar error
                print("Ocurrió un error al conectar a SQL Server: %s", e)
                raise ValidationError(e)
