# models/vencimientos.py
from odoo import api, fields, models, _
from odoo.http import request
# from odoo.addons.queue_job.job import job
import logging
import io
import os
import pandas as pd
import datetime
import time
import re
import json

import subprocess

from xlsxwriter.workbook import Workbook
import base64

import pickle
import gspread

#API Google
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


_logger = logging.getLogger(__name__)

# Templates
template_dic = {'040-AUTOMOVILES': 'mb-asesores.autosglobal',
                '181-MAS_VIDA': 'mb-asesores.masvida',
                '181-MAS VIDA': 'mb-asesores.masvida',
                '090-SALUD': 'mb-asesores.salud',
                '081-VIDA': 'mb-asesores.vida',
                'BOLIVAR': 'mb-asesores.generico',
                '113-PAC': 'mb-asesores.pac',
                'PROVISION': 'mb-asesores.provision',
                'GENERALES': 'mb-asesores.generico',
                'PRUEBAS': 'mb-asesores.autosglobal',
                }

template_autos = {
                'GLOBAL': 'mb-asesores.autosglobal',
                'BASICO': 'mb-asesores.autosglobal',
                # 'MOTOS': 'mb-asesores.autosmotos',
                # 'MOTOS': 'mb-asesores.autosglobal',
                'CLASICOS': 'mb-asesores.autosclasicos',
                'CLASICO': 'mb-asesores.autosclasicos',
                'PESADOS': 'mb-asesores.autosglobal'
            }

