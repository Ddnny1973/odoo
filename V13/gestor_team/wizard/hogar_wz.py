import logging
import pandas as pd

from odoo.exceptions import ValidationError
from datetime import datetime

from odoo import models
import shutil
import os
# from os import listdir

_logger = logging.getLogger(__name__)


class SubirArchivoClaroWizard(models.TransientModel):
    _name = "gestor.carga.hogares.wizard"
    _description = "Subir archivo Hohares Claro Wizard"

    def action_ok(self):
        """
            Buscando la ruta de archivos de la Base de datos
            Se deben crear los parámetros del sistema con la ruta de archivos dentro del docker,
            la ruta debe estar mapeada al sistema operativo y debe ser común entre odoo y postgresql
        """
        ruta_bd = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_bd')]).value or '/var/lib/postgresql/data/compartida/rp/'
        ruta_odoo = self.env['ir.config_parameter'].search([('key', '=', 'gestor_hogares_claro_ruta_odoo')]).value or '/mnt/compartida/rp/'
        ruta_pendientes = 'pendientes/'
        ruta_procesado = 'procesados/'
        archivo = 'HOGARES.txt'
        nombre_archivo = ruta_bd + archivo

        # Análisis de archivo
        # datos_df = pd.read_csv(nombre_archivo, sep=';')  # index_col=0
        # Número de filas
        # raise ValidationError(len(datos_df.index))
        # Número de columnas
        # columnas = datos_df.columns
        # raise ValidationError(len(columnas))

        # Procesando el archivo en la Base de datos
        table_name = 'gestor_hogares_claro'
        self.env.cr.execute("""select load_hogares_csv_file(
                               %s, %s, %s);""",
                            (table_name, nombre_archivo, self.env.user.id))

        # Procesando el archivo ruta pendientes --> Procesados
        fecha = datetime.now()
        filename = "HOGARES-{}.txt".format(fecha.strftime("%Y-%m-%d-%H%M%S"))
        nombre_archivo_pendiente = ruta_odoo + ruta_pendientes + archivo
        nombre_archivo_procesado = ruta_odoo + ruta_procesado + filename
        if os.path.exists(nombre_archivo_pendiente):
            with open(nombre_archivo_pendiente, 'rb') as forigen:
                with open(nombre_archivo_procesado, 'wb') as fdestino:
                    shutil.copyfileobj(forigen, fdestino)
                    os.remove(nombre_archivo_pendiente)
