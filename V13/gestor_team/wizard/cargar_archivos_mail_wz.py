import logging
# import psycopg2
# import pymssql
import os
import shutil
import pandas as pd
import hashlib
# import shutil
# import datetime
# import csv
# import openpyxl as xl

from odoo.exceptions import ValidationError
from odoo import fields, models
from datetime import datetime
from datetime import timedelta
from pytz import utc, timezone
# from itertools import islice

_logger = logging.getLogger(__name__)


class CargarArchivosWizard(models.TransientModel):
    _name = "gestor.cargar.archivos.mail.wizard"
    _description = "Cargar archivos mail CRM"

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

    def _compute_lista_archivos(self):
        archivos_load = []
        total_archivos = 0
        ruta_odoo = '/mnt/compartida/rp/pendientes'
        for archivo in os.listdir(ruta_odoo):
            archivos_load.append(archivo)
        return archivos_load

    def action_cargar_archivos(self):
        # Rutas
        # tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc

        ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'path_files')]).value or '/var/lib/odoo/filestore/TEAM/'
        ruta_pendientes = ruta_odoo + 'pendientes/'

        # ruta_bd = '/var/lib/postgresql/data/compartida/rp/pendientes/'
        ruta_files_odoo = '/mnt/compartida/rp/pendientes/'

        # Buscando eventos
        eventos = self.env['crm.lead'].search([('stage_id', 'in', (5, 1))])   # Estado New
        # Creando lista de archivos a procesar
        archivos = []
        exluir_archivos = ['image/jpeg', 'image/png', 'application/pdf', 'message/rfc822', 'application/rar', 'image/gif']
        for evento in eventos:
            archivos = self.env['ir.attachment'].search([('res_model', '=', 'crm.lead'), ('res_id', '=', evento.id), ('mimetype', 'not in', exluir_archivos)])
            for i in self.env['ir.attachment'].search([('res_model', '=', 'crm.lead'), ('res_id', '=', evento.id), ('mimetype', 'not in', exluir_archivos)]):
                nombre_archivo = ruta_odoo + i.store_fname
                nombre_archivo_new = ruta_files_odoo + i.name
                hash = self.getmd5file(nombre_archivo)

                archivo_procesado = self.env['gestor.log.carga.archivos'].search([('hash', '=', hash)])
                if not archivo_procesado:
                    hash = self.getmd5file(nombre_archivo)
                    # raise ValidationError('Hash: ' + hash)

                    # try:
                    # os.rename(nombre_archivo, nombre_archivo_new)
                    # raise ValidationError('Nombre archivo: ' + nombre_archivo + '\nNombre nuevo: ' + nombre_archivo_new)
                    if nombre_archivo_new not in self._compute_lista_archivos():
                        try:
                            shutil.copy(nombre_archivo, nombre_archivo_new)
                        except:
                            _logger.info('Archivo con problemas: ' + nombre_archivo_new)
                            # raise ValidationError('Error con el archivo: ' + nombre_archivo_new)
                        
                        # shutil.copytree(nombre_archivo, nombre_archivo_new, ignore=ignore)
                    # archivos.append((nombre_archivo_new, nombre_archivo))
                    evento.stage_id = 5
                else:
                    _logger.info('Archivo ya procesado: ' + nombre_archivo_new + '\nHASH: ' + hash)
                    # raise ValidationError('Archivo ya procesado: ' + nombre_archivo_new + '\nHASH: ' + hash)
        # raise ValidationError(errores)
