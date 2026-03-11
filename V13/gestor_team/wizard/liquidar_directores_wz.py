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


class LiquidarDirectoresWizard(models.TransientModel):
    _name = "gestor.liquidar.directores.wizard"
    _description = "Liquidar Directores"

    fecha_inicio = fields.Date('Fecha inicial', help='Fecha de inicio para el cierre')
    fecha_fin = fields.Date('Fecha final', help='Fecha final para el cierre')

    def action_liquidar(self):
        if self.fecha_inicio and self.fecha_fin:
            # La función f_liquidacion_padres_hogar_2 usa array para buscar el valor de la comisión y el esquema, esto reduce los cálculos
            # pues solo hace la búsqueda una sola vez y devuelve tanto el valor como el esquema ID.
            # La función f_liquidacion_padres_hogar usa el método tradicional que busca el valor y luego repite la consulta para buscar el esquema ID
            # sql = """
            #         select f_liquidacion_padres_hogar_2({0}, {1}, '{2}', '{3}')
            #       """.format(0, 0, self.fecha_inicial, self.fecha_final)
            # self.env.cr.execute(sql)

            self._cr.execute("""
                                select f_liquidacion_padres_hogar_2_repositorio(0, 0, %s, %s)
                             """, (self.fecha_inicio, self.fecha_fin)
                             )

            # empleados_ids = self.env['hr.employee'].search([])

    def responsables_historicos_x_orden(self):
        self._cr.execute("""
                            truncate table v_ventas_recursivas_para_conteo;
                            select responsables_historicos_x_orden();
                            """
                        )
