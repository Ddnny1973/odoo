# models/vencimientos.py
from odoo import api, fields, models, _
# from odoo.addons.queue_job.job import job
import logging

import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
import pandas as pd
import datetime
import re

_logger = logging.getLogger(__name__)

class Vencimientos(models.Model):
    _name = 'mb_asesores.vencimientos'
    _description = 'Vencimientos'
    # _inherit = ['mail.thread', 'mail.activity.mixin']
    # _inherit = ['mb_asesores.GoogleDriveConfig']

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
    correo = fields.Char(string='Correo')
    mensaje = fields.Char(string='Mensaje')
    archivo = fields.Char(string='Archivo')
    url = fields.Char(string='URL')

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

    @api.model
    # @job
    def descarga_vencimientos(self):
        _logger.info('Entrando en la función descarga_vencimientos')
        # Instanciar el modelo google.drive.config
        google_drive_config = self.env['google.drive.config']

        # Buscar ID odoo del usuario MB-Asesores
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id
        _logger.info(f"ID del administrador: {id_mb}")

        # Actualizar registro en el modelo google.drive.config con la clave descarga_vencimientos
        # Crear variable En ejecución: hora de inicio
        inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        valor = "En ejecución: " + inicio
        self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})
        self.env.cr.commit()  # confirmar los cambios en la base de datos

        # Crear diccionario para los meses
        meses = {
                'January': 'enero',
                'February': 'febrero',
                'March': 'marzo',
                'April': 'abril',
                'May': 'mayo',
                'June': 'junio',
                'July': 'julio',
                'August': 'agosto',
                'September': 'septiembre',
                'October': 'octubre',
                'November': 'noviembre',
                'December': 'diciembre'
                }

        servicio_drive = google_drive_config.autenticar_google_drive()

        # Buscar proyecto mb-asesores en modulo google.drive.config para el cliente_id = id_admin
        pathgdrive = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-gdrive')]).valor
        pathglocal = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-local')]).valor
        nombrearchivovencimientos = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'vencimientos')]).valor

        id_root=google_drive_config.obtener_id_carpeta_por_nombre(servicio_drive, pathgdrive)

        nombre_archivo = pathgdrive + '/renovaciones/' + nombrearchivovencimientos
        nombre_archivo_destino = pathglocal + nombrearchivovencimientos

        nombre_archivo_destino = re.sub(r'\s', '_', nombre_archivo_destino)

        _logger.info(f"nombre_archivo: {nombre_archivo}")
        _logger.info(f"nombre_archivo_destino: {nombre_archivo_destino}")

        # Descargar y cargar el archivo con pandas
        id_archivo = google_drive_config.obtener_id_archivo_por_nombre(servicio_drive, nombre_archivo)
        df_vencimientos = google_drive_config.descargar_archivo(servicio_drive, id_archivo, nombre_archivo_destino)

        # Mostrar un mensaje de terminación
        _logger.info('Descarga completada con éxito.')

        hojas = ['LISTADO VENCIMIENTOS', 'AUTOS']

        # Abrir achivo con pandas y usar la hoja LISTADO VENCIMIENTOS para cargar en el modelo vencimientos
        if os.path.exists(nombre_archivo_destino):
            with pd.ExcelFile(nombre_archivo_destino, engine='openpyxl') as xls:
                # Realiza operaciones con el archivo Excel si es necesario
                # Crear data frame segùn la hoja, tomando la variable hojas
                for nombre_hoja in hojas:
                    if nombre_hoja == 'LISTADO VENCIMIENTOS':
                        df_vencimientos = pd.read_excel(xls, sheet_name=nombre_hoja)
                        # Cambiando todos los valores nan por un valor null
                        df_vencimientos = df_vencimientos.fillna('')
                    elif nombre_hoja == 'AUTOS':
                        # Eliminar primera fila y usar la segunda como encabezado
                        df_autos = pd.read_excel(xls, sheet_name=nombre_hoja, skiprows=1)
                        # Cambiando todos los valores nan por un valor null
                        df_autos = df_autos.fillna('')
        else:
            _logger.info('El archivo no existe')

        # Mapear campos de df a campos del modelo
        df_vencimientos.rename(columns={'Ramo': 'ramo',
                                        'Póliza Ramo': 'id_poliza',
                                        'Nro DNI Tomador': 'dni_tomador',
                                        'Nombre Tomador': 'tomador',
                                        'Forma de Pago ': 'formadepago',
                                        'Fecha Fin Vigencia': 'finvigencia',
                                        'Aviso': 'aviso'},
                                        inplace=True
                                )

        # Buscar el correo y el mensaje en la hoja AUTOS
        df_autos.rename(columns={'POLIZA': 'id_poliza',
                                 'CORREO': 'correo',
                                 'Mensaje Wsp': 'mensaje'},
                                 inplace=True
                        )
        df_autos = df_autos[['id_poliza', 'correo', 'mensaje']]
        df_vencimientos = df_vencimientos.merge(df_autos, on='id_poliza', how='left')

        # Cargar los registros en el modelo
        for index, row in df_vencimientos.iterrows():
            # Buscar el registro basado en algún criterio
            # Corregir el id de la poliza, debe tener 12 caracteres, completar con 0 a la izquierda. Primero convertir a string
            row['id_poliza'] = str(row['id_poliza']).zfill(12)
            record = self.search([('id_poliza', '=', row['id_poliza'])], limit=1)

            # Obtener el nombre del mes en español y en minúsculas
            mes_ingles = row['finvigencia'].strftime('%B').lower()
            row['mes'] = meses[mes_ingles.capitalize()]

            # Buscar el archivo adjunto
            # nombre_archivo = f"/backup/renovaciones/{row['finvigencia'].year}/{row['mes']}/sura/autos/RENOVACION AUTOS SURA- {row['id_poliza']} 2024-2025.pdf"
            nombre_archivo = pathgdrive + '/renovaciones/' + f"{row['finvigencia'].year}/{row['mes']}/sura/autos/CARATULA_{row['id_poliza']}.pdf"
            _logger.info(f"nombre_archivo: {nombre_archivo}")
            url = ''

            # Verificar si se encontró el registro
            if record:
                # Actualizar el registro
                record.write({
                    'ramo': row['ramo'], 
                    'id_poliza': row['id_poliza'],
                    'dni_tomador': row['dni_tomador'],
                    'tomador': row['tomador'],
                    'formadepago': row['formadepago'],
                    'finvigencia': row['finvigencia'],
                    'aviso': row['aviso'],
                    'mes': row['mes'],
                    'year': row['finvigencia'].year,
                    'correo': row['correo'],
                    'mensaje': row['mensaje'],
                    'archivo': nombre_archivo,
                    'url': url
                })
                _logger.info('Registro actualizado')
            else:
                # Crear un nuevo registro
                self.create({
                    'ramo': row['ramo'], 
                    'id_poliza': row['id_poliza'],
                    'dni_tomador': row['dni_tomador'],
                    'tomador': row['tomador'],
                    'formadepago': row['formadepago'],
                    'finvigencia': row['finvigencia'],
                    'aviso': row['aviso'],
                    'mes': row['mes'],
                    'year': row['finvigencia'].year,
                    'correo': row['correo'],
                    'mensaje': row['mensaje'],
                    'archivo': nombre_archivo,
                    'url': url
                })
        
        # Enviar correo electrónico por cada registro donde el campo Aviso sea igual a ok
        _logger.info('Enviando correos electrónicos')
        contador = 0
        for record in self.search([('aviso', '=', 'ok')]):
            # Buscando el id del archvio en Google Drive y la URL
            _logger.info(f"Buscando el id del archivo: {record.archivo}")
            id_archivo_adjunto = google_drive_config.obtener_id_archivo_por_nombre(servicio_drive, record.archivo)
            if id_archivo_adjunto:
                url = google_drive_config.crear_url_de_acceso(servicio_drive, id_archivo_adjunto)
                record.write({'url': url})
            else:
                url = ''
            # Enviar correo electrónico
            asunto = 'Vencimiento de póliza' + ' ' + record.id_poliza + ' ' + record.tomador
            destinatario = record.correo
            mensaje = record.mensaje
            # Adicionar la UR al mensaje
            mensaje = mensaje + '\n' + "URL archivo renovación: " + url
            record.enviar_correo(asunto, destinatario, mensaje)
            contador += 1
        
        # Actualizar registro de control en el modelo google.drive.config con la clave descarga_vencimientos
        fin = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duracion = datetime.datetime.strptime(fin, "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
        valor = "Terminado: " + fin + " - Duración: " + str(duracion)
        self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'descarga_vencimientos')]).write({'valor': valor})

        # Crear JSON que reporte la cantidad de registros actualizados y la duración de la ejecución
        json = {
            'registros_actualizados': contador,
            'duracion': str(duracion)
        }

        return json

    # Función para enviar correo electrónico
    def enviar_correo(self, asunto, destinatario, mensaje):
        self.ensure_one()

        mail_values = {
            'email_from': 'info-mesa@gestorconsultoria.com.co',
            'email_to': destinatario,
            'subject': asunto,
            'body_html': mensaje,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        # Registrar envìo de correo electrónico en el modelo correo.enviado
        self.env['mb_asesores.correo_enviado'].create({
            'id_poliza': self.id_poliza,
            'mail_id': mail.id,
            'state': mail.state
        })


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

