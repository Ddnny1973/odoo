import io
import os
import pickle

import json
# Liberrías globales
import pandas as pd
import time
from odoorpc import ODOO
import re
import datetime

# from datetime import datetime, timedelta
import pytz

from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import gspread
import argparse


###################################
# Funciones Generales
###################################
# Conectar a google
def autenticar_google_drive():
        id_mb = 1

        # Buscar proyecto mb-asesores en modulo google.drive.config para el cliente_id = id_admin
        pathglocal = '/mnt/extra-addons/mb-asesores/consola/'
        
        SCOPES = ['https://www.googleapis.com/auth/drive',
#                   'https://www.googleapis.com/auth/drive.readonly',
                  'https://www.googleapis.com/auth/spreadsheets']

        creds = None

        # La ruta al archivo token.pickle debe ser la misma en la que intentas cargar las credenciales
        # _logger.info('Busca el archivo token.pickle')
        token_pickle_path = pathglocal + 'token.pickle'

        print(f"token_pickle_path: {token_pickle_path}")
        # Si el archivo token.pickle existe, cargamos las credenciales
        if os.path.exists(token_pickle_path):
            # _logger.info('Existe el archivo token.pickle')
            with open(token_pickle_path, 'rb') as token:
                creds = pickle.load(token)
        else:
            print('No existe el archivo token.pickle')

        # Si no hay credenciales o están caducadas, pedimos al usuario autenticarse
        if not creds or not creds.valid:
            print('No existen credenciales o están caducadas')
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                print(f'Credenciales refrescadas: {creds}')
            else:
                print('Solicitando autenticación...')
                flow = InstalledAppFlow.from_client_secrets_file(
                    pathglocal + 'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                print(f'Credenciales obtenidas: {creds}')

            # Guardamos las credenciales para la próxima vez
            with open(token_pickle_path, 'wb') as token:
                pickle.dump(creds, token)
        else:
            print('Existen credenciales y no están caducadas')
        
        gc = gspread.authorize(creds)
        servicio_drive = build('drive', 'v3', credentials=creds)
        print(f"Antes de salir de autenticación Conexión a Google Drive exitosa: {creds} - {gc} - {servicio_drive}")
        return creds, gc, servicio_drive

def obtener_id_carpeta_por_nombre(servicio_drive, nombre_carpeta):
        resultados = servicio_drive.files().list(
            q=f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder'",
            pageSize=1, fields="files(id)").execute()
        
        archivos = resultados.get('files', [])

        if archivos:
#             print(archivos[0]['id'])
            return archivos[0]['id']
        else:
            print('No se encontró')
        return None
    
    
def obtener_id_carpeta_por_ruta(servicio_drive, ruta_completa):
        # Dividir la ruta en partes
        partes_ruta = ruta_completa.strip('/').split('/')

        # Iniciar la búsqueda desde la carpeta root
        id_padre = 'root'

        for nombre_carpeta in partes_ruta:
            # Buscar el ID de la carpeta actual
#             _logger.info(f"Nombre carpeta antes de la función: {nombre_carpeta}")
            id_carpeta = obtener_id_carpeta_por_nombre(servicio_drive, nombre_carpeta)

            if id_carpeta:
                # Actualizar el ID de la carpeta actual para la siguiente iteración
                id_padre = id_carpeta
            else:
                # Si no se encuentra una carpeta, devolver None
                return None
        # _logger.info(f"id carpeta: {id_padre}")
        return id_padre

# Corrige nombres de columnas
def corregir_columnas( df):
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
                                'Tomador DESC': 'TOMADOR',
                                'PLACA ': 'PLACA',
                                'COMPAÑÍA': 'COMPANIA'
                                }
        for columna_vieja, columna_nueva in columnas_a_cambiar.items():
            if columna_vieja in df.columns:
                df = df.rename(columns={columna_vieja: columna_nueva})
        return df