class Vencimientos(models.Model):
    _name = 'mb_asesores.vencimientos'
    _description = 'Vencimientos'

    ramo = fields.Char(string='Ramo')
    id_poliza = fields.Char(string='ID Poliza')
    dni_tomador = fields.Char(string='DNI Tomador')
    tomador = fields.Char(string='Tomador')
    nombrecorto = fields.Char(string='Nombre Corto')
    formadepago = fields.Char(string='Forma de Pago')
    finvigencia = fields.Date(string='Inicio Vigencia')
    aviso = fields.Char(string='Aviso')
    mes = fields.Char(string='Mes')
    year = fields.Integer(string='Año')
    movil = fields.Char(string='Movil')
    email_to = fields.Char(string='Email To')
    mensaje = fields.Char(string='Mensaje')
    archivo = fields.Char(string='Archivo')
    url = fields.Char(string='URL')
    mail_status = fields.Char(string='Estado Correo')
    whatsapp_status = fields.Char(string='Estado Whatsapp')
    hora_ws = fields.Char(string='Hora Whatsapp')
    correo_temporal = fields.Char(string='Correo Temporal')
    tipo_plan = fields.Char(string='Tipo de Plan')
    mensaje_whatsapp = fields.Char(string='Mensaje Whatsapp')
    placa = fields.Char(string='Placa')
    mensaje2 = fields.Char(string='Mensaje2')
    compania = fields.Char(string='Compañía')
    # Campo que relacione con el modelo de correo_enviado
    correo_enviado_id = fields.Many2one('mb_asesores.correo_enviado', string='Correo Enviado', 
                                        compute='_compute_correo_enviado_id', store=True)
    # # Campo que relacione con el modelo mail.message buscando el id_poiliza dentro del campo subjet
    # mail_message_id = fields.Many2one('mail.message', string='Mail Message',
    #                               compute='_compute_mail_message_id', store=True)


    # @api.depends('id_poliza', 'mes', 'year')
    # def _compute_mail_message_id(self):
    #     for record in self:
    #         # Buscar mensajes cuyo asunto contenga el ID de póliza
    #         message = self.env['mail.message'].search([
    #             ('subject', 'ilike', record.id_poliza),
    #             ('model', '=', 'mb_asesores.vencimientos')
    #         ], limit=1, order='date desc')
            
    #         record.mail_message_id = message.id if message else False

    # Añadir la función de cálculo
    @api.depends('id_poliza', 'mes', 'year')
    def _compute_correo_enviado_id(self):
        for record in self:
            # Buscar el correo enviado relacionado por id_poliza, mes y año
            correo = self.env['mb_asesores.correo_enviado'].search([
                ('id_poliza', '=', record.id_poliza),
                ('mes', '=', record.mes),
                ('year', '=', record.year),
                ('tipo_mensaje', '=', 'Mail')
            ], limit=1)
            
            record.correo_enviado_id = correo.id if correo else False

    @api.model
    def print_dummy_message(self):
        # self.ensure_one()
        _logger.info('Entrando en la función print_dummy_message')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Información'),
                'message': _('Este es un mensaje dummy'),
                'sticky': False,
            },
        }

    def button_descarga_vencimientos(self):
        _logger.info('Entrando en la función button_descarga_vencimientos')
        self.env['mb_asesores.vencimientos'].with_delay().descarga_vencimientos('a', k=2)

    # def button_consola(self):
    #     _logger.info('Entrando en la función button_consola')
    #     self.env['mb_asesores.vencimientos'].with_delay().consola('a', k=2)


    # Función para actualizar el estado general en Google config
    @api.model
    def actualizar_estado_general(self, estado=None, mes = None, hojas = None, year = None):
        _logger.info(f'Entrando en la función actualizar_estado_general con estado: {estado}***************')
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
        json = {'observaciones': 'Actualizado'}  # Inicializa el diccionario json
        if estado:  
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': estado})
            _logger.info(f'Estado actualizado a: {estado}')
            json['status'] = estado  # Actualiza el diccionario json con el estado
            
        if mes:
            mes = mes.upper()
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).write({'valor': mes})
            _logger.info(f'Mes actualizado a: {mes}')
            json['mes'] = mes  # Actualiza el diccionario json con el mes

        if year:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).write({'valor': year})
            _logger.info(f'Año actualizado a: {year}')
            json['year'] = year  # Actualiza el diccionario json con el mes


        if hojas:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).write({'valor': hojas.upper()})
            _logger.info(f'Hojas actualizado a: {hojas}')
            json['hojas'] = hojas  # Actualiza el diccionario json con el mes

        if not estado and not mes and not hojas:
            _logger.warning("No se ha recibido el estado ni el mes")
            json['observaciones'] = 'No se ha recibido el estado ni el mes'
            json['status'] = 'error'
            json['mes'] = 'error'
            json['hojas'] = 'error'

        return json

    @api.model
    def get_status(self):
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
        status = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).valor
        mes_FILTRO = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).valor
        hojas = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).valor
        hojas = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')]).valor
        control_mails = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'control_mails')]).valor
        json = {
                    'status': status,
                    'mes': mes_FILTRO,
                    'hojas': hojas,
                    'mensajes_whatsapp': hojas,
                    'control_mails': control_mails
                }
        _logger.warning(json)
        return json


    @api.model      
    def get_mail_status_count(self, mes):
        # Obtener los registros filtrados por el campo mes
        records = self.search([('mes', '=', mes)])
        
        # Contar la cantidad de registros para cada valor de mail_status
        mail_status_count = {}
        for record in records:
            mail_status = record.mail_status
            if mail_status in mail_status_count:
                mail_status_count[mail_status] += 1
            else:
                mail_status_count[mail_status] = 1
        return mail_status_count

    @api.model
    def get_pending_emails(self, mes):
        # Obtener los registros filtrados por mail_status distinto a 'enviado'
        # records = self.env['tu_modelo'].search([('mail_status', '!=', 'enviado')])
        records = self.search([('mail_status', '!=', 'enviado'), ('mes', '=', mes)])
        
        # Crear una lista de tuplas con la póliza y el tomado para cada registro
        pending_emails = [(record.id_poliza, record.tomador) for record in records]
        
        return pending_emails
    
    def generar_registros_mes(self, mes):
        # Suponiendo que tienes una lista llamada registros_mes que contiene los registros del mes
        records = self.search([('mes', '=', mes)])

        # return json_registros_mes
        return records

    @api.model
    def send_mail_report(self, mes):
        recipient="danielpatinofernandez@gmail.com, asistente@mbasesoresenseguros.com"
        # recipient="danielpatinofernandez@gmail.com"
        # Obtener la cantidad de correos por mail_status
        mail_status_count = self.get_mail_status_count(mes)
        
        # Obtener el listado de correos pendientes
        pending_emails = self.get_pending_emails(mes)

        df = pd.DataFrame(self.generar_registros_mes(mes).read())

        # Seleccionar solo los campos especificados del DataFrame
        selected_fields = ['ramo', 'id_poliza', 'dni_tomador', 'tomador', 'nombrecorto', 'formadepago',
                        'finvigencia', 'mes', 'year', 'movil', 'email_to', 'mensaje',
                        'archivo', 'url', 'mail_status', 'whatsapp_status', 'correo_temporal',
                        'tipo_plan', 'mensaje_whatsapp', 'placa', 'mensaje2', 'compania']
        df = df[selected_fields]

        # Reemplazar los valores False con valores vacíos
        df = df.replace(False, '')

        # Crear un buffer para almacenar el archivo Excel
        output = io.BytesIO()

        # Escribir el DataFrame en un archivo Excel en el buffer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Vencimientos', index=False)

        # Obtener los bytes del buffer
        excel_data = output.getvalue()

        # Crear el objeto de archivo adjunto
        attachment = self.env['ir.attachment'].create({
            'name': f'Vencimientos_{mes}.xlsx',
            'datas': base64.b64encode(excel_data),
            # 'datas_fname': f'Vencimientos_{mes}.xlsx',
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary'
        })
        
        # Crear el contenido del correo en formato HTML
        content_html = "<p><strong>Cantidad de correos por estado:</strong></p>"
        content_html += "<ul>"
        for status, count in mail_status_count.items():
            content_html += f"<li>{status.capitalize()}: {count}</li>"
        content_html += "</ul>"
        
        content_html += "<p><strong>Listado de correos pendientes:</strong></p>"
        content_html += "<ul>"
        for poliza, tomado in pending_emails:
            content_html += f"<li>Póliza: {poliza}, Tomado: {tomado}</li>"
        content_html += "</ul>"
        
        # Crear el objeto de correo
        mail = self.env['mail.mail'].create({
            'subject': f'Informe de correos {mes}',
            'body_html': content_html,
            'email_to': recipient,
            'attachment_ids': [(4, attachment.id)],
        })
        
        # Enviar el correo
        mail.send()
        
        return "Correo enviado con éxito"
    
    def variables(self, month=None, year=None, hojas=None, control=None):
        google_drive_config = self.env['google.drive.config']
        # _logger.info(f"**************Entrando a variables ************")
        creds, gc, servicio_drive = google_drive_config.autenticar_google_drive()
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id

        _logger.info(f"Variables despues de autentigar google: id_mb: {id_mb} - month: {month} - year: {year} - hojas: {hojas} - control: {control} ************")

        pathgdrive = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-gdrive')]).valor    
        pathglocal = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-local')]).valor
        nombrearchivovencimientos = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'vencimientos')]).valor
        ejecucion = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'ejecucion')]).valor

        # _logger.info(f"Variables: pathgdrive: {pathgdrive} - pathglocal: {pathglocal} - nombrearchivovencimientos: {nombrearchivovencimientos} - ejecucion: {ejecucion} ************")

        # separar por comas la cadena contol y colocarla en las variables mensajes_whatsapp y control_mails
        if control:
            control = control.split(",")
            mensajes_whatsapp = control[0].strip()
            control_mails = control[1].strip()
            estado_provision = control[2].strip().lower()
        else:
            mensajes_whatsapp = None
            control_mails = None
            estado_provision = None

        if mensajes_whatsapp == None:
            mensajes_whatsapp = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')]).valor.strip()
        else:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')]).write({'valor': mensajes_whatsapp})
            
        if control_mails == None:
            control_mails = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'control_mails')]).valor.strip()
        else:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'control_mails')]).write({'valor': control_mails})

        if month == None:
            month = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).valor.upper()
        else:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).write({'valor': month})
        month = month.upper()

        if year == None:
            year = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).valor
        else:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).write({'valor': year})

        if hojas == None:
            hojas = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).valor
        else:
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).write({'valor': hojas})

        status = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).valor.lower()

        # month = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).valor.upper()
        # year = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).valor
        # hojas = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).valor

        pathgdrive_mes = pathgdrive + year + '/' + month

        id_root=google_drive_config.obtener_id_carpeta_por_ruta(servicio_drive, pathgdrive_mes)
        lista_archivos = pd.DataFrame(google_drive_config.listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))

        _logger.info(f"Terminando Variables: status: {status} - month: {month} - year: {year} - hojas: {hojas} - mensajes_whatsapp: {mensajes_whatsapp} - control_mails: {control_mails} - id_mb: {id_mb} - google_drive_config: {google_drive_config} ************")

        return status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion

    def get_archivo(self, google_drive_config, servicio_drive, gc, df_sheets, sheet, poliza, mes, lista_archivos):
        # _logger.info(f"Dentro de get_archivo ************")
        # aCTUALIZAR gOOGLE CON EL NOMBRE DEL ARCHIVO Y LA url
        # Eliminar ceros a la izquierda de la poliza para la búsqueda
        poliza_trm = str(poliza).lstrip('0')
        resultados = lista_archivos[lista_archivos['nombrearchivo'].str.contains(poliza_trm, na=False)]
        if len(resultados) > 0:
            nombrearchivo = resultados['nombrearchivo'].values[0]
            idarchivo = resultados['idarchivo'].values[0]
            
            url = google_drive_config.crear_url_de_acceso(servicio_drive, idarchivo)

            column_url = google_drive_config.buscando_columna('URL', df_sheets)
            column_nombrearchivo = google_drive_config.buscando_columna('NOMBREARCHIVO', df_sheets)
            row = google_drive_config.buscar_fila(mes, poliza_trm, df_sheets)
            _logger.info(f"get_archivo: poliza: {poliza_trm} - column_url: {column_url} - column_nombrearchivo {column_nombrearchivo} - row {row} ************")

            # result = google_drive_config.update_sheet_cell(sheet, row, column_url, url)
            # filename = 'VENCIMIENTOS 2024'
            # sheet = gc.open(filename).worksheet('PRUEBA')
            _logger.info(f"Antes de actualizr sheet {sheet} - servicio_drive {servicio_drive} - gc {gc} ************")
            # result = sheet.update_cell(268, 29, url)
            try:
                result = sheet.update_cell(sheet, 267, 28, 'url')
            except Exception as e:
                print(f"Error al actualizar la celda: {e}")
            _logger.info(f"get_archivo: result url: {result} ************")

        return True
    
    def validar_correos(self, correo):
        correos = correo.replace(' y ', ';').replace(' Y ', ';').replace(',', ';').split(';')

        # Validar correos váilidos de la lista
        correos_validos = []
        for correo in correos:
            if correo.find('@') > 0:
                correos_validos.append(correo)
        correos_validos = ';'.join(correos_validos)
        return correos_validos
    
    def validar_moviles(self, movil):
        # Validar teléfono válido. Debe tener 10 dígitos, pueden ser varios separados por , o ;
        moviles = str(movil).replace(',', ';').split(';')
        whatsapp_status = 'número no disponible'
        moviles_validos = []
        for movil in moviles:
            # Validar que el número de celular tenga 10 dígitos, sean solo nùmeros
            movil = re.sub(r'\D', '', movil)
            if len(movil) == 10:
                moviles_validos.append(movil)
                whatsapp_status = 'pendiente'
        return moviles_validos, whatsapp_status
    
    def ajustar_mensaje(self, mensaje_whatsapp):
        # Crear saludo como buenos días, buenas tardes o buenas noches según la hora de proceso. En hora local de Colombia (-5)
        hora = datetime.datetime.now().hour - 5 # Hora local de Colombia
        if hora >= 0 and hora < 12:
            saludo = 'Buenos días'
        elif hora >= 12 and hora < 18:
            saludo = 'Buenas tardes'
        else:
            saludo = 'Buenas noches'

        # _logger.info(f"Saludo ----> {saludo}")

        patron = r'Buenos\s+(días|tardes)'

        # Reemplazando con "Saludo"
        mensaje_whatsapp = re.sub(patron, saludo, mensaje_whatsapp)
        return saludo + mensaje_whatsapp

    @api.model
    def actualizar_modelo_vencimientos(self, df_sheets, year, mes_FILTRO, ramo, hoja_gc):
        _logger.info(f"Dentro de Actualizando modelo vencimientos mes_FILTRO {mes_FILTRO} - {ramo} ************")
        df_filtrado = df_sheets[df_sheets['MES'].str.upper() == mes_FILTRO]
        # _logger.info(f"L417 - df_filtrado: {df_filtrado.count()}")
        for index, row in df_filtrado.iterrows():
            # Buscar que el id_poliza este en el modelo vencimientos
            # Estandarizar a una longitud de 12 caracteres el id_poliza
            # _logger.info(f"POLIZA: {row['POLIZA']} ************")
            poliza = str(row['POLIZA']).zfill(12)
            # _logger.info(f"POLIZA: {poliza} ************")
            # record_id = self.search([('id_poliza', '=', poliza)])
            # _logger.info(f"Registro: {record_id} ************")

            correos_validos = self.validar_correos(row['CORREO'])
            # _logger.info(f"L428 - correos_validos {correos_validos}************")

            # _logger.info(f"CELULAR {row['CELULAR']}************")
            moviles_validos = ''
            whatsapp_status = ''
            if 'CELULAR' in row:
                moviles_validos, whatsapp_status  = self.validar_moviles(row['CELULAR'])

            forma_pago = ''
            if 'FORMA DE PAGO' in row:
                forma_pago = row['FORMA DE PAGO']

            if 'TIPO DE PLAN' in row:
                tipo_plan = row['TIPO DE PLAN'].upper().strip()
            # elif ramo == 'PROVISION':
            #     _logger.info(f"TIPO DE PLAN ramo {ramo} ************")
            #     tipo_plan = row['PRODUCTO'].upper().strip()
            else:
                tipo_plan = 'GENERAL'

            placa = ''
            if 'PLACA' in row:
                placa = row['PLACA']

            compania = ''
            if 'COMPANIA' in row:
                compania = row['COMPANIA']
            # _logger.info(f"compania {compania}************")

            # _logger.info(f"Antes del if ************")
            record = self.search([('id_poliza', '=', poliza)], limit=1)
            if record:
                result = record.write({
                                'ramo': ramo, 
                                'id_poliza': poliza,
                                'dni_tomador': row['ID'],
                                'tomador': row['TOMADOR'],
                                'formadepago': forma_pago,
                                # 'finvigencia': row['FIN DE VIGENCIA'],
                                'mes': mes_FILTRO,
                                'year': year,
                                'email_to': correos_validos,
                                # 'email_to': "danielpatinofernandez@gmail.com",
                                'mensaje': row['MENSAJE'],
                                'archivo': row['NOMBREARCHIVO'],
                                'url': row['URL'],
                                'movil': moviles_validos,
                                'aviso': 'ok',
                                'mail_status': row['ESTADO CORREO'],
                                'whatsapp_status': row['ESTADO WHATSAPP'],
                                'correo_temporal': correos_validos,
                                'tipo_plan': tipo_plan,
                                'mensaje_whatsapp':row['MENSAJE'],
                                'placa':placa,
                                'compania': compania
                            })
                # _logger.info(f"Registro actualizado: {record['id_poliza']}")
            else:
                # Crear un nuevo registro
                # _logger.info(f"Registro NO encontrado: {row['POLIZA']} ************")
                result = self.create({
                                'ramo': ramo, 
                                'id_poliza': poliza,
                                'dni_tomador': row['ID'],
                                'tomador': row['TOMADOR'],
                                'formadepago': forma_pago,
                                # 'finvigencia': row['FIN DE VIGENCIA'],
                                'mes': mes_FILTRO,
                                'year': year,
                                'email_to': correos_validos,
                                # 'email_to': "danielpatinofernandez@gmail.com",
                                'mensaje': row['MENSAJE'],
                                'archivo': row['NOMBREARCHIVO'],
                                'url': row['URL'],
                                'movil': moviles_validos,
                                'aviso': 'ok',
                                'mail_status': row['ESTADO CORREO'],
                                'whatsapp_status': row['ESTADO WHATSAPP'],
                                # 'correo_temporal': correos_validos,
                                'tipo_plan': tipo_plan,
                                'mensaje_whatsapp':row['MENSAJE'],
                                'placa':placa,
                                'compania': compania
                            })
                # _logger.info(f"Registro creado: {row['POLIZA']}")

        return True

    @api.model
    def consola(self, month=None, year=None, hojas=None, control=None):
        _logger.info(f"Entrando en la función consola month {month} - year {year} - hojas {hojas} - control {control} ************")
        status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion = self.variables(month, year, hojas, control)
        
        # Dar commit a la base de datos
        self.env.cr.commit()

        ruta_script = "/mnt/extra-addons/mb-asesores/consola/notebook.py"
        resultado = subprocess.run(["python3", ruta_script], capture_output=True, text=True)
        salida = resultado.stdout
        error = resultado.stderr
        json = {
                'salida': salida,
                'error': error
            }
        _logger.info(f"Salida consola: {json} ********")
        return json

    @api.model
    def descarga_vencimientos(self, month=None, year=None, hojas=None, control=None):
        _logger.info(f"Entrando en la función descarga_vencimientos ************")
        # _logger.info("Ejecutar actualización desde consola")

        # self.consola()

        status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion = self.variables(month, year, hojas, control)
        duracion = 0
        _logger.info(f"Consulta variables: status: {status} - month: {month} - year: {year} - hojas: {hojas} - mensajes_whatsapp: {mensajes_whatsapp} - control_mails: {control_mails} - id_mb: {id_mb} - google_drive_config: {google_drive_config} ************")
        # Si esta vació o idle se ejecuta la función, sino return status
        if (status == 'idle' or status == 'inactivo') or status == '' or status == None:
            # google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'ejecutando'})  # Actualizar el estado a idle
            _logger.info(f"Entrando al IF idle ************")
            # try:
            mes_recibido = month.upper()           
            mes_FILTRO = month
            year_recibido = year
            hojas_recibido = hojas                
            hojas_gc = hojas.split(",")
            hojas = [a.strip().replace(" ", "_").upper() for a in hojas_gc]

            # Actualizar registro en el modelo google.drive.config con la clave descarga_vencimientos
            # Crear variable En ejecución: hora de inicio
            inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            valor = "En ejecución: " + inicio
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})
            self.env.cr.commit()  # confirmar los cambios en la base de datos
                                                            
            # Enviar correo electrónico por cada registro donde el campo Aviso sea igual a ok
            _logger.info('Enviando correos electrónicos')

            contador = 0
            contador_enviados = 0
            contador_no_enviados = 0
            for hoja_gc in hojas_gc:
                # _logger.info(f"L593 - Entró en hoja: {hoja_gc}")
                hoja = hoja_gc.upper()
                df_sheets, sheet, sheet_df_dict, lista_archivos = google_drive_config.cargar_hoja(hoja, hoja_gc, servicio_drive, gc, pathgdrive, mes_FILTRO, year)
                result = self.actualizar_modelo_vencimientos(df_sheets, year, mes_FILTRO, hoja, hoja_gc)
                # _logger.info(f"L597 - Actualizado modelo vencimientos {hoja}: {type(result)} ************")

                df_filtrado = df_sheets[(df_sheets['MES'].str.upper() == mes_FILTRO) & (df_sheets['ESTADO CORREO'] == 'pendiente')]
                _logger.info(f"L600 - df_filtrado: {df_filtrado.count()} **********")
                for index, row in df_filtrado.iterrows():
                    # Ajustar poliza a 12 caracteres
                    poliza = str(row['POLIZA']).zfill(12)
                    _logger.info(f"L684 - Entró a: {row['POLIZA']} - {poliza} ramo {hoja} mes: {row['MES']} ************")

                    if row['URL'] and row['ESTADO CORREO'] == 'pendiente':
                        # Enviar correo electrónico
                        _logger.info(f"L608 - Entró a el envío del correo: {poliza} - control_mails {control_mails} - Correo: {row['CORREO']}**********")
                        asunto = 'Vencimiento de póliza' + ' ' + poliza + ' ' + row['TOMADOR']
                        mensaje = row['MENSAJE']
                        # Adicionar la UR al mensaje
                        mensaje = mensaje + '\n' + "URL archivo renovación: " + row['URL']
                        # _logger.info(f"L590 - Mensaje: {mensaje} ************")

                        # Buscar por poliza y por mes en mb_asesores.correo_enviado
                        mail_enviado = self.env['mb_asesores.correo_enviado'].search([('id_poliza', '=', poliza),
                                                                                    ('mes', '=', row['MES']),
                                                                                    ('year', '=', year_recibido),
                                                                                    ('tipo_mensaje', '=', 'Mail')
                                                                                    ])
                        _logger.info(f"L621 - mail_enviado: {mail_enviado} ************")
                        if mail_enviado or control_mails == 'marcar':
                            _logger.info(f"L623 - Correo electrónico ya enviado: row['POLIZA']: {poliza} control_mails: {control_mails} {type(control_mails)}")
                            # if control_mails == 'marcar':
                            #     record.write({'mail_status': 'enviado cliente'})
                            #     contador_enviados += 1
                            # else:
                            #     _logger.info(f"Correo electrónico ya enviado: {record.id_poliza} - {record.tomador}")
                        else:
                            _logger.info(f"L630 - Correo electrónico no enviado: {poliza} - {row['TOMADOR']} - {row['CORREO']} - hoja: {hoja} - template_dic {template_dic} ************")
                        
                            # Selecccionar el template de acuerdo al ramo
                            if hoja in template_dic:
                                _logger.info(f"L634 - Buscando el tamplate hoja: {hoja} ************")
                                if hoja == '040-AUTOMOVILES':
                                    _logger.info(f"Buscando el tamplate en  040-AUTOMOVILES ************")
                                    try:
                                        template = template_autos[row['TIPO DE PLAN'].upper().strip()] or 'mb-asesores.autosglobal'
                                    except KeyError:
                                        _logger.info(f"KeyError: {KeyError} ************")
                                        template = 'mb-asesores.autosglobal'
                                else:
                                    template = template_dic[hoja] or 'mb-asesores.generico'
                            _logger.info(f"template a enviar: {template}")
                            # Buscar registro en vencimientos
                            record = self.search([('id_poliza', '=', poliza), ('mes', '=', row['MES']), ('year', "=", year_recibido)], limit=1)
                            result, status_mail = record.enviar_correo(asunto, mensaje, template, hoja, row['MES'], year_recibido, row['POLIZA'], control_mails)
                            _logger.info(f"L646 - Resultado del envío de correo: {result} - {status_mail} ************")

                            if status_mail in ('enviado', 'sent'):
                                # Actualizar Sheet con estado de correo enviado
                                ################ Falta código para actualizar la celda en la hoja de Google Drive
                                # column_url = google_drive_config.buscando_columna('URL', df_sheets)
                                # column_nombrearchivo = google_drive_config.buscando_columna('NOMBREARCHIVO', df_sheets)
                                # column_mail_status = google_drive_config.buscando_columna('ESTADO CORREO', df_sheets)
                                # poliza_trm = str(row['POLIZA']).lstrip('0')
                                # row = google_drive_config.buscar_fila(row['MES'], poliza_trm, df_sheets)
                                # _logger.info(f"L655 - row: {row} - column_url: {column_url} - column_nombrearchivo {column_nombrearchivo} - column_mail_status {column_mail_status} ************")
                                # _logger.info(f"L656 - type(sheet): {type(sheet)} ************")


                                # result = sheet.update_cell(row, column_mail_status, status_mail)
                                # result = self.update_cell(row, column_mail_status, status_mail)
                                
                                # result = google_drive_config.update_sheet_cell(sheet, row, column_mail_status, status)
                                contador_enviados += 1
                            else:
                                _logger.info(f"No se encontró el ramo: {hoja}")
                                contador_no_enviados += 1

                        contador += 1
        #             # Si no existe id_archivo_adjunto, actualizar el estado del correo a no disponible
                    elif not row.url and row.mail_status == 'pendiente':
                        _logger.info(f"No se puedo procesar el correo: {row['POLIZA']}")
                        url = ''
                        # if record.mail_status != 'enviado':
                        #     record.write({'mail_status': 'pendiente por adjunto'})
                        # if record.whatsapp_status != 'enviado':
                        #     record.write({'whatsapp_status': 'pendiente por adjunto'})
                        contador_no_enviados += 1
                
            # Actualizar registro de control en el modelo google.drive.config con la clave descarga_vencimientos
            fin = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duracion = datetime.datetime.strptime(fin, "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
            valor = "Terminado: " + fin + " - Duración: " + str(duracion)
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'enviando whatsapp'})

            # Crear JSON que reporte la cantidad de registros actualizados y la duración de la ejecución
            Tipo_year_recibido=type(year_recibido)
            Tipo_mes_recibido=type(mes_recibido)
            json = {
                'registros_actualizados': contador,
                'registros_enviados': contador_enviados  or '0',
                'registros_no_enviados': contador_no_enviados or '0',
                'duracion': str(duracion),
                'mes recibido': mes_recibido,
                'year_recibido': year_recibido,
                'hojas_recibido': hojas_recibido,
                'status': 'enviando whatsapp'
            }

        #     _logger.info(f"json: {json}")
            self.send_mail_report(mes_FILTRO.upper())
            
            self.env.cr.commit()
            self.consola()
            # json_resultado = self.generar_json_registros_mes(mes_FILTRO)
            return json
        else:
            json = {
                        'registros_actualizados': -99,
                        'registros_enviados': -99,
                        'registros_no_enviados': -99,
                        'duracion': -99,
                        'mes recibido': month,
                        'year_recibido': year,
                        'hojas_recibido': hojas,
                        'status': status
                    }
            _logger.info(f"L725 - status: {status} json: {json} ************")
            return json

    # Función para enviar correo electrónico
    # Función para actualizar la hoja de gdrive con el estado del correo
    def update_cell(self, row, column, value):
        # Autenticarse a Google Drive
        google_drive_config = self.env['google.drive.config']
        creds, gc, servicio_drive = google_drive_config.autenticar_google_drive()
        gc = gspread.authorize(creds)
        # Cargar hoja de Google Drive
        sheet = gc.open("VENCIMIENTOS 2025").worksheet('040-AUTOMOVILES')
        result = sheet.update_cell(row, column, value)
        return result
        

    def enviar_correo(self, asunto, mensaje, template, ramo, mes, year, poliza, control_mails='si'):
        _logger.info(f"L736 - Antes de buscar el template: {template} - self.id_poliza: {self.id_poliza} - email_to: {self.email_to} - control_mails: {control_mails} ************")
        self.ensure_one()
        template_id = self.env.ref(template)

        _logger.info(f"template_id: {template_id}")

        if template_id:
            _logger.info(f"Entró a template_id: {template_id} control_mails: {control_mails}")
            if control_mails == 'si':
                mail_id = template_id.send_mail(self.id, force_send=True)
                mail = self.env['mail.mail'].browse(mail_id)
            elif control_mails == 'marcar':
                mail_id = None

            # Revisar si la poliza existe para el mes y año en el modelo correo_enviado
            correo_enviado = self.env['mb_asesores.correo_enviado'].search([('id_poliza', '=', poliza),
                                                                            ('mes', '=', mes),  
                                                                            ('year', '=', year),
                                                                            ('tipo_mensaje', '=', 'Mail')
                                                                            ])
            if not correo_enviado:
                self.env['mb_asesores.correo_enviado'].create({
                    'id_poliza': poliza,
                    'mail_id': mail_id,
                    'mes': mes,
                    'year': year,
                    'tipo_mensaje': 'Mail',
                    'ramo': ramo
                })
            else:
                # Actualizar mail_id en el registro de correo_enviado
                correo_enviado.write({'mail_id': mail_id})
            if mail.state == 'sent':
                _logger.info(f"Correo electrónico enviado a {self.email_to}")
                self.write({'mail_status': 'enviado'})
                return True, mail.state
            else:
                _logger.info(f'Problemas al enviar el correo electrónico a {self.email_to}')
                return False, mail.state

        else:
            _logger.info(f'No se encontró la plantilla de correo electrónico {template}')
            return False, 'Problemas con la plantilla de correo electrónico'

    
    def consultar_vencimientos(self, mes):
        # Consultar registros del modelo 'vencimientos' filtrados por el campo 'mes'
        vencimientos_data = self.env['mb_asesores.vencimientos'].search([('mes', '=', mes)])
        _logger.info(f'vencimientos_data {len(vencimientos_data)}')
        _logger.info(f'type vencimientos_data {type(vencimientos_data)}')

        data = []
        for order in vencimientos_data:
            # Obtener el diccionario de los campos y valores del registro
            record_data = order.read()[0]
            data.append(record_data)

        df = pd.DataFrame(data)
        return df

    # def actualizar_sheet_vencimientos(self, google_drive_config, sheet_df, month=None, year=None, hojas=None):
    #     # Conectandose a Gdrive
    #     hojas_g, meses_g, status_g, control_whatsapp_g = consultar_configuracion(self)
    #     _logger.info(f"hojas_g: {hojas_g} - meses_g: {meses_g} - status_g: {status_g} - control_whatsapp_g: {control_whatsapp_g} *************")

    #     if month == None:
    #         month = meses_g[0]
    #     if hojas == None:
    #         hojas = hojas_g
    #     if year == None:
    #         year = datetime.datetime.now().year

    #     # google_drive_config = self.env['google.drive.config']
    #     # servicio_drive = build('drive', 'v3', credentials=google_drive_config.autenticar_google_drive())
    #     # gc = gspread.authorize(google_drive_config.autenticar_google_drive())

    #     df_vencimientos = self.consultar_vencimientos(month)
    #     for hoja_gc in hojas:
    #         hoja = hoja_gc.upper().replace(" ", "_")
    #         _logger.info(f"nombre_hoja: {hoja_gc} **********")
    #         # sheet_df, sheet = google_drive_config.cargar_hoja(nombre_hoja, gc)
    #         df_sheets, sheet, sheet_df_dict, lista_archivos = google_drive_config.cargar_hoja(hoja, hoja_gc, servicio_drive, gc, pathgdrive, mes_FILTRO)
    #         _logger.info(f"Cargar hoja {hoja_gc} sheet_df.count(): {sheet_df.count()} **********")

    #         ## Filtrando df para mensajes de correo enviado
    #         nombre_ramo = hoja
    #         df_filtered = df_vencimientos[(df_vencimientos['ramo'] == nombre_ramo)
    #         #                 & (df_vencimientos['mail_status'] == 'enviado')
    #                                     ]

    #         contador = 0
    #         contador2 = 1
    #         cantidad_registros = df_filtered.shape[0]

    #         for index, row in df_filtered.iterrows():
    #             # Mostrar el valor del campo 'id_poliza' para cada fila
    #             _logger.info(f"row['id_poliza'] {row['id_poliza']}, row['ramo'] {row['ramo']}, row['mail_status'] {row['mail_status']} mes {month} **********")

    #             # Buscando la posición de las columnas de control
    #             poliza = row['id_poliza'].lstrip('0')
    #             status_mail = row['mail_status']
    #             status_whatsapp = row['whatsapp_status']
    #             hora_whatsapp = row['hora_ws']
    #             columna_estado_correo = sheet_df.columns.to_list().index('ESTADO CORREO')+1
    #             columna_estado_whatsapp = sheet_df.columns.to_list().index('ESTADO WHATSAPP')+1
    #             columna_hora_whatsapp = sheet_df.columns.to_list().index('HORA WHATSAPP')+1
    #             columna_mes = sheet_df.columns.to_list().index('MES')+1
    #             columna_poliza = sheet_df.columns.to_list().index('POLIZA')+1

    #             _logger.info(f"columna_estado_correo: {columna_estado_correo} - columna_estado_whatsapp: {columna_estado_whatsapp} - columna_hora_whatsapp: {columna_hora_whatsapp} - columna_mes: {columna_mes} - columna_poliza: {columna_poliza} **********")

    #             google_drive_config.actualizar_registro(
    #                         hoja_gc,
    #                         poliza,
    #                         status_mail,
    #                         status_whatsapp,
    #                         hora_whatsapp,
    #                         sheet,
    #                         columna_estado_correo,
    #                         columna_estado_whatsapp,
    #                         columna_hora_whatsapp,
    #                         columna_mes,
    #                         columna_poliza,
    #                         month,
    #                         sheet_df)
                
    #             time.sleep(3)
    #             contador += 1
    #             contador2 += 1 
    #             if contador == 10:
    #                 contador = 0
    #                 time.sleep(5)
    #             _logger.info(f"Actualizando {contador2}/{cantidad_registros}")
    #         time.sleep(5)
    #     _logger.info("Terminó la actualización de los registros en las hojas de Google Drive")
    #     return True

