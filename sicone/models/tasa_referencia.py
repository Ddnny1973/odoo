# -*- coding: utf-8 -*-
"""
MÓDULO: Tasas de Referencia para Inversiones Temporales
========================================================
Almacena las tasas de referencia del mercado colombiano que el
administrador actualiza periódicamente (típicamente cada trimestre
o cuando el Banco de la República modifica la tasa de política).

Las tasas son usadas por el módulo de Inversiones Temporales para:
  - Mostrar contexto de mercado al registrar una inversión
  - Comparar la tasa pactada vs el rango orientativo del instrumento
  - Mostrar IBR y DTF actuales como referencia

FUENTE: Portal de Estadísticas Económicas del Banco de la República
  https://suameca.banrep.gov.co/estadisticas-economicas/
  Sección: IBR → Indicador Bancario de Referencia

SINGLETON: Solo existe un registro activo por compañía.
  Usar action_abrir_tasas() para garantizar apertura del singleton.
"""

from odoo import models, fields, api
from datetime import date


class TasaReferencia(models.Model):
    """
    Configuración de tasas de referencia del mercado financiero colombiano.
    Singleton por compañía — el administrador actualiza los valores
    cuando el Banco de la República modifica su postura monetaria.
    """
    _name = 'sicone.tasa.referencia'
    _description = 'Tasas de Referencia — Inversiones SICONE'

    name = fields.Char(
        string='Nombre', default='Tasas de Referencia', required=True
    )
    active = fields.Boolean(default=True)

    # ── Tasas de referencia Banrep ─────────────────────────────────────────
    ibr_overnight_ea = fields.Float(
        string='IBR Overnight EA (%)', digits=(5, 3),
        default=10.68,
        help='IBR overnight en tasa efectiva anual. '
             'Fuente: suameca.banrep.gov.co → Estadísticas → IBR'
    )
    dtf_ea = fields.Float(
        string='DTF EA (%)', digits=(5, 3),
        default=11.13,
        help='DTF efectivo anual. Estimado: IBR + 0.45% (relación histórica). '
             'Verificar en: superfinanciera.gov.co'
    )
    tasa_politica_monetaria = fields.Float(
        string='Tasa de Política Monetaria (%)', digits=(5, 2),
        default=11.25,
        help='Tasa de intervención del Banco de la República. '
             'Fuente: banrep.gov.co'
    )
    fecha_actualizacion = fields.Date(
        string='Fecha de Actualización',
        default=fields.Date.today,
        help='Fecha en que se actualizaron las tasas manualmente.'
    )
    notas = fields.Text(
        string='Notas',
        help='Contexto de la actualización: decisión de política monetaria, '
             'expectativas, fuente consultada, etc.'
    )

    # ── Rangos orientativos por instrumento (EA%) ──────────────────────────
    # CDT
    cdt_tasa_min = fields.Float(
        string='CDT — Tasa Mín (%)', digits=(5, 2), default=13.0
    )
    cdt_tasa_max = fields.Float(
        string='CDT — Tasa Máx (%)', digits=(5, 2), default=15.0
    )

    # Fondo de Liquidez
    fondo_liq_tasa_min = fields.Float(
        string='Fondo Liquidez — Tasa Mín (%)', digits=(5, 2), default=10.0
    )
    fondo_liq_tasa_max = fields.Float(
        string='Fondo Liquidez — Tasa Máx (%)', digits=(5, 2), default=11.0
    )

    # Fondo Corto Plazo
    fondo_cp_tasa_min = fields.Float(
        string='Fondo Corto Plazo — Tasa Mín (%)', digits=(5, 2), default=11.0
    )
    fondo_cp_tasa_max = fields.Float(
        string='Fondo Corto Plazo — Tasa Máx (%)', digits=(5, 2), default=13.0
    )

    # Cuenta Remunerada
    cuenta_rem_tasa_min = fields.Float(
        string='Cuenta Remunerada — Tasa Mín (%)', digits=(5, 2), default=3.0
    )
    cuenta_rem_tasa_max = fields.Float(
        string='Cuenta Remunerada — Tasa Máx (%)', digits=(5, 2), default=6.0
    )

    # ── Compañía ───────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True
    )

    # ==========================================================================
    # MÉTODOS
    # ==========================================================================

    def get_rango_instrumento(self, instrumento):
        """
        Retorna (tasa_min, tasa_max) para el instrumento dado.
        Usado por InversionTemporal.action_consultar_tasas().
        """
        self.ensure_one()
        mapa = {
            'cdt':               (self.cdt_tasa_min,       self.cdt_tasa_max),
            'fondo_liquidez':    (self.fondo_liq_tasa_min,  self.fondo_liq_tasa_max),
            'fondo_corto_plazo': (self.fondo_cp_tasa_min,   self.fondo_cp_tasa_max),
            'cuenta_remunerada': (self.cuenta_rem_tasa_min, self.cuenta_rem_tasa_max),
        }
        return mapa.get(instrumento, (0.0, 0.0))

    @api.model
    def get_tasas_activas(self):
        """
        Obtiene el registro de tasas activo para la compañía actual.
        Si no existe, lo crea con los valores por defecto.
        """
        tasas = self.search(
            [('active', '=', True), ('company_id', '=', self.env.company.id)],
            order='id asc', limit=1
        )
        if not tasas:
            tasas = self.create({
                'name': 'Tasas de Referencia',
                'company_id': self.env.company.id,
            })
        return tasas

    @api.model
    def action_abrir_tasas(self):
        """Abre siempre el singleton de tasas — nunca crea duplicados."""
        tasas = self.get_tasas_activas()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.tasa.referencia',
            'res_id': tasas.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'mode': 'edit'},
        }
