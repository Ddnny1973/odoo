from odoo import fields, models
import hashlib


class GestionArchivos(models.Model):
    _name = 'gestor.archivos.team'
    _description = 'Gestión de tipos de archivo'

    name = fields.Char('Nombre archivo', help='Tipo de archivo a procesar, ej. REPOS.TXT, Rony.csv \nNo importa la extensión del archvio, solo se debe ingresar su estructura.')
    modelo_id = fields.Many2one('ir.model', domain=[('model', 'like', 'gestor%')])
    columnas_ids = fields.One2many('gestor.archivos.columnas.team', 'column_id', ondelete='cascade')
    query = fields.Text('Query', help='Consulta definida para el cruce')


class GestionArchivosColumnas(models.Model):
    _name = 'gestor.archivos.columnas.team'
    _order = "secuencia"
    _description = 'Relación entre columnas y modelo para la importación de información'

    column_id = fields.Many2one('gestor.archivos.team', ondelete='cascade')
    secuencia = fields.Integer('Orden', help='Orden de la columna en el archivo, este orden es fundamental para la importación.')
    columna_archivo = fields.Char('Columna', help='Nombre de la columna en el archivo')
    columna_modelo = fields.Char(string='Columna Modelo',
                                 help='Campo del modelo donde reposará la información')
    columna_key = fields.Boolean('Key', help='Columna a usar en el cruce entre con TIPS')
    """
    columna_modelo = fields.Many2one('ir.model.fields',
                                     domain=[('model_id', '='s, 448)],
                                     string='Columna Modelo',
                                     help='Campo del modelo donde reposará la información')
                                     """


class LogCargaArchivos(models.Model):
    _name = 'gestor.log.carga.archivos'
    _description = 'Log de Carga de archivos'
    _order = 'fecha desc'

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

    name = fields.Char('Archivo')
    registros = fields.Integer('Registros', help='Registros a procesar')
    estado = fields.Char('Estado', help='Estado de la importación')
    fecha = fields.Datetime('Fecha de la importación')
    duracion = fields.Datetime('Duración de la importación')
    hash = fields.Char('HASH', help='Validación HASH del archivo')
    inicio = fields.Datetime('Inicio de la operación')
    fin = fields.Datetime('Fin de la operación')
    mecanismo = fields.Char('Mecanismo', help='Define si el proceso se hizo por SQL o por Python')
    observaciones = fields.Char('Observaciones')
