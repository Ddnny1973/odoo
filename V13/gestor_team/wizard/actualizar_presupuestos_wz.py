import logging
import pymssql
import pandas as pd
import os
import base64
import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

param_dic = {
            'server': '20.119.218.50',
            'database': 'TipsII',
            'user': 'sa',
            'password': 'Soluciondig2015'
            }

# Parametros de conexión postgreSQL
param_dic_pg = {
                "host": "192.168.100.200",
                "port": "9016",
                "database": "TEAM",
                "user": "odoo",
                "password": "Gestor2020"
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


# def connect_pg(params_dic_pg):
#     """ Connect to the PostgreSQL database server """
#     conn_pg = None
#     try:
#         # connect to the PostgreSQL server
#         print('Connecting to the PostgreSQL database...')
#         conn_pg = psycopg2.connect(**params_dic_pg)
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(error)
#         raise ValidationError(error)
#     print("Connection successful")
#     return conn_pg


def send_to_channel(self, body):
    ch_obj = self.env['mail.channel']
    # ch = ch_obj.sudo().search([('name', 'ilike', 'general')])
    ch = ch_obj.sudo().search([('name', 'ilike', 'OdooBot'), ('alias_id', '=', 9)])
    body_ok = body

    ch.message_post(attachment_ids=[], body=body_ok,
                    content_subtype='html', message_type='comment',
                    partner_ids=[], subtype='mail.mt_comment')
    return True


class LogActualizacion(models.Model):
    _name = 'gestor.actualizacion.log'
    _description = 'Saldo en Cartera'

    name = fields.Char('Trabajo')
    inicio = fields.Datetime('Inicio')
    fin = fields.Datetime('Fin')


class ActualizarPresupuestosWizard(models.TransientModel):
    _name = "gestor.actualizar.presupuestos.wizard"
    _description = "Actualización de presupuestos"

    fecha_inicio = fields.Date('Fecha inicio',
                               help='Fecha desde donde se va a buscar información en TIPS',
                               )
    fecha_fin = fields.Date('Fecha fin', default=fields.Date.context_today)

    def consulta_tips_comisiones(self):
        inicio_consulta_tips = False
        fin_consulta_tips = False
        inicio_consulta_gestor = False
        fin_consulta_gestor = False
        inicio_proceso = datetime.datetime.now()
        ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_rp_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
        ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'

        if self.fecha_inicio:
            fecha_inicio = self.fecha_inicio
            fecha_fin = self.fecha_fin
        else:
            fecha_fin = fields.Date.today()
            fecha_inicio = fecha_fin - relativedelta(months=3)

        try:
            # Consultando datos de TEPS
            conn = connect(param_dic)
            sql = """
                      SELECT *
                      FROM [TipsII].[dbo].[Gtor_Ventas]
                      where fecha between '{0}' and '{1}'
                  """.format(fecha_inicio, fecha_fin)
            _logger.info('sql_consulta: ' + sql)
            inicio_consulta_tips = datetime.datetime.now()
            consulta_mssql = pd.read_sql_query(sql, conn)
            fin_consulta_tips = datetime.datetime.now()
            duracion_tips = fin_consulta_tips - inicio_consulta_tips

            total_registros_tips = len(consulta_mssql.index)
            _logger.info('Consulta de actualización de presupuestos realizada. Registros encontrados --> ' + str(total_registros_tips))
            exportacion_name = ruta_odoo + 'consulta_comisiones_mssql.txt'
            importacion_name = ruta_bd + 'consulta_comisiones_mssql.txt'
            if os.path.isfile(importacion_name):
                try:
                    os.remove(importacion_name)
                    _logger.info('Archivo eliminado --> ' + importacion_name)
                except Exception as e:
                    _logger.info('No fue posible eliminar el archivo --> ' + e)
            inicio_consulta_gestor = datetime.datetime.now()
            _logger.info('Copiando el archivo para la importación --> ' + exportacion_name)
            consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
            print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
            # Probar con tabla temporar en postgres por temas de rendimiento
            self.env.cr.execute("""truncate table gestor_consulta_comisiones_tips_tmp""")
            self.env.cr.execute("""copy gestor_consulta_comisiones_tips_tmp from %s DELIMITER ',' csv HEADER;""",
                                (importacion_name,)
                                )
            self.env.cr.execute("""select load_comisiones_ventas_tips();""")
            fin_consulta_gestor = datetime.datetime.now()
            duracion_gestor = fin_consulta_gestor - inicio_consulta_gestor
            self.env.cr.commit()
            _logger.info('terminó cruce de actualización de preuspuestos --> ' + str(duracion_gestor))
        except Exception as e:
            # Atrapar error
            print("Ocurrió un error al conectar a SQL Server: %s", e)
            raise ValidationError(e)
        _logger.info('Iniciando consulta de actualización')
        self.env.cr.execute("""select gestor_ejecucion_por_empleado_2 ('2021-03-01', '2021-03-31');""")
        # self.env.cr.execute("""update gestor_presupuestos_detalle_team set ejecutado=presupuesto_ejecucion_responsable(
        #                         employee_id,
        #                         year,
        #                         mes,
        #                         categorias_planes_id);
        #                     """)
        self.env.cr.commit()
        _logger.info('Consulta de actualización terminada')
        fin_proceso = datetime.datetime.now()
        duracion_total = fin_proceso - inicio_proceso
        tiempo_so = duracion_total - duracion_gestor - duracion_tips
        mensaje = '@soporte@gestorconsultoria.com.co Se terminó la consulta de actualización de presupuestos: \nTiempo total TIPS: ' + str(duracion_tips) + \
                  '\nDuración Gestor: ' + str(duracion_gestor) + \
                  '\nDuración SO: ' + str(tiempo_so) + \
                  '\nDuración Total: ' + str(duracion_total) + \
                  '\nRegistros totales: ' + str(total_registros_tips)
        send_to_channel(self, mensaje)
        _logger.info(mensaje)

        # Actualizando kit prepago
        try:
            # Consultando datos de TEPS
            conn = connect(param_dic)
            sql = """
                      SELECT *
                       FROM [Stok].[dbo].[GTor_EquiposFacturadosKitPrepago]
                       where [FechaDeVenta] between '{0}' and '{1}'
                  """.format(fecha_inicio, fecha_fin)
            consulta_mssql = pd.read_sql_query(sql, conn)
            total_registros_tips = len(consulta_mssql.index)
            exportacion_name = ruta_odoo + 'consulta_kit_prepago_mssql.txt'
            importacion_name = ruta_bd + 'consulta_kit_prepago_mssql.txt'
            if os.path.isfile(importacion_name):
                os.remove(importacion_name)
            consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
            print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
            # Probar con tabla temporar en postgres por temas de rendimiento
            self.env.cr.execute("""truncate table gestor_kit_prepagos_team""")      # No se debe eliminar el historiar, se debe encontrar la llave y actualizar
            self.env.cr.execute("""truncate table gestor_kit_prepago_tmp""")
            self.env.cr.execute("""copy gestor_kit_prepago_tmp from %s DELIMITER ',' csv HEADER;""",
                                (importacion_name,)
                                )
            self.env.cr.execute("""select load_kit_prepago_tips();""")
            self.env.cr.commit()
            _logger.info('terminó cruce de actualización de kit prepago. Total registros --> ' + str(total_registros_tips))
        except Exception as e:
            # Atrapar error
            print("Ocurrió un error al conectar a SQL Server: %s", e)
            raise ValidationError(e)

    def download_txt(self):
        res = {}
        op = self.operation == 'sale' and 'VENTAS' or 'COMPRAS'
        fname = '%s_%s_%s_Comprobantes.txt' %(self.company_id.cuit,self.period.replace('-','_'),op)
        path = '/tmp/' + fname
        txtFile = open(path, 'wb')
        for invoice in self.invoice_ids:
            line = ''
            partner = invoice.partner_id.parent_id and invoice.partner_id.parent_id or invoice.partner_id
            line += invoice.date_invoice.replace("-", '') #fecha factura
            txtFile.write(self.clean_accents(line)+'\n')
        txtFile.close()
        data = base64.encodestring(open(path, 'r').read())
        attach_vals = {'name': fname, 'datas': data, 'datas_fname': fname}
        doc_id = self.env['ir.attachment'].create(attach_vals)
        res['type'] = 'ir.actions.act_url'
        res['target'] = 'new'
        res['url'] = "web/content/?model=ir.attachment&id=" + str(
            doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
        return res
