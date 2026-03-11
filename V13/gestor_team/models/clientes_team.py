import logging
from odoo import models, fields, api
from datetime import datetime, timedelta

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ClientesTeam(models.Model):
    _name = 'gestor.clientes.team'
    _description = 'Clientes Team'

    name = fields.Char('Nombre', required=True, index=True)
    tipo_identificacion = fields.Selection([('cc', 'CC'), ('nit', 'NIT')], default='cc')
    identificacion = fields.Char('Idetificacion', required=True, index=True)
    dv = fields.Char('N. Verificación')

    _sql_constraints = [('unq_clientes_team_identificacion', 'UNIQUE (identificacion)',
                         'El Estado ya existe ya existe!')]

    def _get_clientes(self):
        self.env.cr.execute("""insert into gestor_clientes_team (name, tipo_identificacion, identificacion, dv)
                               select nombre_cliente, 'cc', id_cliente, null from gestor_captura_hogar_team
                               on conflict (identificacion) do nothing""")
        self.env.cr.commit()
