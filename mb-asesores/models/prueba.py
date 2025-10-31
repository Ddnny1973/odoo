# Cargando Librerías
import json
# Liberrías globales
import pandas as pd
import time
from odoorpc import ODOO
import re
import datetime

import pywhatkit
import pyautogui

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

import io
import os
import pickle

import json
# Liberrías globales
import pandas as pd
import pywhatkit
import pyautogui
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

import io
import os
import pickle

###################################
# Funciones Generales
###################################
# Conectar a google
def autenticar_google_drive():
        # _logger.info('Entrando en la función autenticar_google_drive')
        id_mb = 1

        # Buscar proyecto mb-asesores en modulo google.drive.config para el cliente_id = id_admin
        pathgdrive = 'RENOVACIONES/2024'
        pathglocal = ''
        
        SCOPES = ['https://www.googleapis.com/auth/drive',
#                   'https://www.googleapis.com/auth/drive.readonly',
                  'https://www.googleapis.com/auth/spreadsheets']

        creds = None

        # La ruta al archivo token.pickle debe ser la misma en la que intentas cargar las credenciales
        # _logger.info('Busca el archivo token.pickle')
        token_pickle_path = pathglocal + 'token.pickle'

        # Si el archivo token.pickle existe, cargamos las credenciales
        if os.path.exists(token_pickle_path):
            # _logger.info('Existe el archivo token.pickle')
            with open(token_pickle_path, 'rb') as token:
                creds = pickle.load(token)
        else:
            print('No existe el archivo token.pickle')

        # Si no hay credenciales o están caducadas, pedimos al usuario autenticarse
        if not creds or not creds.valid:
            # _logger.info('No existen credenciales o están caducadas')
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    pathglocal + 'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            # Guardamos las credenciales para la próxima vez
            with open(token_pickle_path, 'wb') as token:
                pickle.dump(creds, token)
        else:
            print('Existen credenciales y no están caducadas')
        
        gc = gspread.authorize(creds)
        servicio_drive = build('drive', 'v3', credentials=creds)

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
def cargar_hoja(nombre_hoja, servicio_drive, gc, pathgdrive, month):
    try:
        sheet = gc.open('VENCIMIENTOS 2024').worksheet(nombre_hoja.strip())
        registros = sheet.get_all_records()
        sheet_df = pd.DataFrame(registros)
        sheet_df.reset_index(drop=True, inplace=True)
        # Establecer el índice del DataFrame como el número de fila
        sheet_df.index = sheet_df.index + 2
        sheet_df = corregir_columnas(sheet_df)
        sheet_df['POLIZA'] = sheet_df['POLIZA'].astype(str)
        # Convertir el DataFrame a una lista de diccionarios
        sheet_df_dict = sheet_df.to_dict(orient='records')
        # Buscando lista de archivos
        pathgdrive_mes = pathgdrive + '/' + month
        id_root=obtener_id_carpeta_por_ruta(servicio_drive, pathgdrive_mes)
        lista_archivos = pd.DataFrame(listar_archivos_en_carpeta(servicio_drive, id_root, ruta_padre=''))
        return sheet_df, sheet, sheet_df_dict, lista_archivos
    except:
        sheet_df = []
        sheet = []
        sheet_df_dict = []
        lista_archivos = []
    return odoo

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
    
# Conexión a Odoo
def odoo_conect():
    try:
        odoo = ODOO('65.21.56.197', port=8029)
        odoo.login('aserprem', 'api@gestorconsultoria.com.co', 'Api_2024')
    except:
        odoo = None
    return odoo

def devolver_datos_error(e):
    id_mb = 14
    hojas = []
    meses = []
    status = 'Error de conexión'
    control_whatsapp = None
    pathgdrive = None
    pathglocal = None
    return hojas, meses, status, control_whatsapp, pathgdrive, pathglocal, id_mb
    

def consultar_configuracion(odoo):
    try:
        id_mb = odoo.env['res.partner'].search([('name', '=', 'MB-Asesores')])[0]
    except Exception as e:
        return devolver_datos_error(e)
        
    try:
        hojas_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'hojas')])
        hojas = odoo.env['google.drive.config'].read(hojas_id)[0]['valor']
    except Exception as e:
        return devolver_datos_error(e)