# Carga la hoja a explorar
def cargar_hoja(nombre_hoja, servicio_drive, gc, pathgdrive, month, year):
    """Versión corregida que maneja encabezados duplicados"""
    filename = 'VENCIMIENTOS ' + year
    sheet = gc.open(filename).worksheet(nombre_hoja.strip())
    
    # 🔧 SOLUCIÓN: Obtener headers y crear versión única
    headers_originales = sheet.row_values(1)
    headers_unicos = crear_headers_unicos(headers_originales)
    
    try:
        # Intentar con headers únicos
        registros = sheet.get_all_records(expected_headers=headers_unicos)
        print(f"✅ Cargados {len(registros)} registros de {nombre_hoja}")
    except Exception as e:
        print(f"❌ Error en {nombre_hoja}: {e}")
        # Fallback: usar get_all_values si falla get_all_records
        all_values = sheet.get_all_values()
        if all_values:
            registros = []
            for row in all_values[1:]:  # Saltar headers
                registro = dict(zip(headers_unicos, row))
                registros.append(registro)
        else:
            registros = []
    
    sheet_df = pd.DataFrame(registros)
    sheet_df.reset_index(drop=True, inplace=True)
    # Establecer el índice del DataFrame como el número de fila
    sheet_df.index = sheet_df.index + 2
    sheet_df = corregir_columnas(sheet_df)
    
    # Validar que existe columna POLIZA antes de convertir
    if 'POLIZA' in sheet_df.columns:
        sheet_df['POLIZA'] = sheet_df['POLIZA'].astype(str)
    
    # Convertir el DataFrame a una lista de diccionarios
    sheet_df_dict = sheet_df.to_dict(orient='records')
    
    # Buscando lista de archivos
    pathgdrive_mes = pathgdrive + year + '/' + month
    id_root=obtener_id_carpeta_por_ruta(servicio_drive, pathgdrive_mes)
    lista_archivos = pd.DataFrame(listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))
    return sheet_df, sheet, sheet_df_dict, lista_archivos

# Actulizar celda
def update_cell(sheet, row, column, value):
    fila_poliza = sheet.update_cell(row, column, value)
    return fila_poliza

# Buscar posición de la columna en el DF
def buscando_columna(columnname, sheet_df):
#     column_position = sheet_df.columns.get_loc(columnname) + 1
    try:
        column_position = sheet_df.columns.get_loc(columnname) + 1
    except (ValueError, KeyError):
        column_position = -1
        print(f"No se encontró la columna '{columnname}' en el DataFrame.")
    return column_position

def buscar_fila(mes, poliza, sheet_df):
#     print(f"poliza {poliza} {type(poliza)} ")
    fila_encontrada = sheet_df[(sheet_df['POLIZA'].str.strip() == poliza.strip()) & (sheet_df['MES'].str.upper() == mes.upper())].index
    if not fila_encontrada.empty:
        fila_encontrada_df = fila_encontrada[0]
    else:
        fila_encontrada_df = None
    fila_poliza = None

    if fila_encontrada_df is not None:
#         print(f"El valor de la poliza '{poliza}' se encuentra en la fila {fila_encontrada_df} donde el mes es {mes}.")
        return fila_encontrada_df
    else:
#         print(f"No se encontró el valor de la poliza '{poliza}' en la columna 'POLIZA' donde el mes es {mes}.")
        return None

def listar_archivos_en_carpeta(servicio_drive, id_carpeta, ruta_padre=''):
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
                lista_archivos.extend(listar_archivos_en_carpeta(servicio_drive, id_archivo, ruta_completa))
        return lista_archivos

def validar_correos(correo):
        correos = correo.replace(' y ', ';').replace(' Y ', ';').replace(',', ';').split(';')

        # Validar correos váilidos de la lista
        correos_validos = []
        for correo in correos:
            if correo.find('@') > 0:
                correos_validos.append(correo)
                mail_status = 'pendiente'
            else:
                mail_status = 'correo no disponible'
        correos_validos = ';'.join(correos_validos)
        return correos_validos, mail_status

# def validar_cell(celular, control):
#     # Expresión regular para validar un número de teléfono móvil
#     # patron = r'^\+\d{1,3}\d{8,14}$'
#     patron = r'^\+?\d{1,3}?\d{8,14}$' # Hace el signo más y el código de país opcionales
#     celular = str(celular)

#     # Verificar si el número coincide con el patrón
#     if re.match(patron, celular):
#         if control != 'enviado' or control.lower() == 'enviar':
#             control = 'pendiente enviar whatsapp'
#         return celular, control
#     else:
#         return celular, 'celular no disponible'

