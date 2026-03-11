import logging
# import psycopg2
# import pymssql

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


class CerrarMesWizard(models.TransientModel):
    _name = "gestor.cerrar.mes.wizard"
    _description = "Cerrar ventas mes"

    fecha_inicio = fields.Date('Fecha inicial', help='Fecha de inicio para el cierre')
    fecha_fin = fields.Date('Fecha final', help='Fecha final para el cierre')

    def action_cerrar_mes(self):
        # Actualizando período de consulta por usuario
        captura_new = []
        sql = """
                select cuenta, ot
                    from gestor_hogar_team
                    where (cuenta, ot) not in (select cuenta, ot from gestor_captura_hogar_team)
                    and fecha between '{0}' and '{1}'
                    group by cuenta, ot
              """.format(self.fecha_inicio, self.fecha_fin)
        self.env.cr.execute(sql)  #Execute SQL statement
        hogar_ids = self.env.cr.dictfetchall()
        # hogar_team_ids = self.env['gestor.hogar.team'].search([('fecha', '<=', self.fecha_fin)])
        for reg in hogar_ids:
            captura_new = []
            captura_new.append({'ot': reg['ot'],
                                'cuenta': reg['cuenta'],
                                'id_cliente': '999999999',
                                'nombre_cliente': 'Creado por el sistema',
                                'tel_cliente': '00000',
                                'id_asesor': 6769,
                                'vendedor': 484,
                                'active': False,
                                 })
            # raise ValidationError(referido_new)
        # raise ValidationError(captura_new)
            self.env['gestor.captura.hogar.team'].create(captura_new)