#     print(f"hojas --> {hojas}")
    if hojas:
        hojas = hojas.split(",")
        hojas = [elemento.strip() for elemento in hojas]
    else:
        hojas = ['']
    
    try:
        mes_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mes_FILTRO')])
        mes = odoo.env['google.drive.config'].read(mes_id)[0]['valor']
    except Exception as e:
        return devolver_datos_error(e)
    mes = mes.split(",")
    mes = [elemento.strip().upper() for elemento in mes]
    
    try:
        status_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'status')])
        status = odoo.env['google.drive.config'].read(status_id)[0]['valor']
    except Exception as e:
        return devolver_datos_error(e)
    status = status.strip()
    
    control_whatsapp_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'mensajes_whatsapp')])
    control_whatsapp = odoo.env['google.drive.config'].read(control_whatsapp_id)[0]['valor'].strip()
    
    pathgdrive_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-gdrive')])
    pathgdrive = odoo.env['google.drive.config'].read(pathgdrive_id)[0]['valor']
    pathglocal_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', 'root-local')])
    pathglocal = odoo.env['google.drive.config'].read(pathglocal_id)[0]['valor']

#     print(f"consultar_configuracion")
    return hojas, mes, status, control_whatsapp, pathgdrive, pathglocal, id_mb
# Funciones de envío
def validar_numero_movil(numero):
    # Expresión regular para validar un número de teléfono móvil
    patron = r'^\+\d{1,3}\d{8,14}$'

    # Verificar si el número coincide con el patrón
    if re.match(patron, numero):
        return True
    else:
        return False
    
def enviar_mensaje_whatsapp(phone_number, message):
#     print(f"entro a enviar_mensaje_whatsapp: phone_number: {phone_number} message: {message}")
    # Ubicación por defecto
#     x = 1333
    x = 1318
    y = 698
    # Abrir WhatsApp Web (asegúrate de tenerlo abierto previamente)
    try:
        if validar_numero_movil(phone_number):
            result = pywhatkit.sendwhatmsg_instantly(phone_number, message, 20, tab_close=False)

            try:
                enviar_button_location = pyautogui.locateCenterOnScreen('send_button.png')
#                 print(f"enviar_button_location: {enviar_button_location}")
#                 print(f"Tipo enviar_button_location: {type(enviar_button_location)}")
        #         print("Cambiando valores por defecto")
                x = enviar_button_location.x
                y = enviar_button_location.y
            except:
#                 print(f"Ubicación manual: ({x}, {y})")
                try:
                    enviar_button_location = pyautogui.locateCenterOnScreen('send_button_2.png')
                except:
                    enviar_button_location = (x, y)

            if enviar_button_location:
                # Haz clic en las coordenadas encontradas
                pyautogui.click(enviar_button_location)
                time.sleep(10)

                pyautogui.hotkey('ctrl', 'w') # Cierra la ventana del navegador crhome
                return "enviado"

            else:
#                 print("No se encontró el botón de enviar. Falló la ubicación manual")
                return "Fallo ubicación"
        else:
            return f"Fallo número de Móvil: {phone_number}"
    except Exception as e:
        return f"Fallo: {e}"
    
def actualizar_configuracion(odoo, id_mb, key, value):
    try:
        status_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', key)])
        odoo.env['google.drive.config'].browse(status_id).write({'valor': value})
        return True
    except Exception as e:
        return False

def consultar_estado(odoo, id_mb, key):
    try:
        status_id = odoo.env['google.drive.config'].search([('cliente_id', '=', id_mb), ('clave', '=', key)])
        status = odoo.env['google.drive.config'].read(status_id)[0]['valor']
        status = status.strip().lower()
        return status
    except Exception as e:
        status = 'Error de conexión'


