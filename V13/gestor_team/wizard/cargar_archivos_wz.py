import logging
import psycopg2
import pymssql
import os
import pandas as pd
import shutil
import datetime
import csv
import openpyxl as xl
import hashlib

from odoo.exceptions import ValidationError
from odoo import fields, models
from itertools import islice

_logger = logging.getLogger(__name__)


# Connection parameters, yours will be different
param_dic = {
            'server': 'team.soluciondigital.com.co',
            'database': 'TipsII',
            # 'user': 'procesos',
            # 'password': 'TeamC02020*'
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


def send_to_channel(self, body):
    ch_obj = self.env['mail.channel']
    # ch = ch_obj.sudo().search([('name', 'ilike', 'general')])
    ch = ch_obj.sudo().search([('name', 'ilike', 'OdooBot'), ('alias_id', '=', 9)])
    body_ok = body

    ch.message_post(attachment_ids=[], body=body_ok,
                    content_subtype='html', message_type='comment',
                    partner_ids=[], subtype='mail.mt_comment')
    return True


class CargarArchivosWizard(models.TransientModel):
    _name = "gestor.cargar.archivos.wizard"
    _description = "Cargar archivos"

    def _compute_lista_archivos(self):
        archivos_load = ''
        total_archivos = 0
        ruta_odoo = '/mnt/compartida/rp/pendientes'
        for archivo in os.listdir(ruta_odoo):
            archivos_load = archivos_load + archivo + '\n'
            total_archivos += 1
        archivos_load = archivos_load + 'Total archivos a cargar: ' + str(total_archivos)
        return archivos_load

    def getmd5file(self, archivo):
        try:
            hashmd5 = hashlib.md5()
            with open(archivo, "rb") as f:
                for bloque in iter(lambda: f.read(4096), b""):
                    hashmd5.update(bloque)
            return hashmd5.hexdigest()
        except Exception as e:
            print("Error: %s" % (e))
            return ""
        except:
            print("Error desconocido")
            return ""

    lista_archivos = fields.Text('Archivos', default=_compute_lista_archivos)

    def actualizar_venta_tips(self):
        try:
            sp_tips = """
                        EXEC [dbo].[pro_ext_Gtor_ModificarVenta]
                        @Id={0}
                        ,@PlanId={1}
                        ,@Min={2}
                        ,@Iccid=null
                        ,@Imei={3}
                        ,@Fecha='{4}'
                        ,@CoId=null
                        ,@TipoDeActivacionId=null
                        ,@EquipoId={5};
                      """.format(self.venta_id_tips,
                                 self.plan_tips_id.codigo_id,
                                 self.min_tips,
                                 self.imei_tips,
                                 self.fecha_tips,
                                 self.equipo)
            # raise ValidationError(sp_tips)
            # raise ValidationError(self.venta_id)
            conn = connect(param_dic)
            cursor = conn.cursor()
            cursor.execute(sp_tips)
            conn.commit()
            reporte = 'Actualización en TIPS Exitosa'
            send_to_channel(self, reporte)
            raise ValidationError('Actualización exitosa!')
        except Exception as error:
            # conn.rollback()
            raise ValidationError(error)

    def cargar_archivos(self):
        # Rutas
        # ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_rp_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
        inicio_procesamiento = False
        fin_procesamiento = False
        nombre_archivo_xls = ''
        inicio_carga = datetime.datetime.now()
        ruta_odoo = '/mnt/compartida/rp/'
        ruta_odo_procesados = ruta_odoo
        # ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'
        ruta_bd = '/var/lib/postgresql/data/compartida/rp/'

        ruta_pendientes = 'pendientes/'
        ruta_procesado = 'procesados/'

        ruta_odoo = ruta_odoo + ruta_pendientes
        ruta_bd = ruta_bd + ruta_pendientes

        tipo = 'Archivos \n'
        archivos_pendientes = []

        total_archivos = len(os.listdir(ruta_odoo))

        for archivo in os.listdir(ruta_odoo):
            log = []
            total_registros = 0
            inicio_procesamiento = datetime.datetime.now()
            # Cargando archivo a Pandas para ver su número de ccolumn_name
            nombre_archivo = ruta_odoo + archivo
            nombre_archivo_bd = ruta_bd + archivo
            _logger.info(nombre_archivo)

            fecha = datetime.datetime.now()
            filename = archivo + "-{}.txt".format(fecha.strftime("%Y-%m-%d-%H%M%S"))
            nombres_archivo_procesado = ruta_odo_procesados + ruta_procesado + filename

            root_ext = os.path.splitext(nombre_archivo)
            hash = self.getmd5file(nombre_archivo)
            # raise ValidationError(hash)
            if root_ext[1] in ('.xls', '.xlsx', '.xlsb'):
                if root_ext[1] == '.xlsb':
                    try:
                        archivo_leido = pd.read_excel(nombre_archivo, engine='pyxlsb', converters={'ICCID': str})
                    except:
                        archivo_leido = pd.read_excel(nombre_archivo, engine='pyxlsb')
                else:
                    try:
                        archivo_leido = pd.read_excel(nombre_archivo, sheet_name=0, index_col=None, converters={'ICCID': str})
                    except:
                        archivo_leido = pd.read_excel(nombre_archivo, sheet_name=0, index_col=None)
                columnas_pd = archivo_leido.columns
                total_registros = len(archivo_leido.index)
                a = root_ext[0].split("/")
                nArchivo = a[len(a)-1]
                nombre_archivo_xls = nombre_archivo
                nombre_archivo = ruta_odoo + nArchivo + '.csv'
                nombre_archivo_bd = ruta_bd + nArchivo + '.csv'
                _logger.info('Total registros leidos tipo XLS: ' + str(total_registros))
                try:
                    archivo_leido.to_csv(nombre_archivo, header=True, index=False, sep=';', encoding='utf-8')
                except:
                    archivo_leido.to_csv(nombre_archivo, header=True, index=False, sep=',', encoding='utf-8')
            else:
                try:
                    archivo_leido = pd.read_csv(nombre_archivo, sep=';', index_col=False, encoding='utf8', error_bad_lines=False)
                except:
                    archivo_leido = pd.read_csv(nombre_archivo, sep=',', index_col=False, encoding='utf8', error_bad_lines=False)
                total_registros = len(archivo_leido)
                _logger.info('Total registros leidos tipo CSV: ' + str(total_registros))
                archivo_leido.to_csv(nombre_archivo, header=True, index=False, sep=';', encoding='utf-8')
            columnas_pd = archivo_leido.columns
            _logger.info('Columnas archivo original: --> ')
            _logger.info(columnas_pd)
            columnas = columnas_pd.values.tolist()
            # Tratamiento especial archivo extra grande
            if 'ICCID - (Colocar el Iccid de primero) ' in columnas:
                archivo_leido = archivo_leido.iloc[:, 0:5]
                columnas_pd = archivo_leido.columns
                columnas = columnas_pd.values.tolist()
                archivo_leido.to_csv(nombre_archivo, header=True, index=False, sep=';', encoding='utf-8')
                # crear archivo desde aquí y realizar la actualización de una vez completa luego eliminar el archivo
            if len(columnas) == 1:
                for i in columnas:
                    columnas = i.split(',')
            columnas_corregido = []
            contador = 1
            contador_de_columnas = 0
            for i in columnas:
                # _logger.info('Columna ' + str(contador_de_columnas) + ' --> ' + i)
                nombre_campo = i.upper().replace(' ', '_').replace("'", "").replace('.', '_').replace('-', '_').replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
                if nombre_campo in columnas_corregido:
                    nombre_campo = nombre_campo + '_' + str(contador)
                    contador += 1
                columnas_corregido.append(nombre_campo)
                contador_de_columnas += 1
            importacion_exitosa = 0
            # Consultando columnas de los diferentes tipos de archivo Existentes
            contador = 1
            contador_archivos = 0
            for tipos_archivo in self.env['gestor.archivos.team'].search([]):
                lista_columnas = []
                tipo_Archivo_a_procesar = tipos_archivo.name
                contador = 1
                for columnas in tipos_archivo.columnas_ids:
                    nombre_campo = columnas.columna_archivo.upper().replace(' ', '_').replace("'", "").replace('.', '_').replace('-', '_').replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
                    if nombre_campo in lista_columnas:
                        nombre_campo = nombre_campo + '_' + str(contador)
                        contador += 1
                    lista_columnas.append(nombre_campo)
                columnas_corregido = [element.replace('\'', '').replace("'", "") for element in columnas_corregido]

                lista_columnas = [element.upper().replace(' ', '_').replace('.', '_').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U').replace('Ñ', 'N').replace('-', '_').replace('.', '_') for element in lista_columnas]
                lista_columnas = [element.replace('ÃŠ', 'U').replace("Ã\x8d", "I").replace("Ã“", "O").replace("Ã‘", "N") for element in lista_columnas]
                lista_columnas = [element.replace('\'', '').replace("'", "") for element in lista_columnas]

                if columnas_corregido == lista_columnas:
                    _logger.info('Columnas iguales. Tipo de archivo --> ' + tipo_Archivo_a_procesar)
                    _logger.info('Revisando valores de tabla de archivo --> ' + tipos_archivo.name)
                    # _logger.info('Revisando valores de tabla de archivo modelo --> ' + tipos_archivo.modelo_id.model.replace(".", "_") or '')
                    tipo = tipo + 'Nombre archivo: ' + nombre_archivo + ' Tipo: ' + tipo_Archivo_a_procesar
                    if tipo_Archivo_a_procesar == 'HOGAR':
                        table_name = 'gestor_hogar_team'
                    elif tipo_Archivo_a_procesar == 'SIMS_PRENDIDAS':
                        table_name = 'gestor_sims_prendidas'
                    elif tipo_Archivo_a_procesar in ('AEPAS', 'AEPAS 2'):
                        table_name = 'gestor_aepas_team'
                    elif tipo_Archivo_a_procesar in ('PYMES', 'PYMES 2'):
                        table_name = 'gestor_pyme_team'
                    elif tipo_Archivo_a_procesar == 'CONSOLIDADO VENTAS':
                        table_name = 'gestor_aepas_team'
                    elif tipo_Archivo_a_procesar == 'CALLIDUS':
                        table_name = 'gestor_pago_comision'                       
                    else:
                        # table_name = 'gestor_rp_team'
                        table_name = tipos_archivo.modelo_id.model
                        if table_name:
                            table_name = table_name.replace(".", "_")
                        else:
                            table_name = ''
                    # raise ValidationError('Tipo archivo --> ' + tipo_Archivo_a_procesar)
                    _logger.info('Tipo archivo a procesar (pasando al SQL) --> ' + tipo_Archivo_a_procesar)
                    _logger.info('Tabla a insertar (pasando al SQL) --> ' + table_name)
                    if tipo_Archivo_a_procesar == 'Tipo Activación':
                        _logger.info('Columnas corregido --> ')
                        _logger.info( columnas_corregido)
                        _logger.info('lista_columnas --> ' )
                        _logger.info( lista_columnas)
                    if tipo_Archivo_a_procesar == 'Tipo Activación':
                        control_actualizacion = 0
                        for i in archivo_leido.index:
                            control_actualizacion = i
                            contrato_tmp = archivo_leido["TELE_NUMB-CONTRATO"][i]
                            if archivo_leido["TIPO_LEGALIZACION"][i] == 'Venta Digital':
                                tipo_legalizacion = 3
                            elif archivo_leido["TIPO_LEGALIZACION"][i] == 'Venta Documental':
                                tipo_legalizacion = 1
                            else:
                                tipo_legalizacion = 2
                            # Consultar id venta en TIPS
                            # Consultando datos de TEPS
                            conn = connect(param_dic)
                            sql = """
                                    SELECT [Venta Id] as venta_id
                                    FROM [TipsII].[dbo].[Gtor_Ventas]
                                    where [Min] = '{0}'
                                  """.format(contrato_tmp)
                            consulta_mssql = pd.read_sql_query(sql, conn)
                            venta_id = consulta_mssql["venta_id"][0]
                            try:
                                a = """
                                            EXEC [dbo].[pro_ext_Gtor_ModificarVenta]
                                            @Id={0}
                                            ,@TipoDeActivacionId={1};
                                          """.format(venta_id,
                                                     tipo_legalizacion)
                                # raise ValidationError(sp_tips)
                                # raise ValidationError(self.venta_id)
                                conn = connect(param_dic)
                                cursor = conn.cursor()
                                #cursor.execute(sp_tips)
                                cursor.execute(a)
                                conn.commit()
                                importacion_exitosa = 1
                            except Exception as error:
                                # conn.rollback()
                                importacion_exitosa = 0
                                _logger.info( error)
                        if os.path.exists(nombre_archivo):
                            with open(nombre_archivo, 'rb') as forigen:
                                with open(nombres_archivo_procesado, 'wb') as fdestino:
                                    shutil.copyfileobj(forigen, fdestino)
                                    try:
                                        os.remove(nombre_archivo)
                                    except:
                                        _logger.info('No se pudo remover el archivo: --> ' + nombre_archivo_xls)
                        if os.path.exists(nombre_archivo_xls):
                            try:
                                os.remove(nombre_archivo_xls)
                            except:
                                _logger.info('No se pudo remover el archivo: --> ' + nombre_archivo_xls)
                        log.append({'name': archivo,
                                    'registros': total_registros,
                                    'estado': 'Procesado Exitoso',
                                    'fecha': datetime.datetime.now(),
                                    'hash': hash})
                        self.env['gestor.log.carga.archivos'].create(log)
                        # self.env.cr.commit()    # raise ValidationError(error)

                    if tipo_Archivo_a_procesar != 'Tipo Activación':
                        # log_archivos = self.env['gestor.log.carga.archivos'].search([('hash', '=', hash)])
                        # if log_archivos:
                        #     log_archivos.inicio = datetime.datetime.now()
                        #     log_archivos.observaciones = 'El hash ya existía, se actualiza fecha inicio del proceso'
                        #     inicio_procesamiento = datetime.datetime.now()
                        # else:
                        #     log.append({'name': archivo,
                        #         'registros': 0,
                        #         'estado': 'En proceso',
                        #         'fecha': datetime.datetime.now(),
                        #         'inicio': inicio_procesamiento,
                        #         'mecanismo': 'Python',
                        #         'hash': hash})
                        #     self.env['gestor.log.carga.archivos'].create(log)
                        # # self.env.cr.commit()
                        # archivos_pendientes.append(nombre_archivo)
                        a = self.env.cr.execute("""select load_csv_file(
                                                %s, %s, %s, %s, %s, %s);""",
                                                (table_name, nombre_archivo_bd, tipo_Archivo_a_procesar, len(lista_columnas), self.env.user.id, hash))
                        # self.env.cr.commit()
                        # if tipo_Archivo_a_procesar == 'HOGAR':
                        #     self.env.cr.execute("""update gestor_hogar_team x set estado_ap = (select estado_ap from gestor_hogar_team y
                        #                             where y.estado_ap is not null
                        #                             and y.cuenta = x.cuenta
                        #                             and y.ot = x.ot
                        #                             limit 1)
                        #                             where x.estado_ap is null;
                        #
                        #                             update gestor_captura_hogar_team a set
                        #                             estado_venta =
                        #                             (select
                        #                                 (select id from gestor_estados_ap_team where name=coalesce(d.name, b.tipo_registro))
                        #                                     from gestor_hogar_team b
                        #                                     left join gestor_estados_ap_team d on d.id=b.estado_ap
                        #                                     where  a.cuenta=b.cuenta and a.ot=b.ot
                        #                                     and b.tipo_registro='Instalada'
                        #                                     union
                        #                                     select
                        #                                     (select id from gestor_estados_ap_team where name=coalesce(d.name, b.tipo_registro))
                        #                                     from gestor_hogar_team b
                        #                                     left join gestor_estados_ap_team d on d.id=b.estado_ap
                        #                                     where  a.cuenta=b.cuenta and a.ot=b.ot
                        #                                     and b.tipo_registro='Digitada'
                        #                                     and (b.ot, b.cuenta) not in (select c.ot, c.cuenta
                        #                                     from gestor_hogar_team c where a.cuenta=c.cuenta and a.ot=c.ot and tipo_registro='Instalada'
                        #                                 )
                        #                                 limit 1
                        #                             )
                        #                             WHERE estado_venta is null or estado_venta = 1;
                        #
                        #                             update gestor_captura_hogar_team a set valor_comision=(select sum(b.valor_comision) from gestor_captura_hogar_detalle_agrupado_team b
						# 										  where b.id=b.captura_hogar_id);
                        #
                        #                          """
                        #                         )
                        #     self.env.cr.commit()

                    if a is None:
                        importacion_exitosa = 1
                    break
                else:
                    _logger.info('Columnas diferentes. Tipo de archivo --> ' + tipo_Archivo_a_procesar)
                    if tipo_Archivo_a_procesar == 'SIMS_PRENDIDAS':
                        _logger.info('Columnas corregido --> ')
                        _logger.info(columnas_corregido)
                        _logger.info('lista_columnas --> ' )
                        _logger.info( lista_columnas)
            fin_procesamiento = datetime.datetime.now()
            duracion_procesamiento = fin_procesamiento - inicio_procesamiento
            # duracion_procesamiento = False

            if importacion_exitosa == 1:
                if os.path.exists(nombre_archivo):
                    with open(nombre_archivo, 'rb') as forigen:
                        with open(nombres_archivo_procesado, 'wb') as fdestino:
                            shutil.copyfileobj(forigen, fdestino)
                            try:
                                os.remove(nombre_archivo)
                            except:
                                _logger.info('No se pudo remover el archivo: --> ' + nombre_archivo_xls)
                if os.path.exists(nombre_archivo_xls):
                    try:
                        os.remove(nombre_archivo_xls)
                    except:
                        _logger.info('No se pudo remover el archivo: --> ' + nombre_archivo_xls)
                log_archivos = self.env['gestor.log.carga.archivos'].search([('hash', '=', hash)])
                # if log_archivos:
                #     log_archivos.registros: total_registros
                #     log_archivos.inicio = inicio_procesamiento
                #     log_archivos.fin = fin_procesamiento
                #     log_archivos.fecha = datetime.datetime.now()
                #     log_archivos.duracion = duracion_procesamiento

                # else:
                log.append({'name': archivo,
                            'registros': total_registros,
                            'estado': 'Procesado Exitoso',
                            # 'fecha': datetime.datetime.now(),
                            'duracion': duracion_procesamiento,
                            # 'fin': fin_procesamiento,
                            # 'inicio': inicio_procesamiento,
                            'mecanismo': 'Python',
                            'hash': hash})
                # self.env['gestor.log.carga.archivos'].create(log)
                # self._actualizar_recalculos()
                # self.env.cr.commit()
            else:
                log.append({'name': archivo,
                            'registros': 0,
                            'estado': 'Procesado No Exitoso',
                            'fecha': datetime.datetime.now(),
                            'duracion': duracion_procesamiento,
                            'hash': hash})
                self.env['gestor.log.carga.archivos'].create(log)
                archivos_pendientes.append(nombre_archivo)
            contador += 1

        fin_carga = datetime.datetime.now()
        duracion_tips = fin_carga - inicio_carga
        # raise ValidationError(duracion_tips)
        lista_archivos_pendientes = 'Archivos pendientes por subir: \n'
        for pendientes in archivos_pendientes:
            lista_archivos_pendientes = lista_archivos_pendientes + pendientes + '\n'
        reporte = 'Inicio carga: ' + str(inicio_procesamiento) + '\nLista de archivos pendientes: ' + '\n' + lista_archivos_pendientes + '\n' + 'Tiempo total del proceso: ' + str(duracion_tips)
        if total_archivos > 0:
            send_to_channel(self, reporte)
