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

from xlsxwriter.workbook import Workbook
import base64

import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import gspread


_logger = logging.getLogger(__name__)

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
        # self.with_delay().descarga_vencimientos()
        self.env['mb_asesores.vencimientos'].with_delay().descarga_vencimientos('a', k=2)


    # Función para actualizar el estado general en Google config
    @api.model
    def actualizar_estado_general(self, estado=None):
        _logger.info(f'Entrando en la función actualizar_estado_general con estado: {estado}***************')
        if estado:
            id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': estado})
            _logger.info(f'Estado actualizado a: {estado}')
            json = {
                    'status': estado,
                    'observaciones': 'Actualizado'
                }
            return json
        else:
            _logger.warning("No se ha recibido el estado")
            json = {
                    'status': None,
                    'observaciones': 'No se ha recibido el estado'
                }
            return json

    @api.model
    def get_status(self):
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
        status = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).valor
        json = {
                    'status': status
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
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id

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

        status = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).valor.lower()

        month = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).valor.upper()
        year = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).valor
        hojas = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).valor

        return status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config

    
    @api.model
    # @job
    # def descarga_vencimientos(self, mes=None, year=None):
    def descarga_vencimientos(self, month=None, year=None, hojas=None, control=None):
         # Buscar ID odoo del usuario MB-Asesores
        # _logger.info(f"Iniciando envío ***********************")
        # id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
        # _logger.info(f"ID del administrador: {id_mb}")

        # # separar por comas la cadena contol y colocarla en las variables mensajes_whatsapp y control_mails
        # if control:
        #     control = control.split(",")
        #     mensajes_whatsapp = control[0].strip()
        #     control_mails = control[1].strip()
        #     estado_provision = control[2].strip().lower()
        # else:
        #     mensajes_whatsapp = None
        #     control_mails = None
        #     estado_provision = None
        
        # if mensajes_whatsapp == None:
        #     mensajes_whatsapp = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')]).valor.strip()
        # else:
        #     self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')]).write({'valor': mensajes_whatsapp})
            
        # if control_mails == None:
        #     control_mails = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'control_mails')]).valor.strip()
        # else:
        #     self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'control_mails')]).write({'valor': control_mails})

        # Instanciar el modelo google.drive.config
        # google_drive_config = self.env['google.drive.config']
        # status = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).valor.lower()
        status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config = self.variables(month, year, hojas, control)
        duracion = 0
        # Si esta vació o idle se ejecuta la función, sino return status
        if status == 'idle' or status == '' or status == None:
            google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'running'})  # Actualizar el estado a running        
            try:
                _logger.info('Entrando en la función descarga_vencimientos')

                # # Convertir month a mayúsculas
                # if month:
                #     month = month.upper()

                mes_recibido = month
                # if month == None:
                #     month = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).valor.upper()
                # else:
                #     self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).write({'valor': month.upper()})
            
                mes_FILTRO = month
                # mes_FILTRO = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')]).valor.upper()
                year_recibido = year
                # if year == None:
                #     year = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).valor
                # year = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'year')]).valor
                hojas_recibido = hojas
                # if hojas == None:
                #     hojas = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).valor
                # else:
                #     self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).write({'valor': hojas})
                
                hojas = hojas.split(",")
                hojas = [a.strip().replace(" ", "_").upper() for a in hojas]

                # Actualizar registro en el modelo google.drive.config con la clave descarga_vencimientos
                # Crear variable En ejecución: hora de inicio
                inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                valor = "En ejecución: " + inicio
                self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})
                self.env.cr.commit()  # confirmar los cambios en la base de datos

                # servicio_drive = google_drive_config.autenticar_google_drive()
                servicio_drive = build('drive', 'v3', credentials=google_drive_config.autenticar_google_drive())
                gc = gspread.authorize(google_drive_config.autenticar_google_drive())

                # Buscar proyecto mb-asesores en modulo google.drive.config para el cliente_id = id_admin
                pathgdrive = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-gdrive')]).valor    
                pathglocal = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-local')]).valor
                nombrearchivovencimientos = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'vencimientos')]).valor
                ejecucion = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'ejecucion')]).valor

                pathgdrive_mes = pathgdrive + '/' + mes_FILTRO

                # id_root=google_drive_config.obtener_id_carpeta_por_nombre(servicio_drive, pathgdrive)
                id_root=google_drive_config.obtener_id_carpeta_por_ruta(servicio_drive, pathgdrive_mes)
                # _logger.info(f"id_root ruta completa: {pathgdrive_mes}: id_root: {id_root}")
                lista_archivos = pd.DataFrame(google_drive_config.listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))

                # nombre_archivo = pathgdrive + '/renovaciones/' + nombrearchivovencimientos
                nombre_archivo_sheet = 'VENCIMIENTOS 2024'
                nombre_archivo = pathgdrive + '/' + nombrearchivovencimientos
                nombre_archivo_destino = pathglocal + nombrearchivovencimientos

                nombre_archivo_destino = re.sub(r'\s', '_', nombre_archivo_destino)

                # Descargar y cargar el archivo con pandas
                id_archivo = google_drive_config.obtener_id_archivo_por_nombre(servicio_drive, nombre_archivo)
                id_archivo_sheet = google_drive_config.obtener_id_archivo_sheet(servicio_drive, nombre_archivo_sheet)
                # df_vencimientos = google_drive_config.descargar_archivo(servicio_drive, id_archivo, nombre_archivo_destino)

                # Crrear dataframes
                _logger.info(f"id_archivo_sheet {id_archivo_sheet}")
                df_sheets, no_creados, hojas_corregido = google_drive_config.crear_df_desde_archivo_sheet(gc, id_archivo_sheet)

                # Hojas a examinar
                # _logger.info(f"hojas----> {hojas}")
                _logger.info(f"hojas_corregido------> {hojas_corregido}") 
                for hoja in hojas_corregido:
                    # Validando si la hoja se encuentra en el listado de hojas
                    if hoja in hojas:
                        _logger.info(f"--- Entró en hoja: {hoja}")
                        df_filtrado = df_sheets[hoja][df_sheets[hoja]['MES'].str.upper() == mes_FILTRO]
                        _logger.info(f"df_filtrado {hoja}: {df_filtrado.count()}")

                        # Revisar cada registro del df
                        _logger.info(f"Antes de entrar al for **************")
                        for index, row in df_filtrado.iterrows():
                            # Buscar que el id_poliza este en el modelo vencimientos
                            # Estandarizar a una longitud de 12 caracteres el id_poliza
                            row['POLIZA'] = str(row['POLIZA']).zfill(12)
                            record = self.search([('id_poliza', '=', row['POLIZA'])], limit=1)
                            
                            if hoja == 'BOLIVAR':
                                nombre_archivo = f"BOLIVAR_{row['POLIZA']}.pdf"
                            elif hoja == 'PROVISION':
                                nombre_archivo = f"{row['POLIZA']}.pdf"
                            elif hoja == 'GENERALES':
                                nombre_archivo = f"RENOVACION_{row['POLIZA']}.pdf"
                            else:
                                nombre_archivo = f"CARATULA_{row['POLIZA']}.pdf"
                            url = ''
                            
                            correos = 'NO DISPONIBLE'
                            if 'CORREO' in row:
                                if row['CORREO']:
                                    # _logger.info(f"Revisando row['CORREO']: {row['CORREO']}")
                                    correos = row['CORREO'].replace(',', ';').split(';')

                            # Validar correos váilidos de la lista
                            correos_validos = []
                            for correo in correos:
                                if correo.find('@') > 0:
                                    correos_validos.append(correo)
                                    mail_status = 'pendiente'
                                else:
                                    mail_status = 'no disponible'
                            # Convertir lista de correos válidos en string
                            correos_validos = ';'.join(correos_validos)

                            # Validar teléfono válido. Debe tener 10 dígitos, pueden ser varios separados por , o ;
                            moviles = row['CELULAR'].replace(',', ';').split(';')
                            moviles_validos = []
                            for movil in moviles:
                                # Validar que el número de celular tenga 10 dígitos, sean solo nùmeros
                                movil = re.sub(r'\D', '', movil)
                                if len(movil) == 10:
                                    moviles_validos.append(movil)
                                    whatsapp_status = 'pendiente'
                                else:
                                    whatsapp_status = 'no disponible'
                            # Convertir lista de móviles válidos en string
                            moviles_validos = ';'.join(moviles_validos)
                            mensaje_whatsapp = row["MENSAJE"]

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
                            mensaje_whatsapp = saludo + mensaje_whatsapp

                            if hoja == '081-VIDA':
                                mensaje_especifico = f'enviamos la renovación de su póliza de vida {row["PRODUCTO"]}'
                            elif hoja == '181-MAS_VIDA':
                                mensaje_especifico = f'enviamos la renovación de su póliza de su enfermedades graves'
                            elif hoja == '090-SALUD':
                                mensaje_especifico = f'enviamos la renovación de su póliza de salud {row["TIPO DE PLAN"]}'
                            else:
                                mensaje_especifico = 'enviamos la renovación de su póliza'
                            # Determinar si existe la columna Tipo de plan en el df
                            if 'TIPO DE PLAN' in df_filtrado.columns:
                                tipo_plan = row['TIPO DE PLAN'].upper().strip()
                            elif hoja == 'PROVISION':
                                tipo_plan = row['PRODUCTO'].upper().strip()
                            else:
                                tipo_plan = 'GENERAL'

                            if 'FORMA DE PAGO' in row:
                                forma_pago = row['FORMA DE PAGO']
                            else:
                                forma_pago = ''

                            if 'PRIMA' in row:
                                prima = row['PRIMA']
                            else:
                                prima = ''
                            
                            mensaje = f"""{saludo} Sr(a). {row['TOMADOR']} \n
        Para Mesa Barreneche usted es muy importante, por este medio y al correo {correos_validos},  {mensaje_especifico}, con inicio de vigencia {row['FIN DE VIGENCIA']}.\n
        Nosotros nos estaremos contactando con usted, claro está, que si requiere alguna información con mayor prontitud, puede usted comunicarse con nuestra Asesora Comercial, Angelica Fernandez,  Celular 3127192560, correo electrónico comercial2@mbasesoresenseguros.com \n
        Forma de pago: {forma_pago} \n
        Valor a pagar {prima} \n
        MEDIOS DE PAGO: \n
        https://www.segurossura.com.co/paginas/pago-express.aspx#/Pagos \n
        PSE- Tarjeta de Crédito o efectivo si lo prefiere.
                                    """
                            if hoja == 'PROVISION':
                                if row['ESTADO'].upper() == 'CONDICIONES':
                                    # mensaje2 = "las condiciones de renovación"
                                    mensaje2 = f"""
                                                {saludo} Sr(a). {row['TOMADOR']} \n
                                                Para Mesa Barreneche usted es muy importante, anexo enviamos las condiciones de renovación de la póliza que ampara su vehículo de placas {row['PLACA']}, con inicio de vigencia {row['FIN DE VIGENCIA']} con la compañía de seguros {row['COMPANIA'].upper()}. \n
                                                Nuestra Asesora Comercial, Isabel Cristina Obando Cuartas, estará en contacto con toda la información que usted requiera. Celular 3206128289, correo electrónico comercial1@mbasesoresenseguros.com
                                                Gracias por contar con nosotros. 
                                                ¡¡Feliz Día!!"
                                                """
                                else:
                                    # mensaje2 = "la renovación"
                                    mensaje2 = f"""
                                                {saludo} Sr(a). {row['TOMADOR']} \n
                                                Para Mesa Barreneche usted es muy importante, anexo enviamos la renovación de la póliza que ampara su vehículo de placas {row['PLACA']}, con inicio de vigencia {row['FIN DE VIGENCIA']} con la compañía de seguros {row['COMPANIA'].upper()}. \n
                                                Nuestra Asesora Comercial, Isabel Cristina Obando Cuartas, estará en contacto con toda la información que usted requiera. Celular 3206128289, correo electrónico comercial1@mbasesoresenseguros.com
                                                Gracias por contar con nosotros. 
                                                ¡¡Feliz Día!!"
                                                """
                                placa = row['PLACA']
                                compania = row['COMPANIA'].upper()
                            elif hoja == '040-AUTOMOVILES':
                                mensaje_whatsapp = f"""{saludo} Sr(a). {row['NOMBRE CORTO']} \n
        Para Mesa Barreneche usted es muy importante, por este medio y al correo {row['CORREO']}, enviamos la renovación de la póliza que ampara su vehículo de placa {row['PLACA']}, con inicio de vigencia{row['FIN DE VIGENCIA']}.\n
        Nuestra Asesora Comercial,  Isabel Cristina Obando Cuartas, estará en contacto con toda la información que usted requiera. Celular 3206128289, correo electrónico comercial1@mbasesoresenseguros.com
        Forma de pago: {forma_pago} \n
        Valor a pagar {prima} \n
        MEDIOS DE PAGO: \n
        https://www.segurossura.com.co/paginas/pago-express.aspx#/Pagos \n

        PSE- Tarjeta de Crédito o efectivo si lo prefiere.
        Gracias por contar con nosotros.   
        ¡¡Feliz Día!!

                                    """
                                placa = row['PLACA']
                                mensaje2 = None
                                compania = None
                            else:
                                mensaje2 = None
                                placa = None
                                compania = None

                            _logger.info(f"Evaluando control en provisiones ******************")
                            _logger.info(f"Registro actualizado: {row['POLIZA']} - Ramo {hoja.strip()}******************")
                            controlenviar = 0
                            if hoja.strip() == 'PROVISION':
                                _logger.info(f"Entró a revisar PROVISION ******************")
                                if row['CONTROL']:
                                    rowcontrol = row['CONTROL'].lower()
                                if estado_provision == 'enviar' and rowcontrol == 'enviar':
                                    _logger.info(f"Entró a enviar PROVISION 2 ******************")
                                    controlenviar = 1
                                else:
                                    controlenviar = 1
                            else:
                                _logger.info(f"Entró a revisar otros ramos ******************")
                                controlenviar = 1

                            
                            if controlenviar == 1:
                                if record:
                                    if record.mail_status == 'enviado':
                                        mail_status = 'enviado'
                                    if record.whatsapp_status == 'enviado':
                                            whatsapp_status = 'enviado'

                                    if 'FORMA DE PAGO' in row:
                                        forma_pago = row['FORMA DE PAGO']
                                    else:
                                        forma_pago = ''

                                    if record.url in row:
                                        url = record.url
                                    else:
                                        url = ''

                                    record.write({
                                        'ramo': hoja.strip(), 
                                        'id_poliza': row['POLIZA'],
                                        'dni_tomador': row['ID'],
                                        'tomador': row['TOMADOR'],
                                        'formadepago': forma_pago,
                                        # 'finvigencia': row['FIN DE VIGENCIA'],
                                        'mes': row['MES'].upper().strip(),
                                        'year': year,
                                        # 'email_to': correos_validos,
                                        'email_to': "danielpatinofernandez@gmail.com",
                                        'mensaje': mensaje_whatsapp,
                                        'archivo': nombre_archivo,
                                        'url': url,
                                        'movil': moviles_validos,
                                        'aviso': 'ok',
                                        'mail_status': mail_status,
                                        'whatsapp_status': whatsapp_status,
                                        'correo_temporal': correos_validos,
                                        'tipo_plan': tipo_plan,
                                        'mensaje_whatsapp':mensaje_whatsapp,
                                        'placa':placa,
                                        'mensaje2':mensaje2,
                                        'compania': compania
                                    })
                                    # _logger.info('Registro actualizado')
                                else:
                                    # Crear un nuevo registro
                                    self.create({
                                        'ramo': hoja.strip(), 
                                        'id_poliza': row['POLIZA'],
                                        'dni_tomador': row['ID'],
                                        'tomador': row['TOMADOR'],
                                        'formadepago': forma_pago,
                                        # 'finvigencia': row['FIN DE VIGENCIA'],
                                        'mes': row['MES'].upper().strip(),
                                        'year': year,
                                        # 'email_to': correos_validos,
                                        'email_to': "danielpatinofernandez@gmail.com",
                                        'mensaje': mensaje_whatsapp,
                                        'archivo': nombre_archivo,
                                        'url': url,
                                        'movil': moviles_validos,
                                        'aviso': 'ok',
                                        'mail_status': mail_status,
                                        'whatsapp_status': whatsapp_status,
                                        # 'correo_temporal': correos_validos,
                                        'tipo_plan': tipo_plan,
                                        'mensaje_whatsapp':mensaje_whatsapp,
                                        'placa':placa,
                                        'mensaje2':mensaje2,
                                        'compania': compania
                                    })
                            else:
                                _logger.info(f"Control no enviar: {record.id_poliza} - {record.ramo} - {record.mes} - {record.control.lower()}")
                
                # Enviar correo electrónico por cada registro donde el campo Aviso sea igual a ok
                _logger.info('Enviando correos electrónicos')

                mapeo_ramo = {
                    '040-AUTOMOVILES': 'AUTOS',
                    '041-AUTOS OBLIGATORIO': 'AUTOS',
                    'SALU': 'SALUD',
                    'MAS VIDA': 'MAS VIDA',
                    'HOGAR': 'HOGAR',
                    'PAG': 'ENFERMEDADES GRAVES',
                }
                contador = 0
                contador_enviados = 0
                contador_no_enviados = 0
                for hoja in hojas:
                    _logger.info(f"Revisando consulta **********")
                    for record in self.search([('ramo', '=', hoja), ('mes', '=', mes_FILTRO), ('mail_status', '=', 'pendiente')]):
                        _logger.info(f"Entró a: {record.id_poliza} ramo {record.ramo} mes {mes_FILTRO}:{record.mes} ************")


                    # for record in self.search([('ramo', '=', hoja), ('mes', '=', mes_FILTRO)]):
                    #     _logger.info(f"Entró a: {record.id_poliza} ************")

                        # Crear nombre de archivo alternativo de la forma RENOVACION VIDA SURA-{TOMADOR} 2024-2025
                        nombre_archivo_alternativo = f"RENOVACION {mapeo_ramo.get(record.ramo, 'AUTOS')} SURA-{record.tomador} 2024-2025.pdf"
                        nombre_archivo_alternativo_2 = f"RENOVACION {mapeo_ramo.get(record.ramo, 'AUTOS')} SURA-{record.tomador} 2024-2025.pdf"

                        if len(record.tomador.split()) > 3:
                            nombre_archivo_alternativo_3 = f"RENOVACION {mapeo_ramo.get(record.ramo, 'AUTOS')} SURA- {record.tomador.split()[2]} {record.tomador.split()[3]} {record.tomador.split()[0]} {record.tomador.split()[1]} 2024-2025.pdf"
                            nombre_archivo_alternativo_4 = f"RENOVACION {mapeo_ramo.get(record.ramo, 'AUTOS')} SURA-{record.tomador.split()[2]} {record.tomador.split()[3]} {record.tomador.split()[0]} {record.tomador.split()[1]} 2024-2025.pdf"

                        _logger.info(f"nombre_archivo_alternativo: {record.archivo} *****************")
                        try:
                            id_archivo_adjunto = lista_archivos[lista_archivos['nombrearchivo'] == record.archivo]['idarchivo'].values[0]
                        except:
                            try:
                                id_archivo_adjunto = lista_archivos[lista_archivos['nombrearchivo'] == nombre_archivo_alternativo]['idarchivo'].values[0]
                            except:
                                try:
                                    id_archivo_adjunto = lista_archivos[lista_archivos['nombrearchivo'] == nombre_archivo_alternativo_2]['idarchivo'].values[0]
                                except:
                                    try:
                                        id_archivo_adjunto = lista_archivos[lista_archivos['nombrearchivo'] == nombre_archivo_alternativo_3]['idarchivo'].values[0]
                                    except:
                                        try:
                                            id_archivo_adjunto = lista_archivos[lista_archivos['nombrearchivo'] == nombre_archivo_alternativo_4]['idarchivo'].values[0]
                                        except:
                                            try:
                                                id_archivo_adjunto = lista_archivos[lista_archivos['nombrearchivo'].str.contains(record.id_poliza.lstrip('0'))]['idarchivo'].values[0]
                                            except:
                                                id_archivo_adjunto = ''

                        if id_archivo_adjunto and not record.url:
                            # _logger.info(f"Actualizando URL: {record.id_poliza}")
                            url = google_drive_config.crear_url_de_acceso(servicio_drive, id_archivo_adjunto)
                            record.write({'url': url})

                        # _logger.info(f"Revisando: record.id_poliza: {record.id_poliza} id_archivo_adjunto: {id_archivo_adjunto} - record.mail_status: {record.mail_status} - record.ramo: {record.ramo} - hoja: {hoja}")
                        if id_archivo_adjunto and record.mail_status == 'pendiente' and record.ramo == hoja:
                            # Enviar correo electrónico
                            _logger.info(f"Entró a el envío del correo: {record.id_poliza} - control_mails {control_mails} **********")
                            asunto = 'Vencimiento de póliza' + ' ' + record.id_poliza + ' ' + record.tomador
                            if not ejecucion or ejecucion == 'produccion':
                                destinatario = record.email_to
                            else:
                                destinatario = 'danielpatinofernandez@gmail.com'
                            _logger.info(f"******destinatario: {destinatario} poliza {record.id_poliza} ejecucion {ejecucion}")
                            destinatario = record.email_to
                            mensaje = record.mensaje
                            # Adicionar la UR al mensaje
                            mensaje = mensaje + '\n' + "URL archivo renovación: " + url

                            # Buscar por poliza y por mes en mb_asesores.correo_enviado
                            mail_enviado = self.env['mb_asesores.correo_enviado'].search([('id_poliza', '=', record.id_poliza),
                                                                                        ('mes', '=', record.mes),
                                                                                        ('tipo_mensaje', '=', 'Mail')
                                                                                        ])

                            # if mail_enviado or control_mails == 'marcar':
                            #     _logger.info(f"Correo electrónico ya enviado: record.id_poliza: {record.id_poliza} control_mails: {control_mails} {type(control_mails)}")
                            #     if control_mails == 'marcar':
                            #         record.write({'mail_status': 'enviado cliente'})
                            #         contador_enviados += 1
                            #     else:
                            #         _logger.info(f"Correo electrónico ya enviado: {record.id_poliza} - {record.tomador}")
                            # else:
                            # Crear diccionario segùn el ramo
                            template_dic = {'040-AUTOMOVILES': 'mb-asesores.autosglobal',
                                            '181-MAS_VIDA': 'mb-asesores.masvida',
                                            '090-SALUD': 'mb-asesores.salud',
                                            '081-VIDA': 'mb-asesores.vida',
                                            'BOLIVAR': 'mb-asesores.generico',
                                            '113-PAC': 'mb-asesores.pac',
                                            'PROVISION': 'mb-asesores.provision',
                                            'GENERALES': 'mb-asesores.generico',
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
                            
                            # Selecccionar el template de acuerdo al ramo
                            if record.ramo in template_dic:
                                if record.ramo == '040-AUTOMOVILES':
                                    try:
                                        template = template_autos[record.tipo_plan.upper().strip()] or 'mb-asesores.autosglobal'
                                    except KeyError:
                                        template = 'mb-asesores.autosglobal'
                                else:
                                    template = template_dic[record.ramo] or 'mb-asesores.generico'
                                _logger.info(f"template a enviar: {template}")
                                record.enviar_correo(asunto, destinatario, mensaje, template, record.ramo, control_mails)
                                if control_mails == 'marcar':
                                    record.write({'mail_status': 'enviado cliente'})
                                else:
                                    record.write({'mail_status': 'enviado'})
                                contador_enviados += 1
                            else:
                                _logger.info(f"No se encontró el ramo: {record.ramo}")

                            contador += 1
                        # Si no existe id_archivo_adjunto, actualizar el estado del correo a no disponible
                        elif not id_archivo_adjunto and record.mail_status == 'pendiente':
                            _logger.info(f"No se puedo procesar el correo: {record.id_poliza}")
                            url = ''
                            if record.mail_status != 'enviado':
                                record.write({'mail_status': 'pendiente por adjunto'})
                            if record.whatsapp_status != 'enviado':
                                record.write({'whatsapp_status': 'pendiente por adjunto'})
                            contador_no_enviados += 1
                    
                # Actualizar registro de control en el modelo google.drive.config con la clave descarga_vencimientos
                fin = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                duracion = datetime.datetime.strptime(fin, "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
                valor = "Terminado: " + fin + " - Duración: " + str(duracion)
                self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})

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
                    'status': 'waiting'
                }

                google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'waiting'})  # Actualizar el estado a idle

                _logger.info(f"json: {json}")
                self.send_mail_report(mes_FILTRO)
                # json_resultado = self.generar_json_registros_mes(mes_FILTRO)
                return json
            except:
                # Manejo de la excepción ValueError (si el usuario no ingresa un número)
                #    _logger.info("Error desconocido:", e)
                json = {
                        'registros_actualizados': -99,
                        'registros_enviados': -99,
                        'registros_no_enviados': -99,
                        'duracion': str(duracion),
                        'mes recibido': mes_recibido,
                        'year_recibido': year_recibido,
                        'hojas_recibido': hojas_recibido,
                        'status': 'Error desconocido'
                    }
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
            _logger.info(f"json: {json}")
            return json

    # Función para enviar correo electrónico
    def enviar_correo(self, asunto, destinatario, mensaje, template, ramo, control_mails='si'):
        self.ensure_one()
        _logger.info(f"Antes de buscar el template: {template}")
        template_id = self.env.ref(template)

        _logger.info(f"template_id: {template_id}")

        if template_id:
            _logger.info(f"Entró a template_id: {template_id} control_mails: {control_mails}")
            if control_mails == 'si':
                # _logger.info(f"Entró a control_mails: {control_mails}")
                mail_id = template_id.send_mail(self.id, force_send=True)
                _logger.info(f"Salió de mail_id: {mail_id}")
                mail = self.env['mail.mail'].browse(mail_id)
                # _logger.info(f"mail_id: {mail_id}")
            elif control_mails == 'marcar':
                mail_id = None

            # Registrar envìo de correo electrónico en el modelo correo.enviado
            # Si control_mails es distinto de no se registra el envío del correo
            if control_mails != 'no':
                self.env['mb_asesores.correo_enviado'].create({
                    'id_poliza': self.id_poliza,
                    'mail_id': mail.id,
                    # 'state': mail.state,
                    # 'tipo': 'vencimiento',
                    'mes': self.mes,
                    'year': self.year,
                    'tipo_mensaje': 'Mail',
                    'ramo': ramo
                    # 'subjet': mail.subject,
                    # 'email_to': mail.email_to
                })
        else:
            _logger.info(f'No se encontró la plantilla de correo electrónico {template}')

        return True
    
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

    def actualizar_sheet_vencimientos(self, month=None, year=None, hojas=None):
        # Conectandose a Gdrive
        hojas_g, meses_g, status_g, control_whatsapp_g = consultar_configuracion(self)
        _logger.info(f"hojas_g: {hojas_g} - meses_g: {meses_g} - status_g: {status_g} - control_whatsapp_g: {control_whatsapp_g} *************")

        if month == None:
            month = meses_g[0]
        if hojas == None:
            hojas = hojas_g
        if year == None:
            year = datetime.datetime.now().year

        google_drive_config = self.env['google.drive.config']
        servicio_drive = build('drive', 'v3', credentials=google_drive_config.autenticar_google_drive())
        gc = gspread.authorize(google_drive_config.autenticar_google_drive())

        df_vencimientos = self.consultar_vencimientos(month)
        for nombre_hoja in hojas:
            _logger.info(f"nombre_hoja: {nombre_hoja} **********")
            sheet_df, sheet = google_drive_config.cargar_hoja(nombre_hoja, gc)
            _logger.info(f"Cargar hoja {nombre_hoja} sheet_df.count(): {sheet_df.count()} **********")

            ## Filtrando df para mensajes de correo enviado
            nombre_ramo = nombre_hoja.replace(' ', '_')
            df_filtered = df_vencimientos[(df_vencimientos['ramo'] == nombre_ramo)
            #                 & (df_vencimientos['mail_status'] == 'enviado')
                                        ]

            contador = 0
            contador2 = 1
            cantidad_registros = df_filtered.shape[0]

            for index, row in df_filtered.iterrows():
                # Mostrar el valor del campo 'id_poliza' para cada fila
                _logger.info(f"row['id_poliza'] {row['id_poliza']}, row['ramo'] {row['ramo']}, row['mail_status'] {row['mail_status']} mes {month} **********")

                # Buscando la posición de las columnas de control
                poliza = row['id_poliza'].lstrip('0')
                status_mail = row['mail_status']
                status_whatsapp = row['whatsapp_status']
                hora_whatsapp = row['hora_ws']
                columna_estado_correo = sheet_df.columns.to_list().index('ESTADO CORREO')+1
                columna_estado_whatsapp = sheet_df.columns.to_list().index('ESTADO WHATSAPP')+1
                columna_hora_whatsapp = sheet_df.columns.to_list().index('HORA WHATSAPP')+1
                columna_mes = sheet_df.columns.to_list().index('MES')+1
                columna_poliza = sheet_df.columns.to_list().index('POLIZA')+1

                _logger.info(f"columna_estado_correo: {columna_estado_correo} - columna_estado_whatsapp: {columna_estado_whatsapp} - columna_hora_whatsapp: {columna_hora_whatsapp} - columna_mes: {columna_mes} - columna_poliza: {columna_poliza} **********")

                google_drive_config.actualizar_registro(
                            nombre_hoja,
                            poliza,
                            status_mail,
                            status_whatsapp,
                            hora_whatsapp,
                            sheet,
                            columna_estado_correo,
                            columna_estado_whatsapp,
                            columna_hora_whatsapp,
                            columna_mes,
                            columna_poliza,
                            month,
                            sheet_df)
                
                time.sleep(3)
                contador += 1
                contador2 += 1 
                if contador == 10:
                    contador = 0
                    time.sleep(5)
                _logger.info(f"Actualizando {contador2}/{cantidad_registros}")
            time.sleep(5)
        _logger.info("Terminó la actualización de los registros en las hojas de Google Drive")
        return True

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
    # mail_id = fields.Many2one('mail.mail', string='Correo electrónico')
    mail_id = fields.Integer(string='Correo electrónico')
    # state = fields.Selection(related='mail_id.state', string='Estado', readonly=True)
    state = fields.Char(string='Estado', readonly=True)
    tipo = fields.Selection([('vencimiento', 'Vencimiento'), ('renovacion', 'Renovación')], string='Tipo', default='renovacion')
    mes = fields.Char(string='Mes')
    year = fields.Integer(string='Año')
    subjet = fields.Char(string='Asunto')
    email_to = fields.Char(string='Destinatario')
    tipo_mensaje = fields.Selection([('Mail', 'Mail'), ('Whatsapp', 'Whatsapp')], string='Tipo de mensaje')
    ramo = fields.Char(string='Ramo')