def correccion_mensaje(mensaje):
    hora_actual = datetime.datetime.now().hour
    
    # Definir las frases a reemplazar
    frase_manana = "Buenos días"
    frase_tarde = "Buenas tardes"
    frase_tarde2 = "Buenas tardesBuenas tardes"
    frase_noche = "Buenas noches"
    frase_manana2 = "Buenos díasBuenos días"
    mensaje = mensaje.replace(frase_manana2, frase_manana)
    mensaje = mensaje.replace(frase_tarde2, frase_tarde)

    # Ajustar el mensaje según la hora actual
    if 6 <= hora_actual < 12:
        mensaje = mensaje.replace(frase_tarde, frase_manana)
        mensaje = mensaje.replace(frase_noche, frase_manana)
    elif 12 <= hora_actual < 18:
        mensaje = mensaje.replace(frase_manana, frase_tarde)
        mensaje = mensaje.replace(frase_noche, frase_tarde)
    else:
        mensaje = mensaje.replace(frase_manana, frase_noche)
        mensaje = mensaje.replace(frase_tarde, frase_noche)

    return mensaje

# Función para verificar si la hora actual es una de las horas deseadas
def es_hora_deseada(horas_deseadas, solo_hora=False):
    hora_actual = datetime.datetime.now()
    for hora_deseada in horas_deseadas:
        if solo_hora and hora_actual.hour == hora_deseada[0]:
            return True
        if hora_actual.hour == hora_deseada[0] and hora_actual.minute == hora_deseada[1]:
            return True
    return False

def hora_habil():
    # Obtener la hora actual y el día de la semana actual
    hora_actual = datetime.datetime.now().hour
    dia_semana_actual = datetime.datetime.now().weekday()

    # Verificar si es un día laborable (lunes=0, martes=1, ..., viernes=4)
    if 0 <= dia_semana_actual <=4:
        # Verificar si la hora está entre las 8am y las 12am o entre las 2pm y las 6pm
        if (8 <= hora_actual < 13) or (13 <= hora_actual < 18):
            return True

    return False

def actualizar_estados(odoo, lista_actualizacion):  
    total_registros = len(lista_actualizacion)
    contador = 0
    for registro in lista_actualizacion:
        id_registro = registro['id']
        id_poliza = registro['id_poliza']
#         nuevo_estado = 'enviado'  # Aquí debes definir el nuevo estado que deseas asignar
        nuevo_estado = registro['whatsapp_status']
        hora = registro['hora']
        # Actualizar el registro en Odoo: 
        odoo.env['mb_asesores.vencimientos'].browse(id_registro).write({'whatsapp_status': nuevo_estado, 'hora_ws': hora})
        contador += 1
        print(f"Registro actualizado en odoo: id_registro {id_registro} id_poliza: {id_poliza}")
        print(f"Actualizando {contador}/{total_registros}")
    return True

# Envío de mensajes - Debe quedar en una función
def envio_global(mes, ramo, hora_limite, df_filtered):
    if not hora_habil():
        mensaje = f'No es una horario hábil para el envío de mensajes'
        estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
        return []
    total = len(df_filtered)
    contador = 0
    mensajes_enviados = []
    for index, row in df_filtered.iterrows():
        phone_number = str(row['CELULAR'])
#         phone_number = '3004229309'
        movil_lista = phone_number.replace(';', ',').split(',')
        for movil in movil_lista:
            phone_number = '+57' + movil.strip()
            mensaje = row['MENSAJE']
            if mensaje and row['URL']:
                mensaje = correccion_mensaje(mensaje) +'\n\n' + 'Adjunto: ' + row['URL']
                status = consultar_estado(odoo, id_mb, 'status')
                if (status == 'waiting' or status == 'esperando' or status == 'enviar whatsapp') or (status == 'sending' or status == 'enviando'):
                    estado = enviar_mensaje_whatsapp(phone_number, mensaje)
                    poliza = row['POLIZA']
                    row = buscar_fila(mes, poliza, df_sheets)
                    columnname = buscando_columna('CONTROL', df_sheets)
                    update_cell(sheet, row, columnname, estado)
                    columnname = buscando_columna('ESTADO WHATSAPP', df_sheets)
                    update_cell(sheet, row, columnname, estado)