def validar_cell(celular, control):
    # Expresión regular para validar un número de teléfono móvil
    patron = r'^\+?\d{1,3}?\d{8,14}$'  # Hace el signo más y el código de país opcionales
    celular = str(celular)
    
    # Separar los números de celular por ';' o ','
    numeros = re.split(r'[;,]', celular)
    
    # Listas para almacenar números válidos y no válidos
    numeros_validos = []
    numeros_no_validos = []
    
    # Verificar cada número de celular
    for numero in numeros:
        numero = numero.strip()  # Eliminar espacios en blanco alrededor del número
        if re.match(patron, numero):
            numeros_validos.append(numero)
        else:
            numeros_no_validos.append(numero)
    
    # Determinar el estado del control   
    if control.lower() == 'enviado':
        pass
    elif (control.lower() != 'enviado' or control.lower() == 'enviar') and len(numeros_no_validos) == 0:
        control = 'pendiente enviar whatsapp'
    else:
        control = f'celular no disponible o no válido {numeros_no_validos}'
        
    # Convertir la lista de números válidos a una cadena separada por ';'
    numeros_validos_str = ';'.join(numeros_validos)
    
    # Devolver la cadena de números válidos, el valor del control y la lista de números no válidos
    return numeros_validos_str, control, numeros_no_validos
    
def get_archivo( servicio_drive, gc, df_sheets, sheet, poliza, mes, lista_archivos, estado_correo, mail_status, mail_enviados, hoja, control):
        # print(f"Dentro de get_archivo ************")
        # aCTUALIZAR gOOGLE CON EL NOMBRE DEL ARCHIVO Y LA url
        # Eliminar ceros a la izquierda de la poliza para la búsqueda
        poliza_trm = str(poliza).lstrip('0')
        # resultados = lista_archivos[lista_archivos['nombrearchivo'].str.contains(poliza_trm, na=False)]
        pattern = re.escape(poliza_trm) + r'\.pdf$'

        resultados = lista_archivos[lista_archivos['nombrearchivo'].str.contains(pattern, na=False, regex=True)]
        column_url = buscando_columna('URL', df_sheets)
        column_nombrearchivo = buscando_columna('NOMBREARCHIVO', df_sheets)
        column_estado_correo = buscando_columna('ESTADO CORREO', df_sheets)
        column_control = buscando_columna('CONTROL', df_sheets)
        row = buscar_fila(mes, poliza_trm, df_sheets)


        # bUSCAR POLIZA EN CORREOS ENVIADOS. bUSCAR POR poliza_trm o poliza y mes
        # print(f"mail_enviados: {mail_enviados} - poliza: {poliza} - poliza_trm: {poliza_trm} - mes: {mes}")
        if mail_enviados.empty == False:
            # mail_enviado = mail_enviados.loc[((mail_enviados['id_poliza'] == poliza) | (mail_enviados['id_poliza'] == poliza_trm)) & (mail_enviados['mes'] == mes)]
            mail_enviado = mail_enviados.loc[((mail_enviados['id_poliza'] == poliza) | (mail_enviados['id_poliza'] == poliza_trm)) & 
                                             (mail_enviados['mes'].str.upper() == mes.upper())
]
        else:
            mail_enviado = pd.DataFrame()

        # print(f"poliza: {poliza_trm} - resultados: {resultados} ************")
        if len(resultados) > 0:
            nombrearchivo = resultados['nombrearchivo'].values[0]
            idarchivo = resultados['idarchivo'].values[0]
            
            url = crear_url_de_acceso(servicio_drive, idarchivo)

            result = sheet.update_cell(row, column_url, url)
            time.sleep(1)
            result = sheet.update_cell(row, column_nombrearchivo, nombrearchivo)
            time.sleep(1)

            # print(f"Archivo encontrado: mail_enviado: {len(mail_enviado)} - mail_status: {mail_status} - control {control}")
            if len(mail_enviado) > 0:
                result = sheet.update_cell(row, column_estado_correo, 'enviado')
                if hoja != "PROVISION" and control != 'enviado':
                    result = sheet.update_cell(row, column_control, control)
            elif len(mail_enviado) == 0:
                result = sheet.update_cell(row, column_estado_correo, 'pendiente')
                if hoja != "PROVISION" and control != 'enviado':
                    result = sheet.update_cell(row, column_control, control)
            elif mail_status == 'no disponible' or estado_correo == '':
                result = sheet.update_cell(row, column_estado_correo, 'correo no disponible')
            elif estado_correo == 'no enviar':
                result = sheet.update_cell(row, column_estado_correo, 'no enviar')
            elif mail_status == 'correo no disponible' or mail_status == 'no disponible':
                result = sheet.update_cell(row, column_estado_correo, 'correo no disponible')
            elif estado_correo == '' or estado_correo == 'pendiente por adjunto':
                result = sheet.update_cell(row, column_estado_correo, mail_status)
            time.sleep(1)
        else:
            # print(f"get_archivo No encontrado: poliza: {poliza_trm}")
            if mail_enviado.empty == False:
                result = sheet.update_cell(row, column_estado_correo, 'enviado')
                if hoja != "PROVISION" and control != 'enviado':
                    result = sheet.update_cell(row, column_control, control)
            elif mail_status == 'correo no disponible' or mail_status == 'no disponible':
                result = sheet.update_cell(row, column_estado_correo, 'correo no disponible')
            elif estado_correo == '' or estado_correo == 'pendiente' or estado_correo == 'correo no disponible' or estado_correo == 'no disponible':
                result = sheet.update_cell(row, column_estado_correo, 'pendiente por adjunto')
    
