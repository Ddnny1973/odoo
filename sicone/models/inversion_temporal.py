# -*- coding: utf-8 -*-
"""
MÓDULO: Inversiones Temporales
==============================
Gestiona el análisis, registro y seguimiento de inversiones de excedentes
de liquidez de SICONE SAS.

INSTRUMENTOS SOPORTADOS:
  - CDT:                Sin comisión, plazo mínimo 30 días, baja liquidez
  - Fondo de Liquidez:  Comisión 0.5% anual, liquidez alta, min 30 días
  - Fondo Corto Plazo:  Comisión 0.8% anual, liquidez media-alta, min 30 días
  - Cuenta Remunerada:  Sin comisión, liquidez inmediata, tasa baja

DESCUENTOS APLICADOS (legislación colombiana):
  - Retención en la Fuente: 7% sobre rendimientos financieros
  - GMF (4×1000):           0.4% sobre capital + rendimientos al retirar
                             y 0.4% adicional al momento de invertir
  - Comisión de gestión:    Según instrumento, proporcional al plazo

CONTEXTO DE LIQUIDEZ:
  El módulo lee el excedente invertible del Dashboard Consolidado
  (sicone.config.empresa.cf_excedente) y descuenta el monto de todas
  las inversiones activas para mostrar el disponible real restante.

TASAS EN VIVO:
  Se consulta el IBR overnight desde datos.gov.co (API Socrata).
  El DTF se estima como IBR + 0.45% (relación histórica estable).
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


# ==============================================================================
# CONSTANTES TRIBUTARIAS Y DE MERCADO
# ==============================================================================

GMF = 0.004
RETENCION = 0.07

COMISIONES = {
    'cdt':               0.0,
    'fondo_liquidez':    0.5,
    'fondo_corto_plazo': 0.8,
    'cuenta_remunerada': 0.0,
}

PLAZOS_MINIMOS = {
    'cdt':               30,
    'fondo_liquidez':    30,
    'fondo_corto_plazo': 30,
    'cuenta_remunerada':  1,
}

TASAS_ORIENTATIVAS = {
    'cdt':               (13.0, 15.0),
    'fondo_liquidez':    (10.0, 11.0),
    'fondo_corto_plazo': (11.0, 13.0),
    'cuenta_remunerada':  (3.0,  6.0),
}


# ==============================================================================
# MODELO PRINCIPAL
# ==============================================================================

class InversionTemporal(models.Model):
    _name = 'sicone.inversion.temporal'
    _description = 'Inversión Temporal de Excedentes SICONE'
    _order = 'fecha_inicio desc, id desc'

    # ── Identificación ─────────────────────────────────────────────────────
    nombre = fields.Char(string='Nombre / Referencia', required=True)
    instrumento = fields.Selection([
        ('cdt',               'CDT'),
        ('fondo_liquidez',    'Fondo de Liquidez'),
        ('fondo_corto_plazo', 'Fondo Corto Plazo'),
        ('cuenta_remunerada', 'Cuenta Remunerada'),
    ], string='Instrumento', required=True, default='cdt')
    entidad = fields.Char(string='Entidad Financiera')
    estado = fields.Selection([
        ('activa',    'Activa'),
        ('vencida',   'Vencida'),
        ('cancelada', 'Cancelada'),
    ], string='Estado', default='activa', required=True)

    # ── Parámetros de inversión ────────────────────────────────────────────
    monto = fields.Monetary(
        string='Monto a Invertir', currency_field='currency_id', required=True,
        help='Capital inicial a invertir (antes de GMF de entrada)'
    )
    plazo_dias = fields.Integer(string='Plazo (días)', default=90)
    tasa_ea = fields.Float(string='Tasa EA (%)', digits=(6, 2))
    fecha_inicio = fields.Date(string='Fecha de Inicio', default=fields.Date.today, required=True)
    observaciones = fields.Text(string='Observaciones')

    # ── Tasas de referencia (consultadas desde Banrep) ─────────────────────
    ibr_actual = fields.Float(string='IBR EA (%)', digits=(5, 2), readonly=True)
    dtf_actual = fields.Float(string='DTF (%)', digits=(5, 2), readonly=True)
    tasa_min_orientativa = fields.Float(string='Tasa Mín. Mercado (%)', digits=(5, 2), readonly=True)
    tasa_max_orientativa = fields.Float(string='Tasa Máx. Mercado (%)', digits=(5, 2), readonly=True)
    fecha_tasas = fields.Datetime(string='Tasas consultadas el', readonly=True)

    # ── Contexto de liquidez empresa ───────────────────────────────────────
    excedente_empresa = fields.Monetary(
        string='Excedente Empresa',
        currency_field='currency_id',
        compute='_compute_contexto_liquidez',
        help='Excedente invertible del Dashboard Consolidado (Saldo − Margen de Protección)'
    )
    total_invertido_activo = fields.Monetary(
        string='Ya Invertido (activas)',
        currency_field='currency_id',
        compute='_compute_contexto_liquidez',
        help='Suma de montos de TODAS las inversiones activas'
    )
    excedente_disponible = fields.Monetary(
        string='Disponible para Invertir',
        currency_field='currency_id',
        compute='_compute_contexto_liquidez',
        help='Excedente Empresa − Ya Invertido. Se actualiza al guardar.'
    )
    pct_excedente_usado = fields.Float(
        string='% Excedente Usado',
        digits=(5, 1),
        compute='_compute_contexto_liquidez',
    )

    # ── Comisión del instrumento (computed, guardado) ──────────────────────
    comision_anual = fields.Float(
        string='Comisión Anual (%)',
        compute='_compute_comision',
        store=True,
    )

    # ── Fechas ─────────────────────────────────────────────────────────────
    fecha_vencimiento = fields.Date(
        string='Fecha de Vencimiento',
        compute='_compute_fecha_vencimiento',
        store=True,
    )
    dias_restantes = fields.Integer(
        string='Días Restantes',
        compute='_compute_dias_restantes',
    )

    # ── Resultados financieros ─────────────────────────────────────────────
    retorno_bruto = fields.Monetary(
        string='Retorno Bruto', currency_field='currency_id',
        compute='_compute_retornos', store=True,
    )
    comision_monto = fields.Monetary(
        string='(−) Comisión', currency_field='currency_id',
        compute='_compute_retornos', store=True,
    )
    retencion_fuente = fields.Monetary(
        string='(−) Retención Fuente (7%)', currency_field='currency_id',
        compute='_compute_retornos', store=True,
    )
    gmf_monto = fields.Monetary(
        string='(−) GMF Retiro (4×1000)', currency_field='currency_id',
        compute='_compute_retornos', store=True,
    )
    retorno_neto = fields.Monetary(
        string='Retorno Neto', currency_field='currency_id',
        compute='_compute_retornos', store=True,
    )
    capital_final = fields.Monetary(
        string='Capital Final Neto', currency_field='currency_id',
        compute='_compute_retornos', store=True,
        help='Capital + Retorno Neto − GMF de entrada al invertir'
    )
    roi_neto = fields.Float(
        string='ROI Neto (%)', digits=(6, 2),
        compute='_compute_retornos', store=True,
    )
    tasa_efectiva_neta = fields.Float(
        string='Tasa Efectiva Neta EA (%)', digits=(6, 2),
        compute='_compute_retornos', store=True,
    )
    alerta = fields.Selection([
        ('ok',          '✅ Rentable'),
        ('info',        'ℹ️ Rentabilidad marginal'),
        ('advertencia', '⚠️ Plazo corto'),
        ('critico',     '🔴 Genera pérdida'),
    ], string='Alerta', compute='_compute_alerta', store=True)

    # ── Compañía ───────────────────────────────────────────────────────────
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    # ==========================================================================
    # COMPUTED: CONTEXTO DE LIQUIDEZ
    # ==========================================================================

    def _compute_contexto_liquidez(self):
        """
        Compara el excedente del dashboard empresa con el total ya invertido.

        Al guardar una inversión nueva (activa), el 'disponible' baja
        automáticamente porque este compute recorre todas las activas.
        No usa store=True para que siempre esté fresco.
        """
        for rec in self:
            empresa = self.env['sicone.config.empresa'].search(
                [('active', '=', True), ('company_id', '=', rec.company_id.id)],
                order='id asc', limit=1
            )
            excedente_empresa = empresa.cf_excedente if empresa else 0.0

            # Suma de TODAS las inversiones activas de la empresa
            todas_activas = self.search([
                ('estado', '=', 'activa'),
                ('company_id', '=', rec.company_id.id),
            ])
            total_invertido = sum(o.monto for o in todas_activas)

            excedente_disponible = excedente_empresa - total_invertido
            pct = (total_invertido / excedente_empresa * 100) if excedente_empresa > 0 else 0.0

            rec.excedente_empresa      = excedente_empresa
            rec.total_invertido_activo = total_invertido
            rec.excedente_disponible   = excedente_disponible
            rec.pct_excedente_usado    = pct

    # ==========================================================================
    # COMPUTED: PARÁMETROS
    # ==========================================================================

    @api.depends('instrumento')
    def _compute_comision(self):
        for rec in self:
            rec.comision_anual = COMISIONES.get(rec.instrumento, 0.0)

    @api.depends('fecha_inicio', 'plazo_dias')
    def _compute_fecha_vencimiento(self):
        for rec in self:
            if rec.fecha_inicio and rec.plazo_dias:
                rec.fecha_vencimiento = rec.fecha_inicio + timedelta(days=rec.plazo_dias)
            else:
                rec.fecha_vencimiento = False

    def _compute_dias_restantes(self):
        hoy = date.today()
        for rec in self:
            if rec.fecha_vencimiento and rec.estado == 'activa':
                rec.dias_restantes = (rec.fecha_vencimiento - hoy).days
            else:
                rec.dias_restantes = 0

    # ==========================================================================
    # COMPUTED: RETORNOS FINANCIEROS
    # ==========================================================================

    @api.depends('monto', 'plazo_dias', 'tasa_ea', 'comision_anual')
    def _compute_retornos(self):
        """
        Fórmulas idénticas al módulo Streamlit original:
          Retorno Bruto  = Monto × [(1+i)^(n/365) − 1]
          Comisión       = Monto × (com/100) × (n/365)
          Retención      = Bruto × 7%
          GMF retiro     = (Monto + Bruto) × 0.4%
          Retorno Neto   = Bruto − Comisión − Retención − GMF retiro
          Capital Final  = Monto + Neto − GMF entrada
          Tasa Ef. Neta  = [(1 + Neto/Monto)^(365/n) − 1] × 100
        """
        for rec in self:
            if not rec.monto or not rec.plazo_dias or not rec.tasa_ea:
                rec.retorno_bruto = rec.comision_monto = rec.retencion_fuente = 0.0
                rec.gmf_monto = rec.retorno_neto = rec.roi_neto = rec.tasa_efectiva_neta = 0.0
                rec.capital_final = rec.monto or 0.0
                continue

            n = rec.plazo_dias
            i = rec.tasa_ea / 100.0

            bruto     = rec.monto * ((1.0 + i) ** (n / 365.0) - 1.0)
            comision  = rec.monto * (rec.comision_anual / 100.0) * (n / 365.0)
            retencion = bruto * RETENCION
            gmf_ret   = (rec.monto + bruto) * GMF
            neto      = bruto - comision - retencion - gmf_ret
            capital_f = rec.monto + neto - rec.monto * GMF
            roi       = (neto / rec.monto) * 100.0
            tasa_ef   = ((1.0 + neto / rec.monto) ** (365.0 / n) - 1.0) * 100.0 if n > 0 else 0.0

            rec.retorno_bruto      = bruto
            rec.comision_monto     = comision
            rec.retencion_fuente   = retencion
            rec.gmf_monto          = gmf_ret
            rec.retorno_neto       = neto
            rec.capital_final      = capital_f
            rec.roi_neto           = roi
            rec.tasa_efectiva_neta = tasa_ef

    @api.depends('retorno_neto', 'roi_neto', 'plazo_dias', 'instrumento')
    def _compute_alerta(self):
        for rec in self:
            if not rec.monto or not rec.plazo_dias:
                rec.alerta = 'ok'
                continue
            plazo_min = PLAZOS_MINIMOS.get(rec.instrumento, 30)
            if rec.retorno_neto < 0:
                rec.alerta = 'critico'
            elif rec.plazo_dias < plazo_min:
                rec.alerta = 'advertencia'
            elif rec.roi_neto < 0.5:
                rec.alerta = 'info'
            else:
                rec.alerta = 'ok'

    # ==========================================================================
    # ACCIÓN: CONSULTAR TASAS EN VIVO (Banco de la República)
    # ==========================================================================

    def action_consultar_tasas(self):
        """
        Intenta consultar IBR overnight desde datos.gov.co (API Socrata del Banrep).
        Si el servidor no tiene acceso a esa URL, hace fallback a tasas de referencia
        hardcoded y notifica al usuario sin lanzar error bloqueante.

        Convierte IBR nominal overnight a EA: (1 + i/100)^365 − 1
        Estima DTF = IBR_EA + 0.45% (relación histórica estable).
        """
        self.ensure_one()
        from datetime import datetime as dt

        rango = TASAS_ORIENTATIVAS.get(self.instrumento, (0.0, 0.0))
        nombre_instrumento = dict(self._fields['instrumento'].selection).get(self.instrumento, '')

        # Tasas de referencia hardcoded (actualizar manualmente si la API no está disponible)
        # Fuente: Banco de la República — abril 2026
        IBR_REFERENCIA = 9.86   # IBR overnight EA aproximado
        DTF_REFERENCIA = 10.31  # DTF estimado

        ibr_ea = IBR_REFERENCIA
        dtf_ea = DTF_REFERENCIA
        fuente = 'referencia manual (Banrep abr-2026)'
        tipo_notif = 'warning'

        try:
            import requests

            resp = requests.get(
                "https://www.datos.gov.co/resource/b8fs-cx24.json"
                "?$order=vigenciadesde DESC&$limit=1",
                timeout=6
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    ultimo = data[0]
                    valor = float(ultimo.get('valor', 0))
                    tipo  = ultimo.get('tipotasa', '')
                    ibr_ea = round(
                        ((1 + valor / 100) ** 365 - 1) * 100 if tipo == 'Nominal' else valor,
                        2
                    )
                    dtf_ea = round(ibr_ea + 0.45, 2)
                    fuente = 'datos.gov.co (Banrep)'
                    tipo_notif = 'success'

        except Exception as e:
            # Fallo silencioso: el servidor no alcanza la URL externa
            # Se usan las tasas de referencia hardcoded definidas arriba
            _logger.warning('No se pudo consultar tasas en vivo (%s). Usando referencia.', str(e))

        self.write({
            'ibr_actual':           ibr_ea,
            'dtf_actual':           dtf_ea,
            'tasa_min_orientativa': rango[0],
            'tasa_max_orientativa': rango[1],
            'fecha_tasas':          dt.now(),
        })

        titulo = '📡 Tasas actualizadas' if tipo_notif == 'success' else '⚠️ Tasas de referencia cargadas'
        mensaje = (
            f'IBR EA: {ibr_ea:.2f}%  |  DTF: {dtf_ea:.2f}%  |  '
            f'Rango {nombre_instrumento}: {rango[0]}% – {rango[1]}%\n'
            f'Fuente: {fuente}'
        )
        if tipo_notif == 'warning':
            mensaje += '\n\nEl servidor no alcanzó datos.gov.co. Se usaron tasas de referencia — verifica con tu banco.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   titulo,
                'message': mensaje,
                'type':    tipo_notif,
                'sticky':  tipo_notif == 'warning',
            }
        }

    # ==========================================================================
    # ACCIONES DE ESTADO
    # ==========================================================================

    def action_marcar_vencida(self):
        for rec in self:
            rec.estado = 'vencida'

    def action_marcar_cancelada(self):
        for rec in self:
            rec.estado = 'cancelada'

    @api.model
    def get_timeline_data(self):
        """
        Retorna las inversiones activas para el widget JS del timeline.
        Llamado via RPC desde static/src/js/timeline.js
        """
        inversiones = self.search([('estado', '=', 'activa')])
        resultado = []
        for inv in inversiones:
            if not inv.fecha_inicio or not inv.fecha_vencimiento:
                continue
            resultado.append({
                'id':                inv.id,
                'nombre':            inv.nombre or '',
                'instrumento':       inv.instrumento or '',
                'entidad':           inv.entidad or '',
                'monto':             inv.monto,
                'tasa_ea':           inv.tasa_ea,
                'plazo_dias':        inv.plazo_dias,
                'fecha_inicio':      str(inv.fecha_inicio),
                'fecha_vencimiento': str(inv.fecha_vencimiento),
                'dias_restantes':    inv.dias_restantes,
                'retorno_neto':      inv.retorno_neto,
                'roi_neto':          inv.roi_neto,
                'alerta':            inv.alerta or 'ok',
            })
        return resultado
