# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NewCity(models.Model):
    _inherit = 'l10n_co_cities.city'

    zona_id = fields.Many2one('gestor.zonas')


class Poblaciones(models.Model):
    _name = 'gestor.poblaciones.team'
    _description = 'Poblaciones manejadas por TEAM'

    name = fields.Char('Población', required=True, index=True)

    _sql_constraints = [
                            ('gestor.poblaciones.team_name_uniq', 'unique (name)', "La población ya existe!"),
                        ]

    def cargar_poblaciones(self):
        self._cr.execute("""
                            insert into gestor_poblaciones_team
                            (name, create_date, create_uid )
                            SELECT distinct(poblacion) poblacion, current_timestamp, %s
                            from gestor_captura_hogar_team
                            where poblacion is not null
                            on conflict do nothing;
                        """, (self.env.user.id,)
                        )