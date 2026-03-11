import logging
import psycopg2
import pymssql
import pandas as pd
import os
import base64
import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

from sqlalchemy import create_engine

engine = create_engine('postgresql://odoo:Gestor@localhost:5432/TEAM')

_logger = logging.getLogger(__name__)

# Connection parameters, yours will be different
# param_dic = {
#            'server': 'team.soluciondigital.com.co',
#            'database': 'TipsII',
#            'user': 'procesos',
#            'password': 'TeamC02020*'
#            }

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


class CruzarRPWizard(models.TransientModel):
    _name = "gestor.cruce.rp.wizard"
    _description = "Cruce RP con TIPS II"

    fecha_inicio = fields.Date('Fecha inicio', help='Fecha desde donde se va a buscar información en TIPS')
    fecha_fin = fields.Date('Fecha fin', default=fields.Date.context_today)
    tipo_archivo = fields.Many2one('gestor.archivos.team')
    fecha_inicio_rp = fields.Date('Fecha inicio RP', help='Fecha desde donde se va a buscar información en RP')

    @api.onchange('fecha_inicio')
    def _fecha_rp(self):
        if self.fecha_inicio:
            self.fecha_inicio_rp = self.fecha_inicio - relativedelta(months=1)

    def consulta_tips(self, lcFinicio, lcfin):
        if lcFinicio == '2022-01-01' and lcfin == '2022-01-01':
            lcFfin = fields.Date.context_today(self)
        else:
            lcFfin = lcfin
        ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_rp_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
        ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'
        try:
            # Consultando datos de TEPS
            conn = connect(param_dic)
            sql = """
                      SELECT *
                      FROM [TipsII].[dbo].[Gtor_Ventas]
                      where fecha between '{0}' and '{1}'
                  """.format(lcFinicio, lcFfin)
            consulta_mssql = pd.read_sql_query(sql, conn)
            total_registros_tips = len(consulta_mssql.index)
            _logger.info('Total registros: ' + str(total_registros_tips))
            exportacion_name = ruta_odoo + 'consulta_mssql.txt'
            importacion_name = ruta_bd + 'consulta_mssql.txt'
            if os.path.isfile(importacion_name):
                os.remove(importacion_name)
            consulta_mssql.to_csv(exportacion_name, index=False, encoding='utf-8-sig')
            print('Conexión exitosa usando la clase de conexión. Total registros: ' + str(total_registros_tips))
            # Probar con tabla temporar en postgres por temas de rendimiento
            self.env.cr.execute("""truncate table gestor_consulta_ventas_tips_tmp""")
            self.env.cr.commit()
            self.env.cr.execute("""copy gestor_consulta_ventas_tips_tmp from %s DELIMITER ',' csv HEADER;""",
                                (importacion_name,)
                                )
            self.env.cr.commit()
            self.env.cr.execute("""select load_ventas_tips();""")
            self.env.cr.commit()
            _logger.info('Terminó la consulta a TIPS')
        except Exception as e:
            # Atrapar error
            print("Ocurrió un error al conectar a SQL Server: %s", e)
            raise ValidationError(e)

    def cruzar_rp(self):
        # Conectando a SQL Server TIPS
        inicio_consulta_tips = False
        fin_consulta_tips = False
        inicio_consulta_gestor = False
        fin_consulta_gestor = False
        inicio_proceso = datetime.datetime.now()
        try:
            # Consultando datos de TIPS
            inicio_consulta_tips = datetime.datetime.now()
            self.consulta_tips(self.fecha_inicio, self.fecha_fin)
            fin_consulta_tips = datetime.datetime.now()
            duracion_tips = fin_consulta_tips - inicio_consulta_tips

            # Buscando columnas para el cruce
            parametros_join = False
            contador = 1
            for columnas_key in self.env['gestor.archivos.columnas.team'].search([('columna_key', '=', True),
                                                                                  ('column_id.id', '=', self.tipo_archivo.id)]):
                if contador == 1:
                    parametros_join = 'on a.' + columnas_key.columna_modelo + '=b.' + columnas_key.columna_archivo
                else:
                    parametros_join = parametros_join + ' and a.' + columnas_key.columna_modelo + '=b.' + columnas_key.columna_archivo
                contador += 1

            # gestor_archivo = self.env['gestor.archivos.team'].search([('id', '=', self.tipo_archivo.id)])
            # query = gestor_archivo.query

            inicio_consulta_gestor = datetime.datetime.now()
            # sql_consulta = """select cruce_ventas_tips(%s, $s);"""
            sql_consulta = "select cruce_ventas_tips(" + str(self.env.user.id) + ", '" + str(self.fecha_inicio_rp) + "');"
            _logger.info('sql_consulta: ' + sql_consulta)
            # self.env.cr.execute(sql_consulta, (str(self.env.user.id), str(self.fecha_inicio_rp),))
            self.env.cr.execute(sql_consulta)
            _logger.info('Terminó el cruce en postgresql.')
            registros = self.env['gestor.cruce.ventas.tips'].search_count([])
            fin_consulta_gestor = datetime.datetime.now()
            duracion_gestor = fin_consulta_gestor - inicio_consulta_gestor

            self.env.cr.commit()

            fin_proceso = datetime.datetime.now()
            duracion_total = fin_proceso - inicio_proceso
            tiempo_so = duracion_total - duracion_gestor - duracion_tips
            mensaje = '@soporte@gestorconsultoria.com.co Se terminó la consulta Cruce Ventas: ' + \
                      '\nHora de inicio: ' + str(inicio_proceso) + \
                      '\nTiempo total TIPS: ' + str(duracion_tips) + \
                      '\nDuración Gestor: ' + str(duracion_gestor) + \
                      '\nDuración SO: ' + str(tiempo_so) + \
                      '\nDuración Total: ' + str(duracion_total) + \
                      '\nRegistros totales: ' + str(registros)
            send_to_channel(self, mensaje)

            # Buscando repetidos
            # Create an engine instance
            engine = create_engine('postgresql+psycopg2://odoo:Gestor2020@192.168.100.200:9016/TEAM')
            df = pd.read_sql("SELECT * FROM gestor_cruce_ventas_tips", engine)

            min_tips = df["min_tips"].str.split('.', 1, expand=True)
            if len(min_tips.columns) == 1:
                min_tips.columns = ['min_tips_1']
            else:
                min_tips.columns = ['min_tips_1', 'min_tips_2']
            df = pd.concat([df, min_tips], axis=1)

            # raise ValidationError(df)
            duplicados = df[df.duplicated(subset=['min_tips_1', 'imei_tips', 'tipo_de_plan_tips', 'iccid_tips'], keep=False)]
            for i in duplicados.index:
                # raise ValidationError(duplicados['id'][i])
                registro = self.env['gestor.cruce.ventas.tips'].search([('id', '=', duplicados['id'][i])])
                registro.posible_duplicado = True

            # # Desmarcando mismo ID_Ventas
            # raise ValidationError(duplicados.venta_id_tips)
            no_duplicados = duplicados[duplicados.duplicated(subset=['id_tips'], keep=False)]
            # raise ValidationError(no_duplicados)
            for i in no_duplicados.index:
                # raise ValidationError(duplicados['id'][i])
                registro = self.env['gestor.cruce.ventas.tips'].search([('id', '=', no_duplicados['id'][i])])
                registro.posible_duplicado = False

            # raise ValidationError('df: ' + str(len(df)) + '\nduplicados: ' + str(len(duplicados)))
            # raise ValidationError('df: ' + str(len(df)))

            """
            # Descargando el archivo
            res = {}
            fname = 'Cruce_{}.csv'.format(self.tipo_archivo.name)
            data = base64.b64encode(open(exportacion_name, 'rb').read())
            attach_vals = {'name': fname, 'datas': data}
            doc_id = self.env['ir.attachment'].create(attach_vals)
            res['type'] = 'ir.actions.act_url'
            res['target'] = 'new'
            # res['url'] = "web/content/?model=ir.attachment&id=" + str(
            #    doc_id.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(doc_id.name)
            res['url'] = "web/content/?model=ir.attachment&id=" + str(
                doc_id.id) + "&filename_field=name&field=datas&download=true&filename=" + str(doc_id.name)
            return res
            # raise ValidationError('El resultado se encuentra en esta ruta: ' + exportacion_name)
            """

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
            line+= invoice.date_invoice.replace("-", '') #fecha factura
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