#         else:
#             print(f"get_archivo No encontrado: poliza: {poliza_trm}")
        return True

def crear_url_de_acceso(servicio_drive, archivo, tiempo_expiracion_horas=24):
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
        # _logger.info(f"URL de acceso: {url_acceso}")
        return url_acceso

    except HttpError as e:
        print(f"No se pudo obtener la URL de acceso para el archivo con ID {archivo}. Detalles: {str(e)}")
        return None
# def crear_url_de_acceso(servicio_drive, archivo, tiempo_expiracion_horas=24):
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
#         print(f"No se pudo obtener la URL de acceso para el archivo con ID {archivo}. Detalles: {str(e)}")
#         return None

# Conexión a Odoo
def odoo_conect():
    odoo = ODOO('65.21.56.197', port=8029)
    odoo.login('aserprem', 'api@gestorconsultoria.com.co', 'Api_2024')
    return odoo

def consultar_configuracion(odoo):
    year = None
    try:
        id_mb = odoo.env['res.partner'].search([('name', '=', 'MB-Asesores')])[0]
    except ValueError:
        id_mb = 14
        print(ValueError)
    hojas_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')])
    hojas = odoo.env['google.drive.config'].read(hojas_id)[0]['valor']
    hojas = hojas.split(",")
    hojas = [elemento.strip() for elemento in hojas]
    
    mes_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')])
    mes = odoo.env['google.drive.config'].read(mes_id)[0]['valor']
    mes = mes.split(",")
    mes = [elemento.strip().upper() for elemento in mes]
    
    status_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')])
    status = odoo.env['google.drive.config'].read(status_id)[0]['valor']
    status = status.strip()
    
    control_whatsapp_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')])
    control_whatsapp = odoo.env['google.drive.config'].read(control_whatsapp_id)[0]['valor'].strip()
    
    pathgdrive_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-gdrive')])
    pathgdrive = odoo.env['google.drive.config'].read(pathgdrive_id)[0]['valor']
    pathglocal_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-local')])
    pathglocal = odoo.env['google.drive.config'].read(pathglocal_id)[0]['valor']

    try:
        year_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'year')])
        year = odoo.env['google.drive.config'].read(year_id)[0]['valor']
    except Exception as e:
        return devolver_datos_error(e)

    return hojas, mes, status, control_whatsapp, pathgdrive, pathglocal, year

def crear_headers_unicos(headers_originales):
    """Crear lista de headers únicos agregando sufijos a los duplicados"""
    headers_unicos = []
    contador_duplicados = {}
    
    for header in headers_originales:
        # Manejar headers vacíos
        if not header or header.strip() == '':
            header = 'COLUMNA_VACIA'
            
        if header in contador_duplicados:
            contador_duplicados[header] += 1
            nuevo_header = f"{header}_DUP_{contador_duplicados[header]}"
        else:
            contador_duplicados[header] = 0
            nuevo_header = header
        
        headers_unicos.append(nuevo_header)
    
    return headers_unicos

