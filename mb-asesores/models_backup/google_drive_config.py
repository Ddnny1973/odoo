# models/google_drive_config.py
from odoo import api, fields, models, _
import os
import io
import datetime
import time
import re
import pickle
import logging
import pandas as pd


#API Google
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import gspread


_logger = logging.getLogger(__name__)

class GoogleDriveConfig(models.Model):
    _name = 'google.drive.config'
    _description = 'Google Drive Configuration'

    cliente_id = fields.Many2one('res.partner', string='Cliente')
    clave = fields.Char(string='Clave')
    valor = fields.Char(string='Valor')
    descripcion = fields.Char(string='Descripción')

    def autenticar_google_drive(self):
        # _logger.info('Entrando en la función autenticar_google_drive')
        id_mb = self.env['res.partner'].search([('name', '=', 'MB-Asesores')]).id

        # Buscar proyecto mb-asesores en modulo google.drive.config para el cliente_id = id_admin
        pathgdrive = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-gdrive')]).valor
        pathglocal = self.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-local')]).valor

        SCOPES = ['https://www.googleapis.com/auth/drive',
                #   'https://www.googleapis.com/auth/drive.readonly',
                  'https://www.googleapis.com/auth/spreadsheets']

        creds = None

        # La ruta al archivo token.pickle debe ser la misma en la que intentas cargar las credenciales
        # _logger.info('Busca el archivo token.pickle')
        token_pickle_path = pathglocal + 'credenciales/token.pickle'

        # Si el archivo token.pickle existe, cargamos las credenciales
        if os.path.exists(token_pickle_path):
            # _logger.info('Existe el archivo token.pickle')
            with open(token_pickle_path, 'rb') as token:
                creds = pickle.load(token)
        else:
            _logger.info('No existe el archivo token.pickle')

        # Si no hay credenciales o están caducadas, pedimos al usuario autenticarse
        if not creds or not creds.valid:
            # _logger.info('No existen credenciales o están caducadas')
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    pathglocal + 'credenciales/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            # Guardamos las credenciales para la próxima vez
            with open(token_pickle_path, 'wb') as token:
                pickle.dump(creds, token)
        else:
            _logger.info('Existen credenciales y no están caducadas **************')

        gc = gspread.authorize(creds)
        servicio_drive = build('drive', 'v3', credentials=creds)

        return creds, gc, servicio_drive
    
    # Funciona para carpetas compartidas
    def obtener_id_carpeta_por_nombre(self, servicio_drive, nombre_carpeta):
        resultados = servicio_drive.files().list(
            q=f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder'",
            pageSize=1, fields="files(id)").execute()
        
        archivos = resultados.get('files', [])

        if archivos:
            print(archivos[0]['id'])
            return archivos[0]['id']
        else:
            print('No se encontró')
        return None
        
    def obtener_id_carpeta_por_ruta(self, servicio_drive, ruta_completa):
        # Dividir la ruta en partes
        partes_ruta = ruta_completa.strip('/').split('/')

        # Iniciar la búsqueda desde la carpeta root
        id_padre = 'root'

        for nombre_carpeta in partes_ruta:
            # Buscar el ID de la carpeta actual
            _logger.info(f"Nombre carpeta antes de la función: {nombre_carpeta}")
            id_carpeta = self.obtener_id_carpeta_por_nombre(servicio_drive, nombre_carpeta)

            if id_carpeta:
                # Actualizar el ID de la carpeta actual para la siguiente iteración
                id_padre = id_carpeta
            else:
                # Si no se encuentra una carpeta, devolver None
                return None
        # _logger.info(f"id carpeta: {id_padre}")
        return id_padre

    def obtener_id_archivo_por_nombre(self, servicio_drive, nombre_archivo):
        try:
            # _logger.info(f"Archivo: {nombre_archivo}")
            partes_ruta = nombre_archivo.strip('/').split('/')
            nombre_archivo = partes_ruta[-1]
            ruta_archivo = '/'.join(partes_ruta[:-1])
            
            id_carpeta = self.obtener_id_carpeta_por_ruta(servicio_drive, ruta_archivo)
            # _logger.info(f"id carpeta (obtener_id_archivo_por_nombre): {id_carpeta}")
            resultados = servicio_drive.files().list(
                q=f"'{id_carpeta}' in parents and mimeType != 'application/vnd.google-apps.folder'",
                pageSize=1000, fields="files(id, name)").execute()

            archivos = resultados.get('files', [])

            for archivo in archivos:
                # _logger.info(f"Lista de archivos: {archivos}")
                # _logger.info(f"Buscando Archivo: {nombre_archivo}")
                # Buscar sin tener encuenta mayùsculas y minùsculas
                if archivo['name'].lower() == nombre_archivo.lower():
                    _logger.info(f"Archivo encontrado: {archivo['id']}")
                    return archivo['id']
            return None

        except Exception as e:
            _logger.info(f"No se pudo obtener el ID del archivo. Detalles: {e}")
            return None
        
    def descargar_y_cargar_archivo(self, servicio_drive, id_archivo):
        # _logger.info('Entrando en la función descargar_y_cargar_archivo')
        try:
            # Descargar el contenido del archivo
            request = servicio_drive.files().get_media(fileId=id_archivo)
            archivo_descargado = io.BytesIO()
            downloader = MediaIoBaseDownload(archivo_descargado, request)
            descarga_completa = False
            while descarga_completa is False:
                _, descarga_completa = downloader.next_chunk()

            # # Cargar el contenido del archivo en un DataFrame de pandas
            # archivo_df = pd.read_csv(archivo_descargado)

            return True
            # return archivo_df

        except Exception as e:
            _logger.info(f"No se pudo obtener el ID del archivo. Detalles: {e}")
            return None
        
    # Descargar el archivo
    def descargar_archivo(self, servicio_drive, id_archivo, nombre_archivo_destino):
        # _logger.info(f'Entrando en la función descargar_archivo {id_archivo}')
        # _logger.info(f'Archivo destino {nombre_archivo_destino}')

        request = servicio_drive.files().get_media(fileId=id_archivo)
        fh = io.FileIO(nombre_archivo_destino, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Progreso de descarga: {int(status.progress() * 100)}%")

        # No se necesita el nombre del archivo
        # print(f'Archivo descargado en: {nombre_archivo_destino}')
        path = '/mnt/compartida/mb-asesores/VENCIMIENTOS 2024.xlsx'
        fh.close()
        with open(nombre_archivo_destino, 'rb') as fh:
            with open(path, 'wb') as out:
                out.write(fh.read())

        _logger.info(f'Archivo descargado en: {path}')
        return "Archivo descargado correctamente" 
    
    def crear_url_de_acceso(self, servicio_drive, archivo, tiempo_expiracion_horas=24):
        try:
            permiso = servicio_drive.permissions().create(
                fileId=archivo,
                body={
                    'role': 'reader',
                    'type': 'anyone',
                    'expirationTime': (datetime.datetime.utcnow() + datetime.timedelta(hours=tiempo_expiracion_horas)).isoformat() + 'Z'
                }
            ).execute()

            # Obtener la URL de acceso al archivo
            url_acceso = f"https://drive.google.com/uc?id={archivo}"
            # _logger.info(f"URL de acceso: {url_acceso}")
            return url_acceso

        except HttpError as e:
            print(f"No se pudo obtener la URL de acceso para el archivo con ID {id_archivo_adjunto}. Detalles: {str(e)}")
            return None

    def listar_archivos_en_carpeta(self, servicio_drive, id_carpeta, ruta_padre=''):
        resultados = servicio_drive.files().list(
            q=f"'{id_carpeta}' in parents",
            pageSize=1000, fields="files(id, name, mimeType)").execute()
        
        archivos = resultados.get('files', [])

        lista_archivos = []
        for archivo in archivos:
            nombre_archivo = archivo["name"]
            id_archivo = archivo["id"]
            tipo_archivo = archivo["mimeType"]
            
            # Construir la ruta completa del archivo o carpeta
            ruta_completa = os.path.join(ruta_padre, nombre_archivo)

            # Crear URL de acceso y agregarla a la lista
            #url_acceso = crear_url_de_acceso(servicio_drive, id_archivo, tiempo_expiracion_horas=1)
            url_acceso = ''
            
            # Agregar información a la lista
            lista_archivos.append({
                                    'Tipo': tipo_archivo,
                                    'nombrearchivo': nombre_archivo,
                                    'idarchivo': id_archivo,
                                    'ruta': ruta_completa,
                                    'url': url_acceso
                                })

            if tipo_archivo == 'application/vnd.google-apps.folder':
                # Si el archivo es una carpeta, listar sus archivos con mayor indentación y la ruta actual
                lista_archivos.extend(self.listar_archivos_en_carpeta(servicio_drive, id_archivo, ruta_completa))
        return lista_archivos

    def obtener_id_archivo_sheet(self, servicio_drive, nombre_archivo):
        try:
            tipo_archivo = 'application/vnd.google-apps.spreadsheet'  # Tipo MIME para hojas de cálculo de Google Sheets
            # Realizar la búsqueda
            results = servicio_drive.files().list(
                q=f"name='{nombre_archivo}' and mimeType='{tipo_archivo}'",
                fields="files(id, name)"
            ).execute()
            
            # Imprimir resultados
            archivos = results.get('files', [])
            for archivo in archivos:
                if archivo['name'] == nombre_archivo:
                    _logger.info(f"ID del archivo sheet: {archivo['id']}")
                    return archivos[0]['id']
            _logger.info(f"No se encontró el archivo sheet: {nombre_archivo}")
            return None
        
        except Exception as e:
            _logger.info(f"No se pudo obtener el ID del archivo. Detalles: {e}")
            return None

    @api.model
    def corregir_columnas(self, df):
        columnas_a_cambiar = {'Nro Documento': 'ID',
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
                                'Tomador DESC': 'TOMADOR',
                                'PLACA ': 'PLACA',
                                'COMPAÑÍA': 'COMPANIA'
                                }
        for columna_vieja, columna_nueva in columnas_a_cambiar.items():
            if columna_vieja in df.columns:
                df = df.rename(columns={columna_vieja: columna_nueva})
        return df
    
    def crear_df_desde_archivo_sheet(self, gc, sheet_id):
        # Leer Archivo sheet
        # Abrir el archivo
        archivo = gc.open_by_key(sheet_id)
        _logger.info(f"Archivo sheet open: {archivo.title}")

        # Obtener la lista de hojas en el archivo
        # Obtener la lista de hojas en el archivo
        hojas = archivo.worksheets()
        hojas_corregido = []
        columnas_a_cambiar = {'Nro Documento': 'ID',
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
                                'Tomador DESC': 'TOMADOR',
                                'PLACA ': 'PLACA',
                                'COMPAÑÍA': 'COMPANIA'
                            }

        # Lista para almacenar las hojas que no pudieron crearse
        hojas_no_creadas = []

        # Crear DF por hoja
        dataframes = {}
        for hoja in hojas:
            try:
                # Obtener el valor de la celda B1
                valor_celda_b1 = hoja.acell('B1').value
                valor_celda_b2 = hoja.acell('B2').value
                
                # Obtener los datos de la hoja
                # datos_hoja = hoja.get_all_records()
                datos_hoja = hoja.get_all_values()
                
                if not datos_hoja:
                    raise gspread.exceptions.GSpreadException("La hoja está vacía.")

                print(f"hoja: {hoja.title} - len(datos_hoja) {len(datos_hoja)} - len(datos_hoja[0]) {len(datos_hoja[0])} ")
                #if len(datos_hoja) > 0 and len(datos_hoja[0]) > 1:
                if len(datos_hoja) > 0 and valor_celda_b1:
                    # Crear un DataFrame
                    df_nombre = hoja.title.replace(" ", "_")  # Reemplazar espacios en blanco con guiones bajos u otros caracteres
                    df = pd.DataFrame(datos_hoja[1:], columns=datos_hoja[0])  # Usar la primera fila como encabezado

                    # Agregar el nombre corregido a la lista
                    hojas_corregido.append(df_nombre)
                
                elif len(datos_hoja) > 0 and valor_celda_b1 is None and valor_celda_b2 is not None:
                    # En el caso de una sola columna, asignar nombres de columna predeterminados
                    df_nombre = hoja.title.replace(" ", "_")
                    df = pd.DataFrame(datos_hoja[2:], columns=datos_hoja[1])

                    # Agregar el nombre corregido a la lista
                    hojas_corregido.append(df_nombre)
                elif len(datos_hoja) > 0 and valor_celda_b2 is None:
                    # En el caso de una sola columna, asignar nombres de columna predeterminados
                    df_nombre = hoja.title.replace(" ", "_")
                    df = pd.DataFrame(datos_hoja[3:], columns=datos_hoja[2])

                    # Agregar el nombre corregido a la lista
                    hojas_corregido.append(df_nombre)
                    
                # df = self.corregir_columnas(df)
                for columna_vieja, columna_nueva in columnas_a_cambiar.items():
                    if columna_vieja in df.columns:
                        df = df.rename(columns={columna_vieja: columna_nueva})
                
                # Asignar el DataFrame al nombre de la hoja en el diccionario
                dataframes[df_nombre] = df
                
            except gspread.exceptions.GSpreadException as e:
                # Manejar la excepción de fila de encabezado no única
                hojas_no_creadas.append(hoja.title)

        return dataframes, hojas_no_creadas, hojas_corregido

    # Buscar posición de la columna en el DF
    @api.model
    def buscando_columna(self, columnname, sheet_df):
        if type(sheet_df) == dict:
            sheet_df = pd.DataFrame(sheet_df)
        try:
            column_position = sheet_df.columns.get_loc(columnname) + 1
        except (ValueError, KeyError):
            column_position = -1
            print(f"No se encontró la columna '{columnname}' en el DataFrame.")
        return column_position
        
    # Buscar fila
    @api.model    
    def buscar_fila(self, mes, poliza, sheet_df):
        # _logger.info(f"Buscando fila en el DataFrame para la póliza '{poliza}' y el mes '{mes}'")
        # _logger.info(sheet_df.columns)
        # _logger.info(sheet_df[['POLIZA', 'MES']])
        fila_encontrada = sheet_df[(sheet_df['POLIZA'].str.strip() == poliza.strip()) & (sheet_df['MES'].str.upper() == mes.upper())]
        if not fila_encontrada.empty:
            # Obtiene el primer índice de las filas encontradas
            numero_de_fila = fila_encontrada.index[0]
        else:
            numero_de_fila = None
        return numero_de_fila
    
    @api.model
    # Carga la hoja a explorar
    def cargar_hoja(self, nombre_hoja, servicio_drive, gc, pathgdrive, month):
        sheet = gc.open('VENCIMIENTOS 2024').worksheet(nombre_hoja.strip())
        registros = sheet.get_all_records()
        sheet_df = pd.DataFrame(registros)
        sheet_df.reset_index(drop=True, inplace=True)
        # Establecer el índice del DataFrame como el número de fila
        sheet_df.index = sheet_df.index + 2
        sheet_df = self.corregir_columnas(sheet_df)
        sheet_df['POLIZA'] = sheet_df['POLIZA'].astype(str)
        # Convertir el DataFrame a una lista de diccionarios
        sheet_df_dict = sheet_df.to_dict(orient='records')
        # Buscando lista de archivos
        pathgdrive_mes = pathgdrive + '/' + month
        id_root=self.obtener_id_carpeta_por_ruta(servicio_drive, pathgdrive_mes)
        lista_archivos = pd.DataFrame(self.listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))
        return sheet_df, sheet, sheet_df_dict, lista_archivos

    # Actulizar celda
    @api.model
    def update_sheet_cell(self, sheet, row, column, value):
        _logger.info(f"Actualizando celda en la fila {row} y columna {column} con el valor '{value}'")
        _logger.info(f"sheet: {sheet}")
        result = sheet.update_cell(row, column, value)
        return result

    def actualizar_registro(self,
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
                            sheet_df):
        
        valor_estado_correo = status_mail
        valor_estado_whatsapp = status_whatsapp

        fila = self.buscar_fila(month, poliza, sheet, columna_mes, columna_poliza, sheet_df)
        # time.sleep(2)
        _logger.info(f"Actualizando registros en sheet columna_poliza: {columna_poliza} columna_mes {columna_mes} fila {fila}")

        # Colocar el valor en la columna 'ESTADO CORREO'
        if fila is not None:
            fila_poliza = sheet.update_cell(fila, columna_estado_correo, valor_estado_correo)  # Suponiendo que columna_estado_correo es el número de la columna "ESTADO CORREO"
            # _logger.info(f"Se ha colocado el valor '{valor_estado_correo}' en la columna 'ESTADO CORREO' para la fila {fila}.")

            fila_poliza = sheet.update_cell(fila, columna_estado_whatsapp, valor_estado_whatsapp)  # Suponiendo que columna_estado_correo es el número de la columna "ESTADO CORREO"
            # _logger.info(f"Se ha colocado el valor '{valor_estado_correo}' en la columna 'ESTADO whatsapp' para la fila {fila}.")
            return True
        else:
            return False 

        

