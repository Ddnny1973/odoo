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
import requests

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
    def corregir_columnas(self, registros):
        """
        Estandariza los nombres de columnas de los registros obtenidos de Google Sheets.
        """
        columnas_a_cambiar = {
            'Nro Documento': 'ID',
            'Nro DOCUMENTO': 'ID',
            'Nro DOCUMENTO ': 'ID',
            'Nro DNI Tomador': 'ID',
            'Tomador ID': 'ID',
            'CC CLIENTE': 'ID',
            'PÓLIZA': 'POLIZA',
            '# PÓLIZA': 'POLIZA',
            '# POLIZA': 'POLIZA',
            'Codigo Contrato Op ID': 'POLIZA',
            'CORREO DE ENVIO': 'CORREO',
            'FORMA DE PAGO ': 'FORMA DE PAGO',
            'PRIMA CON IVA 2024': 'PRIMA',
            'PRIMA 2024': 'PRIMA',
            'Prima 2024': 'PRIMA',
            'PRIMA CON IVA 2025': 'PRIMA',
            'PRIMA 2025': 'PRIMA',
            'Prima 2025': 'PRIMA',
            'PLAN': 'TIPO DE PLAN',
            'INICIO VIGENCIA': 'FIN DE VIGENCIA',
            'FECHA FIN': 'FIN DE VIGENCIA',
            'Fecha Expedicion Contrato ID': 'FIN DE VIGENCIA',
            'Mensaje Wsp': 'MENSAJE',
            'MENSAJE DE WSP': 'MENSAJE',
            'MENSAJE WSP': 'MENSAJE',
            'CORREO DEL DENVIO': 'MENSAJE',
            'Numero_Celular_Contacto': 'CELULAR',
            'Nombre Corto ': 'NOMBRE CORTO',
            'Nombre Corto': 'NOMBRE CORTO',
            'NOMBRE CLIENTE': 'TOMADOR',
            'Nombre': 'TOMADOR',
            'NOMBRE': 'TOMADOR',
            'Tomador DESC': 'TOMADOR',
            'PLACA ': 'PLACA',
            'COMPAÑÍA': 'COMPANIA'
        }
        if not registros:
            return registros
        # Solo si hay registros y son dicts
        if isinstance(registros, list) and isinstance(registros[0], dict):
            for i, row in enumerate(registros):
                for columna_vieja, columna_nueva in columnas_a_cambiar.items():
                    if columna_vieja in row:
                        row[columna_nueva] = row.pop(columna_vieja)
                registros[i] = row
        return registros
    
    @api.model
    def enviar_whatsapp_pendientes(self, enviar=None):
        """
        Envía mensajes de WhatsApp a todos los registros pendientes según la lógica del notebook EnvioMejorado-2025-WppApi.
        Independiente del flujo de correos. Ejecutable desde menú.
        """
        _logger.info("[WPP] Iniciando envío de WhatsApp pendientes desde menú Odoo *********************")
        google_drive_config = self.env['google.drive.config']
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
        hojas_config = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')], limit=1).valor
        meses_config = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')], limit=1).valor
        year = google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'year')], limit=1).valor
        # Log de cómo se recibe la variable hojas_config
        _logger.info(f"[WPP-DEBUG] Valor original de hojas_config: {hojas_config!r}")
        if hojas_config:
            hojas_raw = [h for h in hojas_config.split(",")]
            hojas = [h.strip().replace("[", "").replace("]", "").replace("'", "") for h in hojas_raw if h.strip()]
        else:
            hojas = []
            _logger.info(f"[WPP-DEBUG] hojas_config vacío, hojas = []")
        meses = [m.strip().upper() for m in meses_config.split(',')] if meses_config else []
        # creds, gc, servicio_drive = google_drive_config.autenticar_google_drive()

        _logger.info(f"[WPP] Hojas configuradas (antes de variables): {hojas}")
        # Si no se pasa 'enviar', obtenerlo de variables (compatibilidad)
        if enviar is None:
            status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion, enviar = self.variables(month=None, year=year, hojas=hojas, control=None)
        else:
            status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion, _ = self.variables(month=None, year=year, hojas=hojas, control=None)

        # 🔧 CORRECCIÓN: Convertir hojas de vuelta a lista si viene como string
        if isinstance(hojas, str):
            hojas = [h.strip() for h in hojas.split(',') if h.strip()]
            _logger.info(f"[WPP] Hojas convertidas de string a lista: {hojas}")
        
        _logger.info(f"[WPP] Hojas finales (después de variables): {hojas}")

        contador = 0
        contador_enviados = 0
        contador_no_enviados = 0
        detalles = []
        fallidos = 0
        
        # 🔧 INICIALIZAR VARIABLES: Definir antes del if para evitar UnboundLocalError
        mes_recibido = month.upper() if month else 'N/A'
        year_recibido = year
        hojas_recibido = hojas
        inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fin = inicio  # Valor por defecto, se actualizará si entra al if
        
        #################################
        _logger.info(f"Entrando al IF enviar whatsapp status {status} ************")
        if (status == 'enviar' or status == 'enviar whatsapp' or status == 'enviando whatsapp' or 1==1):
            _logger.info(f"Entrando al IF enviar whatsapp ************")
            mes_FILTRO = month
            # hojas ya es una lista limpia
            hojas_gc = hojas
            hojas = [a.strip().replace(" ", "_").upper() for a in hojas_gc]

            # Actualizar registro en el modelo google.drive.config con la clave descarga_vencimientos
            # Actualizar hora de inicio específica para el envío de WhatsApp
            inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            valor = "En ejecución: " + inicio
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})
            self.env.cr.commit()  # confirmar los cambios en la base de datos

            # Enviar WhatsApp por cada registro donde el campo Aviso sea igual a ok
            _logger.info('Enviando WhatsApp ******************')

            for hoja_gc in hojas_gc:
                hoja = hoja_gc.upper()
                try:
                    df_sheets, sheet, sheet_df_dict, lista_archivos = google_drive_config.cargar_hoja(hoja, hoja_gc, servicio_drive, gc, pathgdrive, mes_FILTRO, year)
                except ValueError as e:
                    _logger.error(f"⏭️ Saltando hoja '{hoja_gc}' en WhatsApp: {str(e)}")
                    continue


                # Lógica especial para PROVISION/PRUEBAS-PROVISION
                if hoja in ['PRUEBAS-PROVISION', 'PROVISION']:
                    _logger.info(f"[WPP-DEBUG] Hoja: {hoja} | Param 'enviar': '{enviar}' | ESTADO únicos: {df_sheets['ESTADO'].unique() if 'ESTADO' in df_sheets.columns else 'N/A'} | CONTROL únicos: {df_sheets['CONTROL'].unique() if 'CONTROL' in df_sheets.columns else 'N/A'}")
                    estado_col = df_sheets['ESTADO'].apply(self.normalize_text)
                    control_col = df_sheets['CONTROL'] if 'CONTROL' in df_sheets.columns else pd.Series(['']*len(df_sheets))
                    if enviar and enviar.lower() in ['condiciones de renovación', 'condiciones de renovacion']:
                        df_filtrado = df_sheets[
                            (df_sheets['MES'].str.upper() == mes_FILTRO)
                            & (estado_col == 'condiciones de renovacion')
                            & (control_col.isna() | (control_col == '') | (control_col == 'pendiente'))
                        ].copy()
                        _logger.info(f"📊 HOJA {hoja}: {len(df_filtrado)} registros filtrados para WhatsApp (condiciones de renovacion)")
                    elif enviar and enviar.lower() in ['renovación', 'renovacion']:
                        df_filtrado = df_sheets[
                            (df_sheets['MES'].str.upper() == mes_FILTRO)
                            & (estado_col == 'renovacion')
                        ].copy()
                        _logger.info(f"📊 HOJA {hoja}: {len(df_filtrado)} registros filtrados para WhatsApp (renovacion, sin filtro de 'enviado condiciones')")
                    else:
                        # Si no hay parámetro válido, no se envía nada
                        df_filtrado = df_sheets.iloc[0:0].copy()
                        _logger.info(f"📊 HOJA {hoja}: parámetro 'enviar' no válido, no se filtran registros para WhatsApp")
                else:
                    # Para otras hojas, agregar filtro: URL debe tener información
                    df_filtrado = df_sheets[
                        (df_sheets['MES'].str.upper() == mes_FILTRO)
                        & (
                            df_sheets['CONTROL'].isna()
                            | (df_sheets['CONTROL'] == '')
                            | (df_sheets['CONTROL'] == 'pendiente')
                            | (df_sheets['CONTROL'] == 'pendiente enviar whatsapp')
                        )
                        & (df_sheets['URL'].notna() & (df_sheets['URL'] != ''))
                    ].copy()
                    _logger.info(f"📊 HOJA {hoja}: {len(df_filtrado)} registros filtrados para envío (mes={mes_FILTRO}, estado=pendiente/vacío, url con info)")

                # 📋 LOG: Mostrar lista de pólizas que cumplen filtros iniciales
                if len(df_filtrado) > 0:
                    polizas_filtradas = df_filtrado['POLIZA'].tolist()
                    _logger.info(f"📋 PÓLIZAS CANDIDATAS para envío en {hoja}: {polizas_filtradas}")
                else:
                    _logger.warning(f"⚠️ No hay pólizas candidatas para envío en {hoja}")
                for index, row in df_filtrado.iterrows():
                    contador += 1
                    # Ajustar poliza a 12 caracteres
                    
                    
                    poliza = str(row['POLIZA'])
                    _logger.info(f"L684 - Entró a: {row['POLIZA']} - {poliza} ramo {hoja} mes: {row['MES']} ************")

                    poliza = row.get('POLIZA', '')
                    nombre = row.get('TOMADOR', '')
                    id = str(row.get('ID', '')).strip()
                    celular = str(row.get('CELULAR', '')).strip()
                    mensaje = row.get('MENSAJE', '')
                    url = row.get('URL', '')
                    id_cliente = row.get('ID', '')
                    estado_wsp = str(row.get('ESTADO WHATSAPP', '')).strip().lower()
                    # Normalizar número
                    phone_number = celular.replace('+', '').replace(' ', '').replace('-', '')
                    if len(phone_number) == 10 and phone_number.startswith('3'):
                        phone_number = '57' + phone_number
                    elif len(phone_number) == 12 and phone_number.startswith('57') and phone_number[2] == '3':
                        pass
                    else:
                        _logger.warning(f"[WPP] Número inválido: {celular} (póliza {poliza})")
                        fallidos += 1
                        detalles.append({'poliza': poliza, 'celular': celular, 'motivo': 'número inválido'})
                        continue

                    # Preparar mensaje
                    mensaje_final = mensaje
                    if url:
                        mensaje_final += f"\n\nAdjunto: {url}"
                    _logger.info(f"[WPP] Enviando WhatsApp a {phone_number} | Póliza: {poliza} | Hoja: {hoja} | Mes: {mes_FILTRO}")
                    payload = {"number": str(phone_number), 
                               "message": mensaje_final, 
                               "poliza": poliza, 
                               "id_cliente": id_cliente, 
                               "hoja": hoja, 
                               "mes": mes_FILTRO, 
                               "year": year, 
                               "nombre": nombre}
                    url_n8n = "https://n8n.gestorconsultoria.com.co/webhook/wppapi-mb"
                    # url_n8n = "https://n8n.gestorconsultoria.com.co/webhook-test/wppapi-mb"

                    try:
                        _logger.info(f"[WPP - L368] payload {payload} url_n8n {url_n8n}")
                        response = requests.post(url_n8n, json=payload, timeout=30)
                        if response.status_code == 200:
                            contador_enviados += 1
                            estado = 'enviado'
                            _logger.info(f"[WPP - L373] WhatsApp enviado a {phone_number} (póliza {poliza})")
                            # Actualizar estado en la hoja de Google
                            try:
                                column_control = google_drive_config.buscando_columna('CONTROL', sheet)
                                column_estado_whatsapp = google_drive_config.buscando_columna('ESTADO WHATSAPP', sheet)
                                # column_control = google_drive_config.buscando_columna('CONTROL', df_sheets)
                                # column_estado_whatsapp = google_drive_config.buscando_columna('ESTADO WHATSAPP', df_sheets)
                                _logger.info(f"[WPP-DEBUG - L378] Hoja: {hoja} | Columnas encontradas - CONTROL: {column_control}, ESTADO WHATSAPP: {column_estado_whatsapp}")
                                poliza_trm = str(row['POLIZA']).lstrip('0')
                                row_idx = google_drive_config.buscar_fila(row['MES'], poliza_trm, df_sheets)
                                # Solo para PROVISION/PRUEBAS-PROVISION aplicar lógica especial de estado
                                if hoja in ['PRUEBAS-PROVISION', 'PROVISION']:
                                    estado_poliza = self.normalize_text(row.get('ESTADO', ''))
                                    if estado_poliza == 'condiciones de renovacion':
                                        estado_actualizar = 'enviado condiciones'
                                    elif estado_poliza == 'renovacion':
                                        estado_actualizar = 'enviado renovacion'
                                    else:
                                        estado_actualizar = estado
                                    _logger.info(f"PROVISION: Actualizando CONTROL a '{estado_actualizar}' para póliza {poliza} (tipo: {estado_poliza})")
                                    self.update_sheet_cell_notebook(hoja, row_idx, column_control, estado_actualizar)
                                    _logger.info(f"L392 - ✅ Google Sheets actualizado: fila {row_idx}, columna {column_control}, valor '{estado_actualizar}'")
                                else:
                                    # Para otras hojas, mantener lógica original: solo marcar 'enviado'
                                    self.update_sheet_cell_notebook(hoja, row_idx, column_control, estado)
                                    _logger.info(f"L396 - ✅ Google Sheets actualizado: fila {row_idx}, columna {column_control}, valor '{estado}'")
                                # Actualizar ESTADO WHATSAPP para todas las hojas
                                self.update_sheet_cell_notebook(hoja, row_idx, column_estado_whatsapp, estado)
                                _logger.info(f"L399 - ✅ Google Sheets actualizado: fila {row_idx}, columna {column_estado_whatsapp}, valor '{estado}'")
                            except Exception as e:
                                _logger.error(f"❌ Error actualizando Google Sheets: {e}")
                        else:
                            fallidos += 1
                            estado = f"fallo: HTTP {response.status_code} - {response.text}"
                            _logger.error(f"[WPP] Error HTTP enviando WhatsApp a {phone_number}: {response.text}")
                            detalles.append({'poliza': poliza, 'celular': celular, 'motivo': estado})

                    except requests.exceptions.RequestException as e:
                        _logger.error(f"[WPP] Error enviando WhatsApp a {phone_number}: {e}")

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
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'idle'})

            # Enviar resumen por WhatsApp al número administrador
            resumen_msg = f"RESUMEN ENVÍO WHATSAPP:\n" \
                f"Total procesados: {contador}\n" \
                f"Enviados: {contador_enviados}\n" \
                f"Fallidos: {fallidos}\n" \
                f"Hojas: {hojas_recibido}\n" \
                f"Mes: {mes_recibido}\n" \
                f"Año: {year_recibido}\n" \
                f"Inicio: {inicio}\n" \
                f"Fin: {fin}\n" \
                f"Duración: {str(duracion)}"
            
            payload_admin = {"number": "573104444666", "message": resumen_msg}
            url_n8n = "https://n8n.gestorconsultoria.com.co/webhook/wppapi-mb"
            try:
                _logger.info(f"[WPP] Enviando resumen WhatsApp admin: {payload_admin}")
                requests.post(url_n8n, json=payload_admin, timeout=30)
            except Exception as e:
                _logger.error(f"[WPP] Error enviando resumen WhatsApp admin: {e}")

            payload_admin = {"number": "573004229309", "message": resumen_msg}
            url_n8n = "https://n8n.gestorconsultoria.com.co/webhook/wppapi-mb"
            try:
                _logger.info(f"[WPP] Enviando resumen WhatsApp admin: {payload_admin}")
                requests.post(url_n8n, json=payload_admin, timeout=30)
            except Exception as e:
                _logger.error(f"[WPP] Error enviando resumen WhatsApp admin: {e}")

            return {
                'status': 'ok',
                'resumen': {
                    'total_procesados': contador,
                    'enviados': contador_enviados,
                    'fallidos': fallidos,
                    'hojas': hojas_recibido,
                    'mes': mes_recibido,
                    'year': year_recibido,
                    'inicio': inicio,
                    'fin': fin,
                    'duracion': str(duracion)
                }
            }
        else:
            # Actualizar fin para el caso donde no se procesa WhatsApp
            fin = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _logger.info(f"L725 - status: {status}, no se ejecutó WhatsApp ************")
            return {
                'status': 'ok',
                'mensaje': f'Status actual: {status}, no se ejecutó envío de WhatsApp',
                'resumen': {
                    'total_procesados': contador,
                    'enviados': contador_enviados,
                    'fallidos': fallidos,
                    'hojas': hojas_recibido,
                    'mes': mes_recibido,
                    'year': year_recibido,
                    'inicio': inicio,
                    'fin': fin,
                    'duracion': str(datetime.datetime.strptime(fin, "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S"))
                }
            }

        
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
            # 🔥 NUEVO: Procesar parámetro enviar si existe
            enviar = control[3].strip() if len(control) > 3 else None  # None si no se especifica
        else:
            mensajes_whatsapp = None
            control_mails = None
            estado_provision = None
            enviar = None  # Sin parámetro API = no enviar

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
            
            # 🔧 CORRECCIÓN: Normalizar hojas obtenido de BD si está mal formateado
            if isinstance(hojas, str) and hojas.startswith('[') and hojas.endswith(']'):
                # Si está guardado como string de lista "[...]", convertir a lista y luego a string
                try:
                    import ast
                    hojas_list = ast.literal_eval(hojas)
                    if isinstance(hojas_list, list):
                        hojas = ','.join(hojas_list)
                        _logger.info(f"🔧 VARIABLES: hojas BD mal formateado corregido: '{hojas_list}' -> '{hojas}'")
                except:
                    _logger.warning(f"🔧 VARIABLES: No se pudo corregir hojas BD mal formateado: '{hojas}'")
            
            _logger.info(f"🔧 VARIABLES: hojas obtenido de BD: tipo={type(hojas)}, valor={hojas}")
        else:
            # 🔧 CORRECCIÓN: Normalizar hojas antes de guardar en BD
            if isinstance(hojas, list):
                # Si es lista, convertir a string separado por comas
                hojas_normalizado = ','.join(hojas)
            elif isinstance(hojas, str):
                # Si es string, usar tal como viene
                hojas_normalizado = hojas
            else:
                # Fallback: convertir a string
                hojas_normalizado = str(hojas)
            
            self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')]).write({'valor': hojas_normalizado})
            hojas = hojas_normalizado  # Usar el valor normalizado
            _logger.info(f"🔧 VARIABLES: hojas recibido por parámetro: tipo={type(hojas)}, valor_original={hojas}, valor_normalizado={hojas_normalizado}")

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

        return status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion, enviar

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
        
        # 🔍 VALIDACIÓN DEL AÑO: Asegurar que year tenga valor válido
        if not year or year == '' or year is None:
            _logger.error(f"❌ ERROR: El campo año está vacío o nulo: {year}")
            return False
        
        # Convertir year a entero para validación
        try:
            year_int = int(year)
            if year_int < 2020 or year_int > 2030:
                _logger.warning(f"⚠️ ADVERTENCIA: Año fuera del rango esperado: {year_int}")
        except (ValueError, TypeError):
            _logger.error(f"❌ ERROR: Año no es un número válido: {year}")
            return False
            
        _logger.info(f"✅ Año validado correctamente: {year} (tipo: {type(year)})")
        
        # 🔍 DEBUGGING DEL FILTRO: Verificar datos antes del filtro
        _logger.info(f"📊 ANTES DEL FILTRO:")
        _logger.info(f"   📄 Total registros en DataFrame: {len(df_sheets)}")
        _logger.info(f"   🔤 Mes filtro (mes_FILTRO): '{mes_FILTRO}' (longitud: {len(mes_FILTRO)})")
        _logger.info(f"   📋 Valores únicos en columna MES: {df_sheets['MES'].str.upper().str.strip().unique()}")
        
        # 🔧 FILTRO MEJORADO: Limpiar espacios y hacer comparación robusta
        mes_FILTRO_limpio = mes_FILTRO.upper().strip()
        df_sheets_limpio = df_sheets.copy()
        df_sheets_limpio['MES_LIMPIO'] = df_sheets_limpio['MES'].str.upper().str.strip()
        
        df_filtrado = df_sheets_limpio[df_sheets_limpio['MES_LIMPIO'] == mes_FILTRO_limpio]
        
        # 🔍 DEBUGGING DEL FILTRO: Verificar resultado
        _logger.info(f"📊 DESPUÉS DEL FILTRO:")
        _logger.info(f"   📄 Registros filtrados para mes '{mes_FILTRO_limpio}': {len(df_filtrado)}")
        if len(df_filtrado) == 0:
            _logger.warning(f"⚠️ ADVERTENCIA: No se encontraron registros para el mes '{mes_FILTRO_limpio}'")
            _logger.info(f"   📋 Meses disponibles: {sorted(df_sheets_limpio['MES_LIMPIO'].unique())}")
            return True
        
        # 🔍 LOG ANTES DEL BUCLE
        _logger.info(f"🔄 INICIANDO PROCESAMIENTO EN actualizar_modelo_vencimientos DE {len(df_filtrado)} REGISTROS...")
        
        contador_procesados = 0
        contador_actualizados = 0
        contador_creados = 0
        
        # _logger.info(f"L417 - df_filtrado: {df_filtrado.count()}")
        for index, row in df_filtrado.iterrows():
            contador_procesados += 1
            
            # 🔍 LOG ANTES DE PROCESAR CADA REGISTRO
            # _logger.info(f"📝 PROCESANDO REGISTRO {contador_procesados}/{len(df_filtrado)}: Póliza {row['POLIZA']} - Mes: '{row['MES']}' - Cliente: {row['TOMADOR']}")
            
            # Usar el valor original de la póliza del archivo vencimientos
            poliza = str(row['POLIZA'])
            
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
            
            # 🔍 BÚSQUEDA DE REGISTRO EXISTENTE
            # _logger.info(f"🔍 Buscando registro existente con póliza: '{poliza}'")
            record = self.search([('id_poliza', '=', poliza)], limit=1)
            
            if record:
                # 📝 ACTUALIZACIÓN DE REGISTRO EXISTENTE
                # _logger.info(f"🔄 ACTUALIZANDO registro existente ID: {record.id} - Póliza: '{poliza}' - Cliente: {row['TOMADOR']}")
                # _logger.info(f"   📊 Datos: Año={year}, Mes={mes_FILTRO}, Ramo={ramo}, Email={correos_validos[:50]}...")
                
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
                contador_actualizados += 1
                # _logger.info(f"✅ REGISTRO ACTUALIZADO exitosamente - ID: {record.id} - Póliza: '{poliza}'")
            else:
                # 📝 CREACIÓN DE NUEVO REGISTRO
                # _logger.info(f"➕ CREANDO NUEVO registro - Póliza: '{poliza}' - Cliente: {row['TOMADOR']}")
                # _logger.info(f"   📊 Datos: Año={year}, Mes={mes_FILTRO}, Ramo={ramo}, Email={correos_validos[:50]}...")
                
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
                contador_creados += 1
                # _logger.info(f"✅ NUEVO REGISTRO CREADO exitosamente - ID: {result.id} - Póliza: '{poliza}'")

        # 📊 RESUMEN FINAL DEL PROCESAMIENTO
        _logger.info(f"🎯 RESUMEN FINAL DE PROCESAMIENTO:")
        _logger.info(f"   📄 Total registros procesados: {contador_procesados}")
        _logger.info(f"   🔄 Registros actualizados: {contador_actualizados}")
        _logger.info(f"   ➕ Registros creados: {contador_creados}")
        _logger.info(f"   📅 Mes: {mes_FILTRO} | Año: {year} | Hoja: {hoja_gc}")
        
        if contador_procesados != (contador_actualizados + contador_creados):
            _logger.warning(f"⚠️ ADVERTENCIA: Discrepancia en contadores. Procesados({contador_procesados}) != Actualizados({contador_actualizados}) + Creados({contador_creados})")

        return True

    @api.model
    def consola(self, month=None, year=None, hojas=None, control=None):
        _logger.info(f"Entrando en la función consola month {month} - year {year} - hojas {hojas} - control {control} ************")
        status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion, enviar = self.variables(month, year, hojas, control)
        
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


    # 🔧 FUNCIÓN NORMALIZE_TEXT
    def normalize_text(self, text):
        if pd.isna(text):
            return ''
        import unicodedata
        # Convertir a string y quitar acentos
        text = str(text)
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii')
        return text.lower().strip()
                
    @api.model
    def descarga_vencimientos(self, month=None, year=None, hojas=None, control=None):
        # Obtener hora de Colombia (UTC-5)
        hora_colombia = datetime.datetime.now() - datetime.timedelta(hours=5)
        fecha_hora_inicio = hora_colombia.strftime("%Y-%m-%d %H:%M:%S")
        
        _logger.info(f"🚀🔥 ========================================== 🔥🚀")
        _logger.info(f"🚀🔥 ========================================== 🔥🚀")
        _logger.info(f"🚀🔥 ========================================== 🔥🚀")
        _logger.info(f"🚀🔥 ===== INICIO DESCARGA VENCIMIENTOS ===== 🔥🚀")
        _logger.info(f"⏰ FECHA Y HORA INICIO (Colombia): {fecha_hora_inicio}")
        _logger.info(f"📋 PARÁMETROS: month={month}, year={year}, hojas={hojas}, control={control}")
        _logger.info(f"🚀🔥 ========================================== 🔥🚀")
        
        # _logger.info("Ejecutar actualización desde consola")

        # self.consola()

        status, month, year, hojas, mensajes_whatsapp, control_mails, id_mb, google_drive_config, creds, gc, servicio_drive, lista_archivos, pathgdrive, pathglocal, ejecucion, enviar = self.variables(month, year, hojas, control)
        duracion = 0
        _logger.info(f"Consulta variables: status: {status} - month: {month} - year: {year} - hojas: {hojas} - mensajes_whatsapp: {mensajes_whatsapp} - control_mails: {control_mails} - enviar: {enviar} - id_mb: {id_mb} - google_drive_config: {google_drive_config} ************")
        
        # 🚨 LOG CRÍTICO: Verificar origen de la llamada y comportamiento
        if enviar is None:
            _logger.warning(f"� MODO SIN API: Sin parámetro 'enviar' - Hojas NORMALES funcionan, hojas ESPECIALES bloqueadas")
            _logger.warning(f"   ✅ Hojas normales: Enviarán correos normalmente (valor por defecto)")
            _logger.warning(f"   ❌ Hojas especiales (PROVISION/RENOVACION): NO enviarán (requieren parámetro específico)")
        else:
            _logger.info(f"✅ MODO API: Parámetro 'enviar' recibido: '{enviar}' - Aplicando filtros correspondientes")
        # Si esta vació o idle se ejecuta la función, sino return status
        if (status == 'idle' or status == 'inactivo') or status == '' or status == None or 1 == 1:
            # google_drive_config.search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'ejecutando'})  # Actualizar el estado a idle
            _logger.info(f"Entrando al IF idle ************")
            # try:
            mes_recibido = month.upper()           
            mes_FILTRO = month
            year_recibido = year
            hojas_recibido = hojas
            
            # 🔧 CORRECCIÓN: Manejar hojas como string o lista
            if isinstance(hojas, str):
                # Si hojas es string, dividir por comas
                hojas_gc = hojas.split(",")
            elif isinstance(hojas, list):
                # Si hojas ya es lista, usar directamente
                hojas_gc = hojas
            else:
                # Fallback: convertir a string y dividir
                hojas_gc = str(hojas).split(",")
            
            _logger.info(f"🔧 CORRECCIÓN HOJAS: Tipo original: {type(hojas)}, Valor: {hojas}")
            _logger.info(f"🔧 CORRECCIÓN HOJAS: hojas_gc resultante: {hojas_gc}")
            
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
            
            # 🔍 DEBUG: Verificar estado de hojas_gc antes del bucle
            _logger.info(f"🔍 DEBUG BUCLE: Tipo hojas_gc: {type(hojas_gc)}, Valor: {hojas_gc}")
            _logger.info(f"🔍 DEBUG BUCLE: Longitud hojas_gc: {len(hojas_gc) if hasattr(hojas_gc, '__len__') else 'N/A'}")
            
            for hoja_gc in hojas_gc:
                _logger.info(f"🔍 DEBUG ITERACIÓN: hoja_gc individual: tipo={type(hoja_gc)}, valor='{hoja_gc}'")
                # _logger.info(f"L593 - Entró en hoja: {hoja_gc}")
                hoja = hoja_gc.upper()
                _logger.info(f"🔍 DEBUG ITERACIÓN: hoja procesada: '{hoja}'")
                
                try:
                    df_sheets, sheet, sheet_df_dict, lista_archivos = google_drive_config.cargar_hoja(hoja, hoja_gc, servicio_drive, gc, pathgdrive, mes_FILTRO, year)
                except ValueError as e:
                    _logger.error(f"⏭️ Saltando hoja '{hoja_gc}': {str(e)}")
                    contador_no_enviados += 1
                    continue
                
                # 🔍 LOG VISIBLE: ANTES de actualizar modelo vencimientos
                _logger.info(f"🔍 ANTES DE ACTUALIZAR MODELO VENCIMIENTOS - Hoja: {hoja_gc} ({hoja})")
                _logger.info(f"   📊 Registros cargados desde Google Sheets: {len(df_sheets)}")
                _logger.info(f"   📅 Mes filtro: {mes_FILTRO}")
                _logger.info(f"   📆 Año: {year}")
                _logger.info(f"   🏷️ Ramo/Hoja: {hoja}")
                if 'PROVISION' in hoja.upper():
                    _logger.info(f"   ⚠️ HOJA ESPECIAL PROVISION DETECTADA - Aplicando lógica especial")
                
                result = self.actualizar_modelo_vencimientos(df_sheets, year, mes_FILTRO, hoja, hoja_gc)
                
                # 📊 LOG DETALLADO: Información completa antes del filtro
                _logger.info(f"📊 HOJA {hoja}: ANÁLISIS DETALLADO")
                _logger.info(f"   📄 Total registros en hoja: {len(df_sheets)}")
                
                _logger.info(f"   🎯 Filtro aplicado - Mes: '{mes_FILTRO}', Hoja: '{hoja}'")

                # Filtro inicial con lógica especial para PROVISION
                if 'PROVISION' in hoja.upper():
                    _logger.info(f"   � Aplicando filtro especial PROVISION")
                    
                    # 🎯 FILTRO PROVISION: Incluye registros que puedan necesitar envío
                    df_filtrado = df_sheets[
                        (df_sheets['MES'].apply(self.normalize_text) == mes_FILTRO.lower()) & 
                        (
                            (df_sheets['ESTADO CORREO'].isna()) | 
                            (df_sheets['ESTADO CORREO'] == '') | 
                            (df_sheets['ESTADO CORREO'] == 'pendiente') |
                            (df_sheets['ESTADO CORREO'] == 'enviado condiciones')  # ✅ Necesario para lógica posterior
                        ) &
                        (
                            (df_sheets['ESTADO'].apply(self.normalize_text) == 'condiciones de renovacion') |
                            (df_sheets['ESTADO'].apply(self.normalize_text) == 'renovacion')
                        )
                    ]
                    
                    _logger.info(f"   🔍 FILTRO PROVISION APLICADO:")
                    _logger.info(f"      ✅ Mes: '{mes_FILTRO}' (normalizado a '{mes_FILTRO.lower()}')")
                    _logger.info(f"      ✅ Estado Correo: vacío, null, 'pendiente' O 'enviado condiciones'")
                    _logger.info(f"      ✅ Estado Póliza: 'condiciones de renovacion' OR 'renovacion'")
                    _logger.info(f"      💡 Nota: Lógica posterior decide si enviar basado en estados específicos")
                else:
                    _logger.info(f"   🔧 Aplicando filtro normal mes_FILTRO: {mes_FILTRO}")
                    # Para otras hojas: filtro normal
                    df_filtrado = df_sheets[(df_sheets['MES'].str.upper() == mes_FILTRO) & ((df_sheets['ESTADO CORREO'] == 'pendiente') | (df_sheets['ESTADO CORREO'].isna()) | (df_sheets['ESTADO CORREO'] == ''))]
                
                _logger.info(f"📊 HOJA {hoja}: {len(df_filtrado)} registros pasaron el filtro")
                
                # 📋 LOG: Mostrar lista de pólizas que cumplen filtros iniciales
                if len(df_filtrado) > 0:
                    polizas_filtradas = df_filtrado['POLIZA'].tolist()
                    _logger.info(f"📋 PÓLIZAS CANDIDATAS para envío en {hoja}: {polizas_filtradas[:10]}{'...' if len(polizas_filtradas) > 10 else ''}")
                    
                    # Mostrar detalles de los primeros registros
                    for idx, row in df_filtrado.head(3).iterrows():
                        _logger.info(f"   📄 Registro {idx}: Póliza={row.get('POLIZA', 'N/A')}, Estado Correo='{row.get('ESTADO CORREO', 'N/A')}', Estado='{row.get('ESTADO', 'N/A')}', Mes='{row.get('MES', 'N/A')}'")
                else:
                    _logger.warning(f"⚠️ No hay pólizas candidatas para envío en {hoja}")
                    _logger.info(f"   💡 Posibles razones:")
                    _logger.info(f"      - No hay registros para el mes '{mes_FILTRO}'")
                    _logger.info(f"      - Todos los registros ya tienen estado de correo enviado")
                    _logger.info(f"      - Los estados de póliza no coinciden con los filtros")
                for index, row in df_filtrado.iterrows():
                    # Ajustar poliza a 12 caracteres
                    poliza = str(row['POLIZA'])
                    _logger.info(f"🔍 PROCESANDO PÓLIZA: {poliza}")
                    _logger.info(f"   📄 Detalles: Mes='{row.get('MES', 'N/A')}', Estado Correo='{row.get('ESTADO CORREO', 'N/A')}', Estado='{row.get('ESTADO', 'N/A')}'")
                    _logger.info(f"   👤 Cliente: {row.get('TOMADOR', 'N/A')}, Email: {row.get('CORREO', 'N/A')}")

                    # Verificación de URL con lógica especial para PROVISION
                    puede_enviar = False
                    if 'PROVISION' in hoja.upper():
                        _logger.info(f"   🔧 PROVISION detectado - No requiere URL")
                        puede_enviar = True
                    else:
                        # Para otras hojas se requiere URL y estado pendiente, vacío o NaN
                        estado_correo = row.get('ESTADO CORREO')
                        estado_valido = (
                            estado_correo == 'pendiente' or
                            estado_correo == '' or
                            pd.isna(estado_correo)
                        )
                        puede_enviar = row.get('URL') and str(row.get('URL', '')).strip() != '' and estado_valido
                        _logger.info(f"   🔗 Verificación URL: {'✅ Presente' if (row.get('URL') and str(row.get('URL', '')).strip() != '') else '❌ Faltante'}")
                        _logger.info(f"   📧 Verificación Estado Correo: {'✅ Pendiente/vacío' if estado_valido else '❌ ' + str(estado_correo)}")
                        if not puede_enviar:
                            _logger.info(f"      URL actual: '{row.get('URL', 'N/A')}'")
                            _logger.info(f"      Estado Correo actual: '{estado_correo}'")

                    if puede_enviar:
                        # 🔍 FILTRO CRÍTICO: Verificar si se debe enviar según parámetro API
                        _logger.info(f"L1373 🎯 Verificando autorización de envío: enviar='{enviar}' para hoja: '{hoja}'")
                        
                        # Verificar si es una hoja especial que requiere filtrado específico
                        es_hoja_especial = ('RENOVACION' in hoja.upper() or 
                                          'PRUEBAS-RENOVACION' in hoja.upper() or 
                                          'PROVISION' in hoja.upper())
                        
                        if es_hoja_especial:
                            # 🔒 HOJAS ESPECIALES: Requieren parámetro API específico
                            if enviar is None:
                                _logger.info(f"   ❌ BLOQUEADO: Hoja especial '{hoja}' requiere parámetro 'enviar' específico de API")
                                puede_enviar = False
                            elif enviar.lower() == 'no':
                                # 🚫 NO ENVIAR: Opción explícita de no envío
                                _logger.info(f"   ❌ BLOQUEADO: Parámetro 'enviar' = 'No' - No se envía nada")
                                puede_enviar = False
                            elif enviar.lower() in ['condiciones de renovación', 'condiciones de renovacion']:
                                # 📋 CONDICIONES DE RENOVACIÓN: Solo registros con Estado = "condiciones de renovacion"
                                estado_registro = str(row.get('ESTADO', '')).strip()
                                estado_normalizado = self.normalize_text(estado_registro)
                                estado_correo_actual = str(row.get('ESTADO CORREO', '')).strip().lower()
                                
                                _logger.info(f"   📋 Estado registro: '{estado_registro}' -> normalizado: '{estado_normalizado}'")
                                _logger.info(f"   📧 Estado correo actual: '{estado_correo_actual}'")
                                
                                if estado_normalizado == 'condiciones de renovacion' and estado_correo_actual in ['', 'pendiente'] or pd.isna(row.get('ESTADO CORREO')):
                                    _logger.info(f"   ✅ PERMITIDO: Condiciones de Renovación con estado inicial")
                                else:
                                    _logger.info(f"   ❌ BLOQUEADO: No cumple criterios para Condiciones de Renovación")
                                    puede_enviar = False
                                    
                            elif enviar.lower() in ['renovación', 'renovacion']:
                                # 🔄 RENOVACIÓN: Solo registros con Estado = "renovacion" (sin importar Estado Correo)
                                estado_registro = str(row.get('ESTADO', '')).strip()
                                estado_normalizado = self.normalize_text(estado_registro)
                                _logger.info(f"   📋 Estado registro: '{estado_registro}' -> normalizado: '{estado_normalizado}'")
                                if estado_normalizado == 'renovacion':
                                    _logger.info(f"   ✅ PERMITIDO: Renovación - Estado='{estado_normalizado}' (sin filtro de Estado Correo)")
                                else:
                                    _logger.info(f"   ❌ BLOQUEADO: Estado='{estado_normalizado}' (esperado: 'renovacion')")
                                    puede_enviar = False
                            else:
                                # Para hojas especiales con cualquier otro valor: NO ENVIAR
                                _logger.info(f"   ❌ BLOQUEADO: Hoja especial '{hoja}' recibió parámetro no válido: '{enviar}'")
                                _logger.info(f"   💡 Valores válidos: 'No', 'Condiciones de Renovación', 'Renovación'")
                                puede_enviar = False
                        else:
                            # 🔓 HOJAS NORMALES: El parámetro 'enviar' se ignora, siempre se permite el envío
                            _logger.info(f"   ✅ Hoja normal '{hoja}': ignorando parámetro 'enviar' (valor actual: '{enviar}') y permitiendo envío")
                            # puede_enviar permanece True

                    if puede_enviar:
                        # Construcción de asunto y mensaje con lógica especial para PROVISION
                        if hoja in ['PRUEBAS-PROVISION', 'PROVISION']:
                            # Para PROVISION: formato especial de asunto
                            estado = str(row.get('ESTADO', '')).upper()
                            compania = str(row.get('COMPANIA', ''))
                            asunto = f"{estado} POLIZA {compania} {poliza}"
                            mensaje = row['MENSAJE']  # Solo el mensaje, sin URL
                        else:
                            # Para otras hojas: formato normal
                            asunto = 'Vencimiento de póliza' + ' ' + poliza + ' ' + row['TOMADOR']
                            mensaje = row['MENSAJE']
                            # Adicionar la URL al mensaje
                            mensaje = mensaje + '\n' + "URL archivo renovación: " + row['URL']
                        # _logger.info(f"L590 - Mensaje: {mensaje} ************")

                        # Verificación de envíos previos con lógica especial para PROVISION
                        puede_enviar_correo = True
                        if 'PROVISION' in hoja.upper():
                            _logger.info(f"   🔍 Verificación PROVISION: Confiando en filtro inicial (parámetro enviar='{enviar}')")
                            # Para PROVISION, la verificación inicial ya es suficiente
                            # No necesitamos verificación adicional de envíos previos
                            puede_enviar_correo = True
                            _logger.info(f"   ✅ PROVISION: Verificación de envíos previos simplificada")
                        else:
                            _logger.info(f"   🔍 Verificando envíos previos (lógica normal)")
                            # Lógica normal para otras hojas
                            mail_enviado = self.env['mb_asesores.correo_enviado'].search([('id_poliza', '=', poliza),
                                                                                    ('mes', '=', row['MES']),
                                                                                    ('year', '=', year_recibido),
                                                                                    ('tipo_mensaje', '=', 'Mail')
                                                                                    ])
                            puede_enviar_correo = not mail_enviado
                            _logger.info(f"      📧 Envíos previos encontrados: {len(mail_enviado)}")
                            if mail_enviado:
                                _logger.info(f"      ⏭️ BLOQUEADO: Ya existe envío previo")
                            else:
                                _logger.info(f"      ✅ PERMITIDO: No hay envíos previos")

                        # DECISIÓN FINAL DE ENVÍO
                        if not puede_enviar or not puede_enviar_correo:
                            razon = []
                            if not puede_enviar:
                                razon.append("falta URL" if 'PROVISION' not in hoja.upper() else "verificación inicial fallida")
                            if not puede_enviar_correo:
                                if 'PROVISION' in hoja.upper():
                                    razon.append("lógica PROVISION")
                                else:
                                    razon.append("ya enviado anteriormente")
                            
                            _logger.warning(f"❌ Póliza {poliza} NO SE ENVIARÁ - Razones: {', '.join(razon)}")
                            contador_no_enviados += 1
                        elif control_mails == 'marcar':
                            _logger.info(f"🔄 Póliza {poliza} - MODO MARCAR activado (simulación)")
                            contador_enviados += 1
                        else:
                            _logger.info(f"✅ Póliza {poliza} SÍ SE ENVIARÁ")
                            _logger.info(f"   📧 Detalles: Cliente='{row.get('TOMADOR', 'N/A')}', Email='{row.get('CORREO', 'N/A')}'")
                            _logger.info(f"   📄 Archivo: {row.get('NOMBREARCHIVO', 'N/A')}")
                            if 'PROVISION' not in hoja.upper():
                                _logger.info(f"   🔗 URL: {str(row.get('URL', 'N/A'))[:50]}{'...' if len(str(row.get('URL', ''))) > 50 else ''}")
                            
                            # Seleccionar template con lógica especial para PROVISION
                            if 'PROVISION' in hoja.upper():
                                # Para PROVISION: no usar template, enviar mensaje directo
                                template = ''
                                _logger.info(f"   📝 PROVISION: Enviando mensaje directo sin template")
                            elif hoja in template_dic:
                                _logger.info(f"L634 - Buscando el template hoja: {hoja} ************")
                                if hoja == '040-AUTOMOVILES':
                                    _logger.info(f"Buscando el template en 040-AUTOMOVILES ************")
                                    try:
                                        template = template_autos[row['TIPO DE PLAN'].upper().strip()] or 'mb-asesores.autosglobal'
                                    except KeyError:
                                        _logger.info(f"KeyError: {KeyError} ************")
                                        template = 'mb-asesores.autosglobal'
                                else:
                                    template = template_dic[hoja] or 'mb-asesores.generico'
                            else:
                                template = 'mb-asesores.generico'  # Template por defecto
                            _logger.info(f"template a enviar: {template}")
                            
                            # 🔍 DEBUGGING: Mostrar criterios de búsqueda exactos
                            _logger.info(f"🔍 CRITERIOS DE BÚSQUEDA:")
                            _logger.info(f"   🏷️ id_poliza: '{poliza}' (tipo: {type(poliza)}, longitud: {len(poliza)})")
                            _logger.info(f"   📅 mes: '{row['MES']}' (tipo: {type(row['MES'])}, longitud: {len(str(row['MES']))})")
                            _logger.info(f"   📆 year: '{year_recibido}' (tipo: {type(year_recibido)})")
                            
                            # Buscar registro en vencimientos
                            record = self.search([('id_poliza', '=', poliza), ('mes', '=', row['MES']), ('year', "=", year_recibido)], limit=1)
                            
                            # 🔍 VALIDACIÓN: Verificar que se encontró el registro
                            if not record:
                                _logger.error(f"❌ ERROR: No se encontró registro para póliza '{poliza}', mes '{row['MES']}', año '{year_recibido}'")
                                _logger.error(f"   📊 Búsqueda realizada: id_poliza='{poliza}', mes='{row['MES']}', year='{year_recibido}'")
                                
                                # 🔍 BÚSQUEDA ALTERNATIVA: Intentar encontrar registros similares
                                _logger.info(f"🔍 BÚSQUEDA ALTERNATIVA - Registros con misma póliza:")
                                registros_poliza = self.search([('id_poliza', '=', poliza)])
                                if registros_poliza:
                                    for reg in registros_poliza:
                                        _logger.info(f"   📄 ID: {reg.id}, Póliza: '{reg.id_poliza}', Mes: '{reg.mes}', Año: {reg.year}")
                                else:
                                    _logger.info(f"   ❌ No se encontraron registros con póliza '{poliza}'")
                                
                                _logger.info(f"🔍 BÚSQUEDA ALTERNATIVA - Registros con mismo mes y año:")
                                registros_mes_ano = self.search([('mes', '=', row['MES']), ('year', '=', year_recibido)], limit=5)
                                if registros_mes_ano:
                                    for reg in registros_mes_ano:
                                        _logger.info(f"   📄 ID: {reg.id}, Póliza: '{reg.id_poliza}', Mes: '{reg.mes}', Año: {reg.year}")
                                else:
                                    _logger.info(f"   ❌ No se encontraron registros para mes '{row['MES']}' y año {year_recibido}")
                                
                                contador_no_enviados += 1
                                continue
                            elif len(record) > 1:
                                _logger.warning(f"⚠️ ADVERTENCIA: Se encontraron {len(record)} registros para póliza '{poliza}'. Usando el primero.")
                                record = record[0]  # Tomar solo el primer registro
                            
                            _logger.info(f"✅ Registro encontrado ID: {record.id} para póliza '{poliza}'")
                            _logger.info(f"L773 - Antes de enviar correo {poliza} - {row['POLIZA']}************")
                            
                            success, status_mail, error_message = record.enviar_correo(asunto, mensaje, template, hoja, row['MES'], year_recibido, row['POLIZA'], control_mails)
                            
                            # 📊 LOG: Resultado del envío con más detalle
                            if success:
                                _logger.info(f"L1560 - ✅ ÉXITO - Póliza {poliza}: Correo enviado correctamente")
                                _logger.info(f"L1561 -📧 Estado: {status_mail} | Email: {row['CORREO']} | Cliente: {row['TOMADOR']}")
                                contador_enviados += 1
                            else:
                                _logger.error(f"L1564 - ❌ ERROR - Póliza {poliza}: Falló el envío")
                                _logger.error(f"   💥 Estado: {status_mail} | Error: {error_message}")
                                _logger.error(f"   📧 Email: {row['CORREO']} | Cliente: {row['TOMADOR']}")
                                contador_no_enviados += 1


                            # Solo actualizar Google Sheets y log si el envío fue exitoso
                            if success and status_mail in ('enviado', 'sent'):
                                _logger.info(f"L1572 - Actualizando estado en Google Sheets y log para póliza {poliza} ************")
                                try:
                                    column_mail_status = google_drive_config.buscando_columna('ESTADO CORREO', sheet)
                                    _logger.info(f"L1572 - Columna ESTADO CORREO encontrada en índice {column_mail_status} ************")
                                    # Actualizar el estado del correo en Google Sheets
                                    poliza_trm = str(row['POLIZA']).lstrip('0')
                                    row_idx = google_drive_config.buscar_fila(row['MES'], poliza_trm, df_sheets)

                                    # Determinar el estado correcto para actualizar en Google Sheets
                                    if hoja in ['PRUEBAS-PROVISION', 'PROVISION']:
                                        # Para PROVISION: usar estados específicos basados en el tipo de póliza - usar función normalize_text ya definida
                                        
                                        estado_poliza = self.normalize_text(row.get('ESTADO', ''))
                                        _logger.info(f"      🔧 Valor original ESTADO: '{row.get('ESTADO', 'N/A')}' → Normalizado: '{estado_poliza}'")
                                        if estado_poliza == 'condiciones de renovacion':
                                            estado_actualizar = 'enviado condiciones'
                                        elif estado_poliza == 'renovacion':
                                            estado_actualizar = 'enviado renovacion'
                                        else:
                                            estado_actualizar = status_mail  # fallback
                                        _logger.info(f"PROVISION: Actualizando estado a '{estado_actualizar}' para póliza {poliza} (tipo: {estado_poliza})")
                                    else:
                                        # Para otras hojas: usar el estado normal
                                        estado_actualizar = status_mail

                                    _logger.info(f"L1597 - Actualizando Google Sheets: hoja {hoja}, fila {row_idx}, columna {column_mail_status}, valor '{estado_actualizar}'")
                                    self.update_sheet_cell_notebook(hoja, row_idx, column_mail_status, estado_actualizar)
                                    _logger.info(f"✅ Google Sheets actualizado: fila {row_idx}, columna {column_mail_status}, valor '{estado_actualizar}'")
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
                    elif not row.get('URL') and row.get('ESTADO CORREO') == 'pendiente':
                        _logger.warning(f"⚠️ SIN URL - Póliza {poliza}: No se puede enviar correo (falta archivo PDF)")
                        # if record.mail_status != 'enviado':
                        #     record.write({'mail_status': 'pendiente por adjunto'})
                        # if record.whatsapp_status != 'enviado':
                        #     record.write({'whatsapp_status': 'pendiente por adjunto'})
                        contador_no_enviados += 1
                
                # 📊 LOG: Resumen detallado de la hoja procesada
                _logger.info(f"🎯 RESUMEN HOJA {hoja}:")
                _logger.info(f"   📊 Total registros procesados: {contador}")
                _logger.info(f"   ✅ Registros que pasaron filtro inicial: {len(df_filtrado)}")
                _logger.info(f"   📧 Registros candidatos para envío: {len(df_filtrado)}")
                _logger.info(f"   📈 Tasa de filtrado: {round((len(df_filtrado)/len(df_sheets)*100) if len(df_sheets) > 0 else 0, 1)}%")
                
                # Resetear contadores para la siguiente hoja
                contador = 0
                
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

            # Cambiar status a 'enviando whatsapp'
            # self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')]).write({'valor': 'enviando whatsapp'})

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

            # Enviar resumen por WhatsApp al número administrador
            import requests
            resumen_msg = (
                f"RESUMEN ENVÍO CORREOS:\n"
                f"Total procesados: {contador}\n"
                f"Enviados: {contador_enviados}\n"
                f"No enviados: {contador_no_enviados}\n"
                f"Hojas: {hojas_recibido}\n"
                f"Mes: {mes_recibido}\n"
                f"Año: {year_recibido}\n"
                f"Inicio: {inicio}\n"
                f"Fin: {fin}\n"
                f"Duración: {str(duracion)}"
            )
            url_n8n = "https://n8n.gestorconsultoria.com.co/webhook/wppapi-mb"
            for admin_number in ["573104444666", "573004229309"]:
                payload_admin = {"number": admin_number, "message": resumen_msg}
                try:
                    _logger.info(f"[WPP] Enviando resumen WhatsApp admin: {payload_admin}")
                    requests.post(url_n8n, json=payload_admin, timeout=30)
                except Exception as e:
                    _logger.error(f"[WPP] Error enviando resumen WhatsApp admin: {e}")

            self.env.cr.commit()
            # Lanzar el envío de WhatsApp
            _logger.info(f"L713 - Lanzando el envío de WhatsApp para el mes {mes_FILTRO} ************")
            self.enviar_whatsapp_pendientes(enviar=enviar)
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
