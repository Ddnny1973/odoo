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
                'PRUEBAS': 'mb-asesores.vida',
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

    # def guardar_en_log_mail(self, poliza, destinatario, asunto, estado, fecha_envio, mensaje, ramo, compania, year, mes, url_archivo=None, gc=None, sheet=None):
    #     """
    #     Registra un envío de correo en la hoja LogMail de Google Sheets.
    #     Parámetros:
    #         poliza: str
    #         destinatario: str
    #         asunto: str
    #         estado: str (enviado, error, etc)
    #         fecha_envio: str (YYYY-MM-DD HH:MM:SS)
    #         mensaje: str (puede ser resumen o parte del cuerpo)
    #         ramo: str
    #         compania: str
    #         year: int o str
    #         mes: str
    #         url_archivo: str (opcional)
    #     gc: gspread client (opcional, para evitar re-autenticación)
    #     sheet: worksheet de gspread (opcional, para evitar abrir de nuevo el archivo)
    #     """
    #     _logger.info(f"[LOGMAIL] INICIO: póliza={poliza}, destinatario={destinatario}, estado={estado}, fecha={fecha_envio}")
    #     try:
    #         google_drive_config = self.env['google.drive.config']
    #         if sheet is not None:
    #             _logger.info("[LOGMAIL] Usando worksheet 'log_mail' ya cargado (no se vuelve a abrir el archivo)")
    #         else:
    #             if gc is None:
    #                 creds, gc, servicio_drive = google_drive_config.autenticar_google_drive()
    #                 _logger.info("[LOGMAIL] Autenticación Google realizada dentro de guardar_en_log_mail")
    #             else:
    #                 _logger.info("[LOGMAIL] Usando instancia gc existente (no se reautentica)")
    #             nombre_archivo = google_drive_config.search([('clave', '=', 'vencimientos')], limit=1).valor or 'VENCIMIENTOS 2025'
    #             sheet = gc.open(nombre_archivo).worksheet('log_mail')
    #         # Preparar fila
    #         fila = [
    #             str(fecha_envio),
    #             str(poliza),
    #             str(destinatario),
    #             str(asunto),
    #             str(estado),
    #             str(ramo),
    #             str(compania),
    #             str(year),
    #             str(mes),
    #             str(url_archivo) if url_archivo else '',
    #             (mensaje[:200] + '...') if mensaje and len(str(mensaje)) > 200 else str(mensaje)
    #         ]
    #         _logger.info(f"[LOGMAIL] Fila a registrar: {fila}")
    #         try:
    #             result = sheet.append_row(fila, value_input_option='USER_ENTERED')
    #             _logger.info(f"[LOGMAIL] Registro exitoso en LogMail para póliza {poliza}, resultado append_row: {result}")
    #             return True
    #         except Exception as e_append:
    #             _logger.error(f"[LOGMAIL] ERROR al intentar append_row en hoja 'log_mail'.\nFila: {fila}\nExcepción: {repr(e_append)}")
    #             return False
    #     except Exception as e:
    #         _logger.error(f"[LOGMAIL] Error general en guardar_en_log_mail: {repr(e)}")
    #         return False

    # def guardar_en_log_mail(gc, year, log_data):

    #########################################################
    # Evío de whatsapp
    #########################################################
    @api.model
    async def enviar_mensajes_whatsapp(self):
        """
        Busca mensajes listos para enviar, los envía por WhatsApp y registra el resultado.
        Esta función debe ser llamada por la API (macro Excel o proceso de correos).
        """
        # 1. Obtener hojas y meses desde la configuración
        hojas = self.env['google.drive.config'].get_config('hojas')
        meses = self.env['google.drive.config'].get_config('mes_FILTRO')
        year = self.env['google.drive.config'].get_config('year')
        pathgdrive = self.env['google.drive.config'].get_config('root-gdrive')
        gc = self.env['google.drive.config'].get_gspread_client()
        servicio_drive = self.env['google.drive.config'].get_drive_service()

        # 2. Recorrer hojas y meses para buscar mensajes listos
        for hoja in hojas:
            for mes in meses:
                df_sheets, sheet, sheet_df_dict, lista_archivos = cargar_hoja(hoja, servicio_drive, gc, pathgdrive, mes, year)
                df_filtrado = df_sheets[
                    (df_sheets['MES'].str.upper() == mes) &
                    (df_sheets['CONTROL'].str.lower().isin(['pendiente enviar whatsapp', 'enviar', 'pendiente'])) &
                    (df_sheets['URL'].notnull()) &
                    (df_sheets['URL'] != '')
                ]
                for _, row in df_filtrado.iterrows():
                    phone_number = str(row['CELULAR'])
                    mensaje = row['MENSAJE']
                    url = row['URL']
                    poliza = row['POLIZA']
                    id_cliente = row.get('ID', '')
                    tipo = hoja
                    # Validar si ya fue enviado
                    if mensaje_ya_enviado(gc, year, poliza, tipo, mes):
                        continue
                    # Enviar mensaje
                    status = await self._enviar_mensaje_whatsapp(phone_number, mensaje, url, tipo, mes, poliza, id_cliente, gc, year)
                    # Registrar y actualizar estado
                    self._registrar_envio(sheet, mes, poliza, status)
        return True

    async def _enviar_mensaje_whatsapp(self, phone_number, mensaje, url, tipo, mes, poliza, id_cliente, gc, year):
        """Envía el mensaje por WhatsApp usando el webhook n8n"""
        phone_number = str(phone_number).strip()
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]
        if len(phone_number) == 10 and phone_number.startswith('3'):
            phone_number = '57' + phone_number
        elif len(phone_number) == 12 and phone_number.startswith('57') and phone_number[2] == '3':
            pass
        else:
            return 'fallo: número inválido'
        mensaje_completo = f"{mensaje}\n\nAdjunto: {url}"
        payload = {"number": phone_number, "message": mensaje_completo}
        url_n8n = "https://n8n.gestorconsultoria.com.co/webhook/consulta-glue"
        try:
            response = requests.post(url_n8n, json=payload, timeout=30)
            status = "enviado" if response.status_code == 200 else f"fallo: HTTP {response.status_code} - {response.text}"
        except Exception as e:
            status = f"fallo: {str(e)}"
        # Registrar en log
        log_data = {
            'phone_number': phone_number,
            'hora': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'estado': status,
            'mensaje': mensaje,
            'TIPO': tipo,
            'MES': mes,
            'POLIZA': poliza,
            'ID': id_cliente
        }
        guardar_en_log_whatsapp(gc, year, log_data)
        return status

    def _registrar_envio(self, sheet, mes, poliza, estado):
        """Actualiza el estado en la hoja de vencimientos"""
        fila = buscar_fila(mes, poliza, sheet)
        if fila:
            col_control = buscando_columna('CONTROL', sheet)
            if col_control != -1:
                update_cell(sheet, fila, col_control, estado)
            col_estado = buscando_columna('ESTADO WHATSAPP', sheet)
            if col_estado != -1:
                update_cell(sheet, fila, col_estado, estado)
            col_hora = buscando_columna('HORA WHATSAPP', sheet)
            if col_hora != -1:
                update_cell(sheet, fila, col_hora, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    ##################################################################
    def guardar_en_log_mail(self, poliza, destinatario, asunto, estado, fecha_envio, mensaje, ramo, compania, year, mes, url_archivo=None, gc=None, sheet=None):
        _logger.info(f"[LOGMAIL] INICIO: póliza={poliza}, destinatario={destinatario}, estado={estado}, fecha={fecha_envio}")
        try:
            filename = 'VENCIMIENTOS ' + year
            
            # Intentar abrir la hoja LogMail
            try:
                log_sheet = gc.open(filename).worksheet('LogMail')
            except:
                # Si no existe, crearla
                spreadsheet = gc.open(filename)
                log_sheet = spreadsheet.add_worksheet(title='LogMail', rows=1000, cols=10)
                
                # Añadir encabezados
                headers = ['fecha_envio', 'poliza', 'destinatario', 'asunto', 'estado', 'ramo', 'compania', 'year', 'mes', 'url_archivo', 'mensaje']
                log_sheet.append_row(headers)
            
            # Preparar los datos para insertar
            row_data = [
                fecha_envio,
                poliza,
                destinatario,
                asunto,
                estado,
                ramo,
                compania,
                year,
                mes,
                url_archivo,
                mensaje
            ]
            
            # Insertar la fila
            log_sheet.append_row(row_data)
            _logger.info(f"[LOGMAIL] Log guardado en hoja LogMail: {row_data[1]} - {row_data[4]}")
            print(f"✅ Log guardado en hoja LogMail: {row_data[1]} - {row_data[4]}")

        except Exception as e:
            _logger.error(f"[LOGMAIL] Error guardando en LogMail: {str(e)}")
            print(f"❌ Error guardando en LogMail: {str(e)}")

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
        mensajes_whatsapp = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')]).valor
        control_mails = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'control_mails')]).valor
        json = {
                    'status': status,
                    'mes': mes_FILTRO,
                    'hojas': hojas,
                    'mensajes_whatsapp': mensajes_whatsapp,
                    'control_mails': control_mails
                }
        _logger.warning(json)
        return json


    @api.model      
    def get_mail_status_count(self, mes):
        """Obtener estadísticas detalladas de correos por estado"""
        # Usar read_group para optimizar la consulta
        domain = [('mes', '=', mes)]
        groups = self.read_group(
            domain=domain,
            fields=['mail_status'],
            groupby=['mail_status']
        )
        
        # Convertir el resultado a un diccionario más manejable
        mail_status_count = {}
        total_records = 0
        
        for group in groups:
            status = group['mail_status'] or 'sin_estado'
            count = group['mail_status_count']
            mail_status_count[status] = count
            total_records += count
        
        # Agregar información adicional
        mail_status_count['total'] = total_records
        
        return mail_status_count

    @api.model
    def get_pending_emails(self, mes):
        """Obtener correos pendientes con información detallada"""
        # Filtrar registros pendientes (excluyendo estados exitosos)
        domain = [
            ('mes', '=', mes),
            ('mail_status', 'not in', ['enviado', 'sent'])
        ]
        records = self.search(domain)
        
        # Crear lista con información más detallada
        pending_emails = []
        for record in records:
            pending_emails.append({
                'id_poliza': record.id_poliza,
                'tomador': record.tomador,
                'email_to': record.email_to,
                'mail_status': record.mail_status or 'sin_estado',
                'ramo': record.ramo,
                'compania': record.compania
            })
        
        return pending_emails
    
    def generar_registros_mes(self, mes):
        # Suponiendo que tienes una lista llamada registros_mes que contiene los registros del mes
        records = self.search([('mes', '=', mes)])

        # return json_registros_mes
        return records

    @api.model
    # def send_mail_report(self, mes, json):
    def send_mail_report(self, mes):
        """Generar y enviar reporte mejorado de correos"""
        recipient = "danielpatinofernandez@gmail.com, asistente@mbasesoresenseguros.com"
        # recipient = "danielpatinofernandez@gmail.com"
        
        try:
            # Obtener estadísticas mejoradas
            mail_status_count = self.get_mail_status_count(mes)
            pending_emails = self.get_pending_emails(mes)
            
            # Obtener estadísticas adicionales
            total_records = mail_status_count.get('total', 0)
            enviados = mail_status_count.get('enviado', 0) + mail_status_count.get('sent', 0)
            pendientes = len(pending_emails)
            
            # Estadísticas por ramo
            ramo_stats = self.read_group(
                domain=[('mes', '=', mes)],
                fields=['ramo', 'mail_status'],
                groupby=['ramo', 'mail_status'],
                lazy=False
            )

            # Generar Excel con datos mejorados
            records = self.generar_registros_mes(mes)
            df = pd.DataFrame(records.read())

            # Campos seleccionados con mejor orden
            selected_fields = [
                'ramo', 'compania', 'id_poliza', 'dni_tomador', 'tomador', 
                'email_to', 'movil', 'tipo_plan', 'placa', 'formadepago',
                'finvigencia', 'mes', 'year', 'mail_status', 'whatsapp_status',
                'mensaje', 'archivo', 'url', 'correo_temporal', 'mensaje_whatsapp', 'mensaje2'
            ]
            
            # Filtrar solo campos que existen en el DataFrame
            existing_fields = [field for field in selected_fields if field in df.columns]
            df = df[existing_fields]
            
            # Reemplazar valores False/None con cadenas más descriptivas
            df = df.fillna('No disponible').replace(False, 'No disponible')

            # Crear archivo Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Vencimientos', index=False)
                
                # Agregar hoja de estadísticas
                stats_data = {
                    'Métrica': ['Total registros', 'Correos enviados', 'Correos pendientes', 
                               'Tasa de éxito (%)', 'Registros sin estado'],
                    'Valor': [
                        total_records,
                        enviados,
                        pendientes,
                        round((enviados / total_records * 100) if total_records > 0 else 0, 2),
                        mail_status_count.get('sin_estado', 0)
                    ]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)

            excel_data = output.getvalue()

            # Crear adjunto
            attachment = self.env['ir.attachment'].create({
                'name': f'Reporte_Vencimientos_{mes}.xlsx',
                'datas': base64.b64encode(excel_data),
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary'
            })
            
            # Crear contenido HTML mejorado
            content_html = self._generate_html_report(mail_status_count, pending_emails, mes, total_records, enviados)
            
            # Enviar el reporte por n8n usando enviar_correo
            asunto = f'📊 Reporte Detallado de Correos - {mes} ({enviados}/{total_records} enviados)'
            mensaje = content_html
            template = ''  # No se usa plantilla específica
            ramo = 'REPORTE'
            poliza = 'REPORTE'
            # Enviar solo al primer registro del mes, o crear un dummy si no hay
            record = self.search([('mes', '=', mes)], limit=1)
            if not record:
                # Crear un dummy solo para el envío del reporte, forzando el mensaje HTML
                record = self.create({'mes': mes, 'email_to': recipient, 'mensaje': mensaje})
            else:
                # Asegurarse que el email_to sea el destinatario del reporte y el mensaje sea el HTML generado
                record.email_to = recipient
                record.mensaje = mensaje

            success, status_mail, error_msg = record.enviar_correo(
                asunto,
                mensaje,  # Se pasa el HTML generado, no el campo del registro
                '',  # Sin template
                ramo,
                mes,
                record.year if hasattr(record, 'year') else datetime.datetime.now().year,
                poliza,
                control_mails='si'
            )
            if success:
                _logger.info(f"Reporte de correos enviado exitosamente para el mes {mes} (n8n)")
                return "Reporte enviado exitosamente (n8n)"
            else:
                _logger.error(f"Error al enviar reporte por n8n: {error_msg}")
                return f"Error al enviar reporte por n8n: {error_msg}"
            
        except Exception as e:
            _logger.error(f"Error al generar reporte de correos: {str(e)}")
            return f"Error al enviar reporte: {str(e)}"
    
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

        # 🔧 NUEVA LÓGICA: pathgdrive es siempre un ID de carpeta
        print(f"Usando ID de carpeta base: {pathgdrive}")
        id_root_base = pathgdrive
        
        # Buscar carpeta año dentro de la carpeta base
        id_year = google_drive_config.obtener_id_carpeta_por_nombre_en_padre(servicio_drive, year, id_root_base)
        if id_year:
            # Buscar carpeta mes dentro de la carpeta año
            id_root = google_drive_config.obtener_id_carpeta_por_nombre_en_padre(servicio_drive, month, id_year)
            if id_root:
                lista_archivos = pd.DataFrame(google_drive_config.listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))
            else:
                _logger.warning(f"No se encontró carpeta mes '{month}' en año {year}")
                lista_archivos = pd.DataFrame()
        else:
            _logger.warning(f"No se encontró carpeta año '{year}' en carpeta base {pathgdrive}")
            lista_archivos = pd.DataFrame()

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
            # Usar el valor original de la póliza del archivo vencimientos
            poliza = str(row['POLIZA'])
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
        _logger.info(f"Antes de ejecutar el scrip Ruta del script: {ruta_script} ************")
        resultado = subprocess.run(["python3", ruta_script], capture_output=True, text=True)
        _logger.info(f"Resultado de la ejecución del script: {resultado} ************")
        salida = resultado.stdout
        error = resultado.stderr
        json = {
                'salida': salida,
                'error': error
            }
        # _logger.info(f"Salida consola: {json} ********")
        return json
    
    @api.model
    def lanzar_descarga_vencimientos_job(self, month=None, year=None, hojas=None, control=None):
        self.with_delay().descarga_vencimientos(month, year, hojas, control)
        return {'status': 'running', 'message': 'Job lanzado en background'}
    
    @api.model
    def lanzar_consola_job(self, month=None, year=None, hojas=None, control=None):
        _logger.info(f"Entrando en la función lanzar_consola_job month {month} - year {year} - hojas {hojas} - control {control} ************")
        self.with_delay().consola(month, year, hojas, control)
        return {'status': 'running', 'message': 'Job lanzado en background'}


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
            _logger.info('Enviando correos electrónicos ******************')

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
                _logger.info(f"📊 HOJA {hoja}: {len(df_filtrado)} registros filtrados para envío (mes={mes_FILTRO}, estado=pendiente)")
                
                # 📋 LOG: Mostrar lista de pólizas que cumplen filtros iniciales
                if len(df_filtrado) > 0:
                    polizas_filtradas = df_filtrado['POLIZA'].tolist()
                    _logger.info(f"📋 PÓLIZAS CANDIDATAS para envío en {hoja}: {polizas_filtradas}")
                else:
                    _logger.warning(f"⚠️ No hay pólizas candidatas para envío en {hoja}")
                for index, row in df_filtrado.iterrows():
                    # Ajustar poliza a 12 caracteres
                    poliza = str(row['POLIZA'])
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
                            _logger.info(f"⏭️ SALTANDO póliza {poliza}: {'Ya enviado anteriormente' if mail_enviado else 'Modo marcar activado'}")
                            # if control_mails == 'marcar':
                            #     record.write({'mail_status': 'enviado cliente'})
                            #     contador_enviados += 1
                            # else:
                            #     _logger.info(f"Correo electrónico ya enviado: {record.id_poliza} - {record.tomador}")
                        else:
                            _logger.info(f"📧 ENVIANDO CORREO - Póliza: {poliza} | Cliente: {row['TOMADOR']} | Email: {row['CORREO']} | Ramo: {hoja}")
                            _logger.info(f"📄 Archivo PDF: {row.get('NOMBREARCHIVO', 'N/A')} | URL: {row['URL'][:50]}{'...' if len(str(row['URL'])) > 50 else ''}")
                        
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
                            _logger.info(f"L773 - Antes de enviar correo {poliza} - {row['POLIZA']}************")
                            success, status_mail, error_message = record.enviar_correo(asunto, mensaje, template, hoja, row['MES'], year_recibido, row['POLIZA'], control_mails)
                            
                            # 📊 LOG: Resultado del envío con más detalle
                            if success:
                                _logger.info(f"✅ ÉXITO - Póliza {poliza}: Correo enviado correctamente")
                                _logger.info(f"   📧 Estado: {status_mail} | Email: {row['CORREO']} | Cliente: {row['TOMADOR']}")
                                contador_enviados += 1
                            else:
                                _logger.error(f"❌ ERROR - Póliza {poliza}: Falló el envío")
                                _logger.error(f"   💥 Estado: {status_mail} | Error: {error_message}")
                                _logger.error(f"   📧 Email: {row['CORREO']} | Cliente: {row['TOMADOR']}")
                                contador_no_enviados += 1


                            # Solo actualizar Google Sheets y log si el envío fue exitoso
                            if success and status_mail in ('enviado', 'sent'):
                                try:
                                    column_mail_status = google_drive_config.buscando_columna('ESTADO CORREO', df_sheets)
                                    # Actualizar el estado del correo en Google Sheets
                                    poliza_trm = str(row['POLIZA']).lstrip('0')
                                    row_idx = google_drive_config.buscar_fila(row['MES'], poliza_trm, df_sheets)
                                    _logger.info(f"L747 - Actualizando Google Sheets: hoja {hoja}, fila {row_idx}, columna {column_mail_status}, valor '{status_mail}'")
                                    self.update_sheet_cell_notebook(hoja, row_idx, column_mail_status + 1, status_mail)
                                    _logger.info(f"✅ Google Sheets actualizado: fila {row_idx}, columna {column_mail_status}, valor '{status_mail}'")
                                except Exception as e:
                                    _logger.error(f"❌ Error actualizando Google Sheets: {e}")
                                # Sincronizar el campo mail_status en el modelo vencimientos
                                if record:
                                    record.write({'mail_status': status_mail})
                                    _logger.info(f"✅ Campo mail_status actualizado en modelo vencimientos: póliza={poliza}, estado={status_mail}")
                                # Registrar en LogMail
                                _logger.info(f"[LOGMAIL] Llamando a guardar_en_log_mail para póliza={poliza}, destinatario={row['CORREO']}, estado={status_mail}")
                                fecha_envio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                try:
                                    res_log = self.guardar_en_log_mail(
                                        poliza=poliza,
                                        destinatario=row['CORREO'],
                                        asunto=asunto,
                                        estado=status_mail,
                                        fecha_envio=fecha_envio,
                                        mensaje=mensaje,
                                        ramo=hoja,
                                        compania=row.get('COMPANIA', ''),
                                        year=year_recibido,
                                        mes=row['MES'],
                                        url_archivo=row.get('URL', None),
                                        gc=gc,
                                        sheet=sheet
                                    )
                                    _logger.info(f"[LOGMAIL] Resultado guardar_en_log_mail: {res_log}")
                                except Exception as e:
                                    _logger.error(f"[LOGMAIL] Error al llamar a guardar_en_log_mail: {e}")

                        contador += 1
        #             # Si no existe id_archivo_adjunto, actualizar el estado del correo a no disponible
                    elif not row.get('URL') and row.get('ESTADO CORREO') == 'pendiente':
                        _logger.warning(f"⚠️ SIN URL - Póliza {poliza}: No se puede enviar correo (falta archivo PDF)")
                        # if record.mail_status != 'enviado':
                        #     record.write({'mail_status': 'pendiente por adjunto'})
                        # if record.whatsapp_status != 'enviado':
                        #     record.write({'whatsapp_status': 'pendiente por adjunto'})
                        contador_no_enviados += 1
                
                # 📊 LOG: Resumen de la hoja procesada
                _logger.info(f"📊 RESUMEN HOJA {hoja}: Procesados {contador} registros")
                
            # 📊 LOG: Resumen final de todas las hojas
            _logger.info(f"🎯 RESUMEN FINAL ENVÍO DE CORREOS:")
            _logger.info(f"   📧 Correos enviados exitosamente: {contador_enviados}")
            _logger.info(f"   ❌ Correos fallidos: {contador_no_enviados}")
            _logger.info(f"   📝 Total registros procesados: {contador}")
            _logger.info(f"   ✅ Tasa de éxito: {round((contador_enviados/contador*100) if contador > 0 else 0, 1)}%")
            
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
        """
        Envía correo usando n8n, renderizando el cuerpo con la plantilla seleccionada.
        """
        _logger.info(f"L882 - 📧 Enviando a n8n - Póliza: {poliza} | Email: {self.email_to} ****")
        self.ensure_one()
        _logger.info(f"L878 - por pasos ************")

        template_id = None
        success = False
        status_mail = 'pendiente'
        error_msg = None
        # Si se pasa el nombre técnico, usarlo directamente
        if template:
            try:
                template_id = self.env.ref(template)
            except Exception:
                template_id = None
        if not template_id:
            if ramo == '040-AUTOMOVILES' and self.tipo_plan:
                template_name = template_autos.get(self.tipo_plan.upper(), template_dic.get(ramo, 'mb-asesores.generico'))
            else:
                template_name = template_dic.get(ramo, 'mb-asesores.generico')
            try:
                template_id = self.env.ref(template_name)
            except Exception:
                template_id = None

        # Renderizar el cuerpo del correo usando la plantilla
        _logger.info(f"L901 - Antes del render ************")
        if template_id:
            _logger.info(f"Usando plantilla: {template_id.name} ({template_id._name}) para ramo: {ramo} y tipo_plan: {getattr(self, 'tipo_plan', None)}")
            body_html = template_id._render_field('body_html', [self.id])
            mensaje_final = body_html
        else:
            _logger.warning(f"No se encontró plantilla, usando mensaje plano")
            mensaje_final = mensaje

        if control_mails == 'si':
            try:
                success, status_mail, error_msg = self.enviar_a_n8n(
                    poliza=poliza,
                    tomador=self.tomador,
                    email_to=self.email_to,
                    asunto=asunto,
                    mensaje=mensaje_final,
                    template=template_id.xml_id if template_id and hasattr(template_id, 'xml_id') else template,
                    ramo=ramo,
                    mes=mes,
                    year=year,
                    url_archivo=self.url,
                    tipo_plan=self.tipo_plan,
                    compania=self.compania
                )
            except Exception as e:
                error_msg = f'Error enviando a n8n: {str(e)}'
                status_mail = 'error_n8n_json'
                success = False
        elif control_mails == 'marcar':
            _logger.info(f"🔄 Modo marcar: simulando envío exitoso para póliza {poliza}")
            success = True
            status_mail = 'enviado'
            error_msg = "Modo marcar activado"
        else:
            error_msg = f"❌ Parámetro control_mails inválido: {control_mails}"

        # La actualización de Google Sheets se realiza en descarga_vencimientos, donde existen las variables necesarias
        if not success:
            _logger.error(error_msg)
        return success, status_mail, error_msg

    
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

    def _generate_html_report(self, mail_status_count, pending_emails, mes, total_records, enviados):
        """Generar contenido HTML mejorado para el reporte"""
        
        # Calcular tasa de éxito
        success_rate = round((enviados / total_records * 100) if total_records > 0 else 0, 2)
        
        # Estilo CSS para el reporte
        css_style = """
        <style>
            .report-container { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
            .header { background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .summary-box { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 10px 0; }
            .success { color: #28a745; font-weight: bold; }
            .warning { color: #ffc107; font-weight: bold; }
            .danger { color: #dc3545; font-weight: bold; }
            .status-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            .status-table th, .status-table td { border: 1px solid #dee2e6; padding: 8px; text-align: left; }
            .status-table th { background-color: #f8f9fa; }
            .pending-list { max-height: 300px; overflow-y: auto; border: 1px solid #dee2e6; padding: 10px; }
        </style>
        """
        
        content_html = f"""
        {css_style}
        <div class="report-container">
            <div class="header">
                <h2>📊 Reporte de Correos de Vencimientos - {mes.upper()}</h2>
                <p><strong>Fecha del reporte:</strong> {(datetime.datetime.now() - datetime.timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary-box">
                <h3>📈 Resumen Ejecutivo</h3>
                <ul>
                    <li><strong>Total de registros:</strong> {total_records}</li>
                    <li><strong>Correos enviados:</strong> <span class="success">{enviados}</span></li>
                    <li><strong>Correos pendientes:</strong> <span class="{'warning' if len(pending_emails) > 0 else 'success'}">{len(pending_emails)}</span></li>
                    <li><strong>Tasa de éxito:</strong> <span class="{'success' if success_rate >= 80 else 'warning' if success_rate >= 60 else 'danger'}">{success_rate}%</span></li>
                </ul>
            </div>
            
            <div class="summary-box">
                <h3>📋 Estadísticas por Estado</h3>
                <table class="status-table">
                    <thead>
                        <tr>
                            <th>Estado</th>
                            <th>Cantidad</th>
                            <th>Porcentaje</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Agregar filas de estadísticas
        for status, count in mail_status_count.items():
            if status != 'total':
                percentage = round((count / total_records * 100) if total_records > 0 else 0, 1)
                status_display = status.replace('_', ' ').title() if status else 'Sin Estado'
                content_html += f"""
                        <tr>
                            <td>{status_display}</td>
                            <td>{count}</td>
                            <td>{percentage}%</td>
                        </tr>
                """
        
        content_html += """
                    </tbody>
                </table>
            </div>
        """
        
        # Sección de pendientes
        if pending_emails:
            content_html += f"""
            <div class="summary-box">
                <h3>⚠️ Correos Pendientes ({len(pending_emails)})</h3>
                <div class="pending-list">
                    <table class="status-table">
                        <thead>
                            <tr>
                                <th>Póliza</th>
                                <th>Tomador</th>
                                <th>Ramo</th>
                                <th>Estado</th>
                                <th>Email</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Limitar a primeros 50 para evitar emails muy largos
            for pending in pending_emails[:50]:
                content_html += f"""
                            <tr>
                                <td>{pending['id_poliza']}</td>
                                <td>{pending['tomador'][:30]}{'...' if len(pending['tomador']) > 30 else ''}</td>
                                <td>{pending['ramo']}</td>
                                <td>{pending['mail_status']}</td>
                                <td>{pending['email_to'][:30]}{'...' if len(str(pending['email_to'])) > 30 else ''}</td>
                            </tr>
                """
            
            if len(pending_emails) > 50:
                content_html += f"""
                            <tr>
                                <td colspan="5" style="text-align: center; font-style: italic;">
                                    ... y {len(pending_emails) - 50} registros más (ver archivo Excel adjunto)
                                </td>
                            </tr>
                """
            
            content_html += """
                        </tbody>
                    </table>
                </div>
            </div>
            """
        else:
            content_html += """
            <div class="summary-box">
                <h3>✅ Correos Pendientes</h3>
                <p class="success">¡Excelente! No hay correos pendientes para este mes.</p>
            </div>
            """
        
        content_html += """
            <div class="summary-box">
                <h3>📎 Archivo Adjunto</h3>
                <p>El archivo Excel adjunto contiene el detalle completo de todos los registros del mes, incluyendo:</p>
                <ul>
                    <li>Hoja "Vencimientos": Datos completos de todas las pólizas</li>
                    <li>Hoja "Estadísticas": Métricas resumidas del proceso</li>
                </ul>
            </div>
        </div>
        """
        
        return content_html

    def enviar_a_n8n(self, poliza, tomador, email_to, asunto, mensaje, template, ramo, mes, year, url_archivo, tipo_plan, compania):
        """
        Enviar datos de correo al webhook de n8n
        """
        import requests
        import json
        
        webhook_url_test = "https://n8n.gestorconsultoria.com.co/webhook-test/61a30243-1a64-4ae9-9987-fc213ac251ed"
        webhook_url_publica = "https://n8n.gestorconsultoria.com.co/webhook/61a30243-1a64-4ae9-9987-fc213ac251ed"
        webhook_url_local = "http://172.17.0.1:8032/webhook/61a30243-1a64-4ae9-9987-fc213ac251ed"

        # Forzar mensaje como string plano (HTML/texto)
        mensaje_str = mensaje
        if isinstance(mensaje, dict):
            # Si es dict, tomar el primer valor
            primer_valor = next(iter(mensaje.values()))
            # Si el valor es Markup, convertir a string plano
            try:
                # Markup puede tener .unescape() o .striptags(), pero si no, usar str()
                if hasattr(primer_valor, 'unescape'):
                    mensaje_str = primer_valor.unescape()
                elif hasattr(primer_valor, 'striptags'):
                    mensaje_str = primer_valor.striptags()
                else:
                    mensaje_str = str(primer_valor)
            except Exception:
                mensaje_str = str(primer_valor)
        elif not isinstance(mensaje, str):
            mensaje_str = str(mensaje)
        # --- CORRECCIÓN DE RUTAS DE IMÁGENES ---
        if isinstance(mensaje_str, str):
            mensaje_str = mensaje_str.replace('src="/web/image', 'src="https://aserprem.gestorconsultoria.com.co/web/image')

        try:
            _logger.info(f"L1256 - 🚀 Enviando a n8n webhook: {webhook_url_local} ******************")
            _logger.info(f"L1257 - 📦 Record ID: {self.id} | Póliza: {poliza} ****************")
            data = {
                "record_id": self.id,
                "poliza": poliza,
                "tomador": tomador,
                "email_to": email_to,
                "asunto": asunto,
                "mensaje": mensaje_str,
                "template": template,
                "ramo": ramo,
                "mes": mes,
                "year": year,
                "url_archivo": url_archivo,
                "tipo_plan": tipo_plan,
                "compania": compania
            }
            response = requests.post(webhook_url_local, json=data, timeout=30)
            _logger.info(f"L1121 - 📬 Respuesta de n8n: {response.status_code} - {response.text}")
            if response.status_code == 200:
                _logger.info(f"L1262 - ✅ Respuesta 200 de n8n para póliza {poliza}")
                return True, "enviado", None
            else:
                _logger.error(f"L1265 - ❌ Error enviando a n8n: {response.status_code}")
                return False, "error_n8n", None
        except Exception as e:
            _logger.error(f"L1269 - 💥 Error conectando con n8n: {e}")
            return False, "error_conexion_n8n", None
        
    def update_sheet_cell_notebook(self, sheet_name, row, column, value):
        """
        Actualiza una celda en Google Sheets usando el mecanismo del notebook.
        """
        import os
        import pickle
        import gspread
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        # Usar el mismo path que el notebook
        pathglocal = '/mnt/extra-addons/mb-asesores/consola/'
        SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
        token_pickle_path = os.path.join(pathglocal, 'token.pickle')
        credentials_path = os.path.join(pathglocal, 'credentials.json')

        creds = None
        if os.path.exists(token_pickle_path):
            with open(token_pickle_path, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = Credentials.from_authorized_user_file(credentials_path, SCOPES)
            with open(token_pickle_path, 'wb') as token:
                pickle.dump(creds, token)

        gc = gspread.authorize(creds)
        sheet = gc.open("VENCIMIENTOS 2025").worksheet(sheet_name)
        result = sheet.update_cell(row, column, value)
        return result


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
    subject = fields.Char(string='Asunto')
    email_to = fields.Char(string='Destinatario')
    tipo_mensaje = fields.Selection([('Mail', 'Mail'), ('Whatsapp', 'Whatsapp')], string='Tipo de mensaje')
    ramo = fields.Char(string='Ramo')
    mail_id_n8n = fields.Char(string='ID n8n', help="ID del registro en n8n para seguimiento")
