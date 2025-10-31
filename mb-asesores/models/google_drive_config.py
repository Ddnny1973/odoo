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
from gspread.exceptions import WorksheetNotFound


_logger = logging.getLogger(__name__)

class GoogleDriveConfig(models.Model):
    _name = 'google.drive.config'
    _description = 'Google Drive Configuration'

    cliente_id = fields.Many2one('res.partner', string='Cliente')
    clave = fields.Char(string='Clave')
    valor = fields.Char(string='Valor')
    descripcion = fields.Char(string='Descripción')

    def autenticar_google_drive(self):
        _logger.info('Entrando en la función autenticar_google_drive')
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
        credentials_json_path = os.path.join(pathglocal, 'credenciales', 'credentials.json')

        # Verificar si las rutas y archivos existen
        if not os.path.exists(token_pickle_path):
            _logger.info('No existe el archivo token.pickle')
        if not os.path.exists(credentials_json_path):
            _logger.error('No existe el archivo credentials.json')
            return None, None, None

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
                # flow = InstalledAppFlow.from_client_secrets_file(
                #     pathglocal + 'credenciales/credentials.json', SCOPES)
                # creds = flow.run_local_server(port=0)
                flow = InstalledAppFlow.from_client_secrets_file(credentials_json_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Guardamos las credenciales para la próxima vez
            with open(token_pickle_path, 'wb') as token:
                pickle.dump(creds, token)
        else:
            _logger.info('Existen credenciales y no están caducadas **************')

        try:
            gc = gspread.authorize(creds)
            servicio_drive = build('drive', 'v3', credentials=creds)
        except Exception as e:
            _logger.error(f'Error al autorizar gspread o construir el servicio de Google Drive: {e}')
            return None, None, None

        _logger.info('Saliendo de la función autenticar_google_drive')

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
            permiso = {
                'role': 'reader',
                'type': 'anyone'
            }

            # Solo establecer la fecha de expiración si no es un permiso de tipo "dominio" o "cualquiera"
            if tiempo_expiracion_horas and permiso['type'] not in ['domain', 'anyone']:
                permiso['expirationTime'] = (datetime.datetime.utcnow() + datetime.timedelta(hours=tiempo_expiracion_horas)).isoformat() + 'Z'

            servicio_drive.permissions().create(
                fileId=archivo,
                body=permiso
            ).execute()

            # Obtener la URL de acceso al archivo
            url_acceso = f"https://drive.google.com/uc?id={archivo}"
            _logger.info(f"URL de acceso: {url_acceso}")
            return url_acceso

        except HttpError as e:
            _logger.error(f"No se pudo obtener la URL de acceso para el archivo con ID {archivo}. Detalles: {str(e)}")
            return None
    
    # def crear_url_de_acceso(self, servicio_drive, archivo, tiempo_expiracion_horas=24):
    #     try:
    #         permiso = servicio_drive.permissions().create(
    #             fileId=archivo,
    #             body={
    #                 'role': 'reader',
    #                 'type': 'anyone',
    #                 'expirationTime': (datetime.datetime.utcnow() + datetime.timedelta(hours=tiempo_expiracion_horas)).isoformat() + 'Z'
    #             }
    #         ).execute()

    #         # Obtener la URL de acceso al archivo
    #         url_acceso = f"https://drive.google.com/uc?id={archivo}"
    #         # _logger.info(f"URL de acceso: {url_acceso}")
    #         return url_acceso

    #     except HttpError as e:
    #         print(f"No se pudo obtener la URL de acceso para el archivo con ID {id_archivo_adjunto}. Detalles: {str(e)}")
    #         return None

    def listar_archivos_en_carpeta(self, servicio_drive, id_carpeta, ruta_padre=''):
        # ✅ Validar que id_carpeta no sea None
        if id_carpeta is None:
            _logger.warning("ID de carpeta es None, retornando lista vacía")
            return []
            
        try:
            resultados = servicio_drive.files().list(
                q=f"'{id_carpeta}' in parents",
                pageSize=1000, fields="files(id, name, mimeType)").execute()
        except HttpError as e:
            _logger.error(f"Error al listar archivos en carpeta {id_carpeta}: {str(e)}")
            return []
        
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
        """
        Corrige los nombres de las columnas del DataFrame y elimina duplicados.
        
        Este método:
        1. Renombra columnas usando un mapeo predefinido
        2. Detecta y elimina columnas duplicadas que causan warnings en pandas
        3. Registra información detallada para debugging
        
        Esto soluciona el warning: "DataFrame columns are not unique, some columns will be omitted"
        """
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
        
        # Log the original columns for debugging
        _logger.info(f"Columnas originales del DataFrame: {list(df.columns)}")
        
        # Rename columns using the mapping
        for columna_vieja, columna_nueva in columnas_a_cambiar.items():
            if columna_vieja in df.columns:
                df = df.rename(columns={columna_vieja: columna_nueva})
        
        # Check for duplicate columns after renaming
        columnas_duplicadas = df.columns[df.columns.duplicated()].tolist()
        if columnas_duplicadas:
            _logger.warning(f"Se encontraron columnas duplicadas después de la corrección: {columnas_duplicadas}")
            
            # Handle duplicate columns by keeping only the first occurrence and dropping the rest
            # This prevents the pandas warning about non-unique columns
            df = df.loc[:, ~df.columns.duplicated()]
            _logger.info(f"Columnas duplicadas eliminadas. Columnas finales: {list(df.columns)}")
        
        # 🔧 LIMPIAR CAMPOS CON ESPACIOS: Especialmente el campo MES
        _logger.info("🧹 Limpiando espacios en campos de texto...")
        
        # Limpiar campo MES si existe
        if 'MES' in df.columns:
            valores_originales = df['MES'].unique()[:5]  # Mostrar máximo 5 ejemplos
            _logger.info(f"   📅 MES - Valores originales (muestra): {valores_originales}")
            
            # Limpiar espacios y convertir a mayúsculas
            df['MES'] = df['MES'].astype(str).str.strip().str.upper()
            
            valores_limpios = df['MES'].unique()[:5]  # Mostrar máximo 5 ejemplos
            _logger.info(f"   📅 MES - Valores limpios (muestra): {valores_limpios}")
        
        # Limpiar otros campos de texto importantes
        campos_texto = ['TOMADOR', 'CORREO', 'ESTADO CORREO', 'ESTADO WHATSAPP', 'COMPANIA']
        for campo in campos_texto:
            if campo in df.columns:
                # Solo limpiar si es texto, mantener NaN como NaN
                df[campo] = df[campo].astype(str).str.strip()
                _logger.info(f"   🧹 Campo '{campo}' limpiado")
        
        _logger.info("✅ Limpieza de campos completada")
        
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
                                'NOMBRE': 'TOMADOR',
                                'Nombre': 'TOMADOR',
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
                    
                # Apply column corrections and handle duplicates
                _logger.info(f"Procesando hoja '{hoja.title}' con {len(df)} filas y {len(df.columns)} columnas")
                _logger.info(f"Columnas originales en '{hoja.title}': {list(df.columns)}")
                
                for columna_vieja, columna_nueva in columnas_a_cambiar.items():
                    if columna_vieja in df.columns:
                        df = df.rename(columns={columna_vieja: columna_nueva})
                
                # Check for and handle duplicate columns
                columnas_duplicadas = df.columns[df.columns.duplicated()].tolist()
                if columnas_duplicadas:
                    _logger.warning(f"Columnas duplicadas encontradas en hoja '{hoja.title}': {columnas_duplicadas}")
                    # Keep only the first occurrence of duplicate columns
                    df = df.loc[:, ~df.columns.duplicated()]
                    _logger.info(f"Columnas duplicadas eliminadas en '{hoja.title}'. Columnas finales: {list(df.columns)}")
                
                # Asignar el DataFrame al nombre de la hoja en el diccionario
                dataframes[df_nombre] = df
                
            except gspread.exceptions.GSpreadException as e:
                # Manejar la excepción de fila de encabezado no única
                hojas_no_creadas.append(hoja.title)

        return dataframes, hojas_no_creadas, hojas_corregido

    # Buscar posición de la columna en el DF
    # @api.model
    # def buscando_columna(self, columnname, sheet_df):
    #     if type(sheet_df) == dict:
    #         sheet_df = pd.DataFrame(sheet_df)
    #     try:
    #         column_position = sheet_df.columns.get_loc(columnname) + 1
    #     except (ValueError, KeyError):
    #         column_position = -1
    #         print(f"No se encontró la columna '{columnname}' en el DataFrame.")
    #     return column_position
    
    @api.model
    def buscando_columna(self, columnname, sheet):
        # sheet: objeto Worksheet de gspread
        headers = sheet.row_values(1)  # Primera fila, usualmente los encabezados
        try:
            column_position = headers.index(columnname) + 1  # +1 porque gspread es 1-based
        except ValueError:
            column_position = -1
            print(f"No se encontró la columna '{columnname}' en la hoja de Google Sheets.")
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
    def cargar_hoja(self, nombre_hoja, hoja_gc, servicio_drive, gc, pathgdrive, month, year):
        filename = 'VENCIMIENTOS ' + year
        _logger.info(f"L483 - filename {filename} - nombre_hoja {nombre_hoja}")
        _logger.info(f"L484 - servicio_drive: {servicio_drive} - gc: {gc} - pathgdrive: {pathgdrive} - month: {month} - year: {year}")

        try:
            sheet = gc.open(filename).worksheet(nombre_hoja.strip())
        except WorksheetNotFound:
            error_msg = f"Hoja '{nombre_hoja.strip()}' no encontrada en el archivo '{filename}' de Google Sheets"
            _logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error al abrir la hoja '{nombre_hoja.strip()}': {str(e)}"
            _logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        registros = sheet.get_all_records()
        sheet_df = pd.DataFrame(registros)
        
        # Verificar integridad del DataFrame inicial
        self.verificar_integridad_dataframe(sheet_df, f"DataFrame inicial de hoja {nombre_hoja}")
        
        sheet_df.reset_index(drop=True, inplace=True)
        # Establecer el índice del DataFrame como el número de fila
        sheet_df.index = sheet_df.index + 2
        sheet_df = self.corregir_columnas(sheet_df)
        
        # Verificar integridad después de la corrección de columnas
        if not self.verificar_integridad_dataframe(sheet_df, f"DataFrame corregido de hoja {nombre_hoja}"):
            _logger.error("❌ El DataFrame aún tiene problemas después de la corrección de columnas")
        
        sheet_df['POLIZA'] = sheet_df['POLIZA'].astype(str)
        
        # Convertir el DataFrame a una lista de diccionarios
        sheet_df_dict = sheet_df.to_dict(orient='records')
        # 🔧 NUEVA LÓGICA: Buscar archivos usando IDs de carpeta
        _logger.info(f"Buscando archivos para {month}/{year} en pathgdrive: {pathgdrive}")
        
        # pathgdrive es siempre un ID de carpeta
        id_root_base = pathgdrive
        
        # Buscar carpeta año dentro de la carpeta base
        id_year = self.obtener_id_carpeta_por_nombre_en_padre(servicio_drive, year, id_root_base)
        if id_year:
            # Buscar carpeta mes dentro de la carpeta año
            id_root = self.obtener_id_carpeta_por_nombre_en_padre(servicio_drive, month, id_year)
            if id_root:
                _logger.info(f"Encontrada carpeta mes {month} con ID: {id_root}")
                lista_archivos = pd.DataFrame(self.listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))
            else:
                _logger.warning(f"No se encontró carpeta mes '{month}' en año {year}")
                lista_archivos = pd.DataFrame()
        else:
            _logger.warning(f"No se encontró carpeta año '{year}' en carpeta base {pathgdrive}")
            lista_archivos = pd.DataFrame()
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

    def obtener_id_carpeta_por_nombre_en_padre(self, servicio_drive, nombre_carpeta, id_padre):
        """Buscar una carpeta por nombre dentro de una carpeta padre específica"""
        try:
            _logger.info(f"🔍 Buscando carpeta '{nombre_carpeta}' en padre {id_padre}")
            
            # Primero, listar todas las carpetas en el padre para debug
            todas_carpetas = servicio_drive.files().list(
                q=f"mimeType='application/vnd.google-apps.folder' and '{id_padre}' in parents",
                pageSize=100, fields="files(id, name)").execute()
            
            carpetas_disponibles = [carpeta['name'] for carpeta in todas_carpetas.get('files', [])]
            _logger.info(f"📁 Carpetas disponibles en {id_padre}: {carpetas_disponibles}")
            
            # Buscar la carpeta específica
            resultados = servicio_drive.files().list(
                q=f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder' and '{id_padre}' in parents",
                pageSize=1, fields="files(id, name)").execute()
            
            archivos = resultados.get('files', [])
            
            if archivos:
                _logger.info(f"✅ Encontrada carpeta {nombre_carpeta} con ID: {archivos[0]['id']}")
                return archivos[0]['id']
            else:
                _logger.warning(f"❌ No se encontró la carpeta {nombre_carpeta} en {id_padre}")
                return None
        except Exception as e:
            _logger.error(f"❌ Error buscando carpeta {nombre_carpeta} en {id_padre}: {str(e)}")
            return None

    @api.model
    def verificar_integridad_dataframe(self, df, nombre_contexto="DataFrame"):
        """
        Método utilitario para verificar la integridad de un DataFrame
        y detectar posibles problemas que puedan causar warnings o errores.
        """
        _logger.info(f"🔍 Verificando integridad de {nombre_contexto}")
        
        # Verificar columnas duplicadas
        columnas_duplicadas = df.columns[df.columns.duplicated()].tolist()
        if columnas_duplicadas:
            _logger.warning(f"⚠️ Columnas duplicadas en {nombre_contexto}: {columnas_duplicadas}")
            return False
        
        # Verificar columnas vacías
        columnas_vacias = [col for col in df.columns if col.strip() == '']
        if columnas_vacias:
            _logger.warning(f"⚠️ Columnas con nombres vacíos en {nombre_contexto}: {len(columnas_vacias)} columnas")
        
        # Verificar columnas con nombres muy similares
        columnas_similares = []
        for i, col1 in enumerate(df.columns):
            for j, col2 in enumerate(df.columns):
                if i < j and col1.strip().upper() == col2.strip().upper():
                    columnas_similares.append((col1, col2))
        
        if columnas_similares:
            _logger.warning(f"⚠️ Columnas con nombres similares en {nombre_contexto}: {columnas_similares}")
        
        _logger.info(f"✅ {nombre_contexto} verificado - {len(df.columns)} columnas únicas")
        _logger.info(f"📋 Columnas: {list(df.columns)}")
        
        return len(columnas_duplicadas) == 0