def consultar_configuracion(self):
    id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id

    configuracion = self.env['google.drive.config'].search([('cliente_id', '=', id_mb)])
    # mensajes_whatsapp = configuracion.filtered(lambda x: x.clave == 'mensajes_whatsapp').valor
    hojas = configuracion.filtered(lambda x: x.clave == 'hojas').valor.split(",")
    hojas = [elemento.strip() for elemento in hojas]

    mes = configuracion.filtered(lambda x: x.clave == 'mes_FILTRO').valor.split(",")
    mes = [elemento.strip() for elemento in mes]

    status = configuracion.filtered(lambda x: x.clave == 'status').valor.strip()
    control_whatsapp = configuracion.filtered(lambda x: x.clave == 'mensajes_whatsapp').valor.strip()
    
    return hojas, mes, status, control_whatsapp

# Modelo que registra el correo electrónico enviado a cada cliente.
# El modelo hereda el ID del mail.mail.
            
class CorreoEnviado(models.Model):
    _name = 'mb_asesores.correo_enviado'
    _description = 'Log de correos enviados'

    id_poliza = fields.Char(string='ID Poliza')
    mail_id = fields.Many2one('mail.mail', string='Correo electrónico', ondelete='set null')
    state = fields.Selection(related='mail_id.state', string='Estado', store=True, readonly=True)
    create_date = fields.Datetime(related='mail_id.create_date', string='Fecha de creación', store=True, readonly=True)
    tipo = fields.Selection([('vencimiento', 'Vencimiento'), ('renovacion', 'Renovación')], string='Tipo', default='renovacion')
    mes = fields.Char(string='Mes')
    year = fields.Integer(string='Año')
    subjet = fields.Char(string='Asunto')
    email_to = fields.Char(string='Destinatario')
    tipo_mensaje = fields.Selection([('Mail', 'Mail'), ('Whatsapp', 'Whatsapp')], string='Tipo de mensaje')
    ramo = fields.Char(string='Ramo')