def main():
    print("Iniciando script...")
    parser = argparse.ArgumentParser(description="Script para interactuar con Google Drive y Sheets")
    parser.add_argument('--action', help='Acción a realizar: autenticar, obtener_id_carpeta, corregir_columnas, etc.', default='accion_por_defecto')
    # Agregar más argumentos según sea necesario

    args = parser.parse_args()

    if args.action == 'sudo yum install cronie':
        creds, gc, servicio_drive = autenticar_google_drive()
        print("Autenticación completada.")
    # Agregar más condiciones para manejar diferentes acciones
    elif args.action == 'accion_por_defecto':
        
        odoo = odoo_conect()
        # print(f"Conectado a odoo {odoo}...")
        creds, gc, servicio_drive = autenticar_google_drive()
        print(f"Conectado google: {creds} - {gc} - {servicio_drive} - {odoo}")

        hojas, meses, status, control_whatsapp, pathgdrive, pathglocal, year = consultar_configuracion(odoo)
        count_hojas = len(hojas)
        for mes in meses:
            for hoja in hojas:
                print(f"Procesando hoja {hoja} para el mes {year}-{mes}...")
                df_sheets, sheet, sheet_df_dict, lista_archivos = cargar_hoja(hoja, servicio_drive, gc, pathgdrive, mes, year)
                # Mostrar cantidad de registros de df_sheets
                # print(f"Registros en df_sheets: {df_sheets.count()}")
                # Consultar en odoo los correos enviados
                mail_enviado_ids = odoo.env['mb_asesores.correo_enviado'].search([('mes', 'ilike', mes),
                                                                                  ('year', '=', year),
                                                                              ('tipo_mensaje', '=', 'Mail')
                                                                            ])
                mail_enviados = pd.DataFrame(odoo.env['mb_asesores.correo_enviado'].read(mail_enviado_ids))
                # df_filtrado = df_sheets[(df_sheets['MES'].str.upper() == mes) & (df_sheets['URL'].isna() | (df_sheets['URL'] == ''))]
                df_filtrado = df_sheets[(df_sheets['MES'].str.upper() == mes)]
                # print(f"df_filtrado (mes de {mes}): {df_filtrado.count()}")
                # print(f"lista_archivos: {lista_archivos}")
                contador = 0
                for index, row in df_filtrado.iterrows():
                    poliza = str(row['POLIZA']).zfill(12)
                    correo = row['CORREO']
                    estado_correo = row['ESTADO CORREO']
                    correos_validos, mail_status = validar_correos(correo)
                    # print(f"Antes de validar celular {row['CELULAR']} - {row['CONTROL']}")
                    celular, control, celulares_no_validos = validar_cell(row['CELULAR'], row['CONTROL'])
                    # print(f"poliza: {poliza} - correo: {correo} - mail_status {mail_status} - estado_correo: {estado_correo}")
                    print(f"poliza: {poliza} - control: {control} - mail_status {mail_status} - estado_correo: {estado_correo}")
                    actualizar = get_archivo(servicio_drive, gc, df_sheets, sheet, poliza, mes, lista_archivos, estado_correo, mail_status, mail_enviados, hoja, control)
                    if contador == 15:
                        print("Esperando 60 segundos...")
                        time.sleep(60)
                        contador = 0
                    else:
                        contador += 1
                        time.sleep(1)
                if count_hojas > 1:
                    print("Esperando 90 segundos...")
                    time.sleep(90)
    else:
        print(f"Acción '{args.action}' no reconocida.")


if __name__ == "__main__":
    main()

def devolver_datos_error(error):
    """Función para manejar errores y devolver valores por defecto"""
    print(f"Error en consultar_configuracion: {error}")
    # Valores por defecto en caso de error
    hojas = ["040-AUTOMOVILES"]
    mes = ["ENERO"]
    status = "idle"
    control_whatsapp = "si"
    pathgdrive = "/MB-Asesores/"
    pathglocal = "/mnt/extra-addons/mb-asesores/consola/"
    year = "2025"
    return hojas, mes, status, control_whatsapp, pathgdrive, pathglocal, year