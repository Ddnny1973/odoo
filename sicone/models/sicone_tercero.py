# -*- coding: utf-8 -*-
"""
MÓDULO: Unificación de Terceros
================================
Gestiona nombres canónicos y aliases de terceros (proveedores, contratistas)
para normalizar variaciones de nombre en el libro auxiliar.

Ejemplos de variaciones reales encontradas:
  ELKIN YOVANY VALLEJO TORO  ←→  ELKIN YOVANNY VALLEJO
  ALBERTO GARCIA FERGUSSON   ←→  ALBERTO JOSE GARCIA FERGUSSON

FLUJO:
1. Wizard de detección escanea movimientos y detecta similitudes
2. Usuario confirma/rechaza qué nombres son el mismo tercero
3. Se crea registro canónico + aliases
4. El wizard del libro auxiliar normaliza al importar
"""
from difflib import SequenceMatcher
from odoo import models, fields, api
from odoo.exceptions import UserError


class SiconeTercero(models.Model):
    _name = 'sicone.tercero'
    _description = 'Tercero Unificado (Nombre Canónico + Aliases)'
    _order = 'nombre_canonico'

    nombre_canonico = fields.Char(
        string='Nombre Canónico',
        required=True,
        help='Nombre oficial que se usará en todos los reportes y análisis'
    )
    identificacion = fields.Char(
        string='Identificación (NIT/CC)',
        help='NIT o cédula del tercero — referencia adicional de verificación'
    )
    aliases = fields.Text(
        string='Aliases',
        help='Nombres alternativos separados por coma. Ej: ELKIN YOVANNY VALLEJO, E. VALLEJO TORO'
    )
    categoria = fields.Selection([
        ('proveedor',    'Proveedor de materiales'),
        ('contratista',  'Contratista / Mano de obra'),
        ('empleado',     'Empleado'),
        ('cliente',      'Cliente'),
        ('entidad',      'Entidad (DIAN, EPS, etc.)'),
        ('otro',         'Otro'),
    ], string='Categoría', default='contratista')
    activo = fields.Boolean(default=True)
    total_movimientos = fields.Integer(
        string='Movimientos',
        compute='_compute_movimientos',
        store=False
    )
    notas = fields.Text(string='Notas')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('nombre_canonico_unique', 'UNIQUE(nombre_canonico, company_id)',
         'Ya existe un tercero con ese nombre canónico.'),
    ]

    @api.depends('nombre_canonico')
    def _compute_movimientos(self):
        for rec in self:
            nombres = rec._get_todos_nombres()
            count = self.env['sicone.movimiento.contable'].search_count([
                ('nombre_tercero', 'in', nombres)
            ])
            rec.total_movimientos = count

    def _get_todos_nombres(self):
        """Retorna lista con nombre canónico + todos los aliases"""
        nombres = [self.nombre_canonico]
        if self.aliases:
            nombres += [a.strip() for a in self.aliases.split(',') if a.strip()]
        return nombres

    def action_agregar_alias(self):
        """Abre wizard para agregar alias manualmente"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agregar Alias',
            'res_model': 'sicone.wizard.alias',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_tercero_id': self.id},
        }

    @api.model
    def normalizar_nombre(self, nombre_raw):
        """
        Normaliza un nombre de tercero contra la tabla canónica.
        Retorna (nombre_normalizado, confianza)
        confianza: 100=exacto, 80-99=auto, 70-79=revisar, 0=sin match
        """
        if not nombre_raw:
            return nombre_raw, 0

        nombre_limpio = nombre_raw.strip().upper()
        terceros = self.search([('activo', '=', True)])

        # 1. Match exacto
        for t in terceros:
            for alias in t._get_todos_nombres():
                if nombre_limpio == alias.strip().upper():
                    return t.nombre_canonico, 100

        # 2. Fuzzy matching
        mejor_tercero = None
        mejor_score = 0
        for t in terceros:
            for alias in t._get_todos_nombres():
                score = SequenceMatcher(
                    None, nombre_limpio, alias.strip().upper()
                ).ratio() * 100
                if score > mejor_score:
                    mejor_score = score
                    mejor_tercero = t

        if mejor_score >= 80 and mejor_tercero:
            return mejor_tercero.nombre_canonico, round(mejor_score)
        elif mejor_score >= 70 and mejor_tercero:
            return nombre_raw, round(mejor_score)  # retorna original, requiere revisión
        return nombre_raw, 0