#                     columnname = buscando_columna('HORA WHATSAPP', df_sheets)
#                     update_cell(sheet, row, columnname, datetime.datetime.now())
#                     if estado == 'enviado':
#                         mensajes_enviados.append({'id': row['ID'], 'id_poliza': row['POLIZA'], 'whatsapp_status': estado, 'hora': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        contador += 1
        print(f"Enviados {contador}/{total} movil {phone_number}")
        if es_hora_deseada(hora_limite):
            mensaje = f'Se termina la ejecución por temas de horas'
            estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
            break

    actualizar_estados(odoo, mensajes_enviados)
    return mensajes_enviados

odoo = odoo_conect()
creds, gc, servicio_drive = autenticar_google_drive()
# ##############################
# Ejecución
##############################
horas_deseadas = [(8, 0), (12, 15)]
hora_limite = [(18, 0)]
hora_fin = [(18, 0)]
hora_inicio = [(8, 0)]


# Ciclo while para verificar la hora actual y ejecutar una acción si es una de las horas deseadas
print("Iniciando...")
while True:
    try:
        status = consultar_estado(odoo, id_mb, 'status')
        if status == 'Error de conexión':
            print("Intentando nueva conexión...")
            odoo = odoo_conect()
        hojas, meses, status, control_whatsapp, pathgdrive, pathglocal, id_mb = consultar_configuracion(odoo)
        control_whatsapp = consultar_estado(odoo, id_mb, 'mensajes_whatsapp')
        print(f"status:{status}  control_whatsapp:{control_whatsapp} - {datetime.datetime.now()}")
    #     if not es_hora_deseada(hora_limite, True) and status == 'waiting':
        if hora_habil() and (status == 'waiting' or 
                               status == 'esperando' or 
                               status == 'enviando whatsapp' or 
                               status == 'enviar whatsapp'):
            if control_whatsapp != 'no':
                actualizar_configuracion(odoo, id_mb, 'status', 'enviando whatsapp')
                mensaje = f'Arrancando y calentando WS'
                print(mensaje)
                estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
                time.sleep(30)  # Espera 300 segundos para que se actualice WS
                for mes in meses:
                    if hojas != [''] and hojas:
                        for hoja in hojas:
                                mensaje = f'Arrancando proceso mes: {mes} ramo: {hoja}'
                                print(mensaje)
                                estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
                                df_sheets, sheet, sheet_df_dict, lista_archivos = cargar_hoja(hoja, servicio_drive, gc, pathgdrive, mes)
                                df_filtrado = df_sheets[(df_sheets['MES'].str.upper() == mes) & (df_sheets['CONTROL'].str.lower() == 'pendiente enviar whatsapp')]
                                mensajes_enviados = envio_global(mes, hoja, hora_limite, df_filtrado)
                                mensaje = 'Envío finalizado finalizado. \nActualizando Sheet'
                                print(mensaje)
                                estado = enviar_mensaje_whatsapp('+573004229309', mensaje)

    #                             actualizar_configuracion(odoo, id_mb, 'status', 'actualizando')
    #                             actualizar_sheet_vencimientos(month=mes, year=None, hojas=hojas)

                                mensaje = 'Actualización sheet terminada'
                                print(mensaje)
                                estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
                    else:
                        mensaje = f'Proceso terminado porque no vino ninguna hoja para analizar {datetime.datetime.now()}'
                        print(mensaje)
                        estado = enviar_mensaje_whatsapp('+573004229309', mensaje)

                mensaje = f'Proceso terminado para la hora {datetime.datetime.now()}'
                print(mensaje)
                estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
                actualizar_configuracion(odoo, id_mb, 'status', 'inactivo')
            else:
                mensaje = f'No esta habilitado el envío'
                print(mensaje)

        else:
            pyautogui.moveRel(10, 0, duration=0.5)  # Mueve el mouse a la derecha
            pyautogui.moveRel(-10, 0, duration=0.5)  # Mueve el mouse a la izquierda
            time.sleep(15)
            if es_hora_deseada(hora_inicio):
#                 mensaje = f'Iniciando el día {datetime.datetime.now()}'
#                 estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
#                 print(mensaje)
#             if es_hora_deseada(hora_fin):
#                 mensaje = f'Proceso terminado para la hora {datetime.datetime.now()}'
#                 print(mensaje)
#                 estado = enviar_mensaje_whatsapp('+573004229309', mensaje)
#                 break
    except ValueError:
        print(ValueError)