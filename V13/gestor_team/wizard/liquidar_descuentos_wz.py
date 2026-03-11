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


class LiquidarDescuentosWizard(models.TransientModel):
    _name = "gestor.liquidar.descuentos.wizard"
    _description = "Liquidar Descuentos"

    fecha_inicio = fields.Date('Fecha inicial', help='Fecha de inicio para el cierre')
    fecha_fin = fields.Date('Fecha final', help='Fecha final para el cierre')
    sw_comision_ventas = fields.Boolean('Comisión Ventas', help='Incluir en descuentos', default=True)
    sw_comision_responsable = fields.Boolean('Comisión Responsable', help='Incluir en descuentos', default=True)
    sw_comision_incentivo = fields.Boolean('Comisión Incentivo', help='Incluir en descuentos', default=True)
    empleados_ids = fields.One2many('hr.employee', 'liquidacion_descuentos_wz_id',
                                    string='Empleados',
                                    domain=['|', ('active', '=', True), ('active', '=', False)])

    def action_liquidar_descuentos(self):
        if self.fecha_inicio and self.fecha_fin:
            # La función f_liquidacion_padres_hogar_2 usa array para buscar el valor de la comisión y el esquema, esto reduce los cálculos
            # pues solo hace la búsqueda una sola vez y devuelve tanto el valor como el esquema ID.
            # La función f_liquidacion_padres_hogar usa el método tradicional que busca el valor y luego repite la consulta para buscar el esquema ID
            # sql = """
            #         select f_liquidacion_padres_hogar_2({0}, {1}, '{2}', '{3}')
            #       """.format(0, 0, self.fecha_inicial, self.fecha_final)
            # self.env.cr.execute(sql)           

            self._cr.execute("""
                                select f_descuentos_2(%s, %s, %s, 0, %s, %s, %s);
                             """,
                             (self.empleados_ids.ids,
                              self.fecha_inicio,
                              self.fecha_fin,
                              self.sw_comision_ventas,
                              self.sw_comision_responsable,
                              self.sw_comision_incentivo)
                             )
            # self.env.cr.commit()
