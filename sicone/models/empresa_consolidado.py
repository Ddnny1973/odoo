# -*- coding: utf-8 -*-
"""
MÓDULO: Análisis Empresarial Consolidado
=========================================
Consolida el cash flow de todos los proyectos activos de SICONE
en un único dashboard con métricas empresariales.

MODELOS:
- sicone.config.empresa: Configuración global (gastos fijos, semanas margen/proyección)
- sicone.consolidado.mes: Resumen mensual consolidado de todos los proyectos

LÓGICA DE GASTOS FIJOS:
  Promedio mensual de movimientos con categoria='gasto_fijo' sin proyecto_id
  de los últimos 6 meses. El usuario puede aceptar o modificar el valor.

LÓGICA DE BURN RATE CONSOLIDADO:
  Promedio móvil de las últimas 8 semanas de egresos de TODOS los proyectos
  + gastos fijos empresariales semanales.

ESTADOS DE LIQUIDEZ:
  CRÍTICO  → saldo < margen × 0.5
  ALERTA   → saldo < margen
  ESTABLE  → saldo < margen × 2
  EXCEDENTE → saldo >= margen × 2

CONCILIACIÓN:
  El usuario ingresa saldos bancarios reales (iniciales y finales del período).
  El sistema compara el saldo acumulado calculado vs el saldo real final
  para detectar desviaciones.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta
from collections import defaultdict


MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# Año de corte: solo se procesan movimientos desde este año en adelante
ANIO_CONCILIACION = 2025


def _estado_liquidez(saldo, margen):
    """Determina el estado de liquidez según saldo vs margen de protección"""
    if saldo < 0:
        return 'critico'
    elif saldo < margen * 0.5:
        return 'critico'
    elif saldo < margen:
        return 'alerta'
    elif saldo < margen * 2:
        return 'estable'
    else:
        return 'excedente'


# ==============================================================================
# MODELO: Configuración Empresarial
# ==============================================================================

class ConfigEmpresa(models.Model):
    """
    Configuración global del módulo empresarial SICONE.
    Solo debe existir un registro activo (singleton pattern).
    """
    _name = 'sicone.config.empresa'
    _description = 'Configuración Empresarial SICONE'

    name = fields.Char(string='Nombre', default='Configuración Principal', required=True)
    active = fields.Boolean(string='Activo', default=True)

    # ── Gastos fijos empresariales ─────────────────────────────────────────
    gastos_fijos_mensuales = fields.Monetary(
        string='Gastos Fijos Mensuales',
        currency_field='currency_id',
        help='Gastos fijos empresariales mensuales: nómina administrativa, '
             'arriendo, servicios, etc. El sistema sugiere el promedio de los '
             'últimos 6 meses desde los movimientos contables.'
    )
    gastos_fijos_sugeridos = fields.Monetary(
        string='Sugerido por el Sistema',
        currency_field='currency_id',
        readonly=True,
        help='Promedio mensual de gastos fijos de los últimos 6 meses '
             'calculado desde movimientos contables sin proyecto asignado.'
    )
    gastos_fijos_semanales = fields.Monetary(
        string='Gastos Fijos Semanales',
        compute='_compute_gastos_semanales',
        currency_field='currency_id',
        store=True,
    )
    fecha_ultimo_calculo = fields.Date(
        string='Último cálculo sugerido', readonly=True
    )

    # ── Parámetros de proyección ───────────────────────────────────────────
    semanas_margen = fields.Integer(
        string='Semanas de Margen de Protección',
        default=8,
        help='Número de semanas de burn rate a mantener como reserva. '
             'Margen = Burn Rate Total × semanas_margen'
    )
    semanas_proyeccion = fields.Integer(
        string='Semanas de Proyección',
        default=8,
        help='Semanas a proyectar hacia adelante desde hoy en el consolidado'
    )

    # ── Saldos bancarios reales — Conciliación ─────────────────────────────
    saldo_inicial_fiducuenta = fields.Monetary(
        string='Saldo Inicial Fiducuenta',
        currency_field='currency_id',
        default=310617303.0,
        help='Saldo real de la Fiducuenta al 01/01/2025 según extracto bancario.'
    )
    saldo_inicial_cuenta = fields.Monetary(
        string='Saldo Inicial Cuenta de Ahorros',
        currency_field='currency_id',
        default=550820851.0,
        help='Saldo real de la Cuenta de Ahorros al 01/01/2025 según extracto bancario.'
    )
    saldo_final_fiducuenta = fields.Monetary(
        string='Saldo Final Fiducuenta',
        currency_field='currency_id',
        default=0.0,
        help='Saldo real de la Fiducuenta al cierre del período de conciliación según extracto.'
    )
    saldo_final_cuenta = fields.Monetary(
        string='Saldo Final Cuenta de Ahorros',
        currency_field='currency_id',
        default=0.0,
        help='Saldo real de la Cuenta de Ahorros al cierre del período según extracto.'
    )
    fecha_corte_conciliacion = fields.Date(
        string='Fecha de Corte',
        help='Fecha hasta la cual aplica la conciliación. '
             'El sistema compara el saldo calculado hasta esta fecha '
             'contra los saldos finales reales ingresados.'
    )

    # ── Campos computados de conciliación ─────────────────────────────────
    saldo_inicial_total = fields.Monetary(
        string='Saldo Inicial Total',
        compute='_compute_saldos_conciliacion',
        currency_field='currency_id',
        store=True,
        help='Suma de saldo inicial Fiducuenta + Cuenta de Ahorros.'
    )
    saldo_final_real_total = fields.Monetary(
        string='Saldo Final Real Total',
        compute='_compute_saldos_conciliacion',
        currency_field='currency_id',
        store=True,
        help='Suma de saldo final real Fiducuenta + Cuenta de Ahorros según extractos.'
    )
    diferencia_conciliacion = fields.Monetary(
        string='Diferencia de Conciliación',
        compute='_compute_diferencia_conciliacion',
        currency_field='currency_id',
        store=True,
        help='Saldo final real − Saldo calculado por el sistema al corte. '
             'Valor positivo: el banco tiene más de lo calculado. '
             'Valor negativo: el sistema calculó más de lo real.'
    )
    estado_conciliacion = fields.Selection([
        ('sin_datos', 'Sin datos'),
        ('cuadrado', 'Cuadrado'),
        ('desviacion_menor', 'Desviación menor'),
        ('desviacion_mayor', 'Desviación mayor'),
    ], string='Estado Conciliación',
       compute='_compute_diferencia_conciliacion',
       store=True,
       help='Cuadrado: diferencia < 3% (margen técnico aceptable). '
            'Desviación menor: diferencia entre 3% y 10% (explicable y manejable). '
            'Desviación mayor: diferencia > 10% (requiere investigación).'
    )

    # ── Compañía ───────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    @api.depends('gastos_fijos_mensuales')
    def _compute_gastos_semanales(self):
        for rec in self:
            rec.gastos_fijos_semanales = rec.gastos_fijos_mensuales / 4.33

    @api.depends('saldo_inicial_fiducuenta', 'saldo_inicial_cuenta',
                 'saldo_final_fiducuenta', 'saldo_final_cuenta')
    def _compute_saldos_conciliacion(self):
        for rec in self:
            rec.saldo_inicial_total = rec.saldo_inicial_fiducuenta + rec.saldo_inicial_cuenta
            rec.saldo_final_real_total = rec.saldo_final_fiducuenta + rec.saldo_final_cuenta

    @api.depends('saldo_final_real_total', 'cf_saldo_actual')
    def _compute_diferencia_conciliacion(self):
        """
        Compara el saldo final real ingresado contra el saldo calculado
        por el sistema al último mes del consolidado.
        Solo aplica cuando ambos saldos finales están cargados.
        """
        for rec in self:
            if not rec.saldo_final_fiducuenta and not rec.saldo_final_cuenta:
                rec.diferencia_conciliacion = 0.0
                rec.estado_conciliacion = 'sin_datos'
                continue

            saldo_real = rec.saldo_final_real_total
            saldo_calculado = rec.cf_saldo_actual

            diferencia = saldo_real - saldo_calculado
            rec.diferencia_conciliacion = diferencia

            if saldo_calculado == 0:
                rec.estado_conciliacion = 'sin_datos'
            else:
                pct = abs(diferencia) / saldo_calculado
                if pct < 0.03:
                    rec.estado_conciliacion = 'cuadrado'
                elif pct < 0.10:
                    rec.estado_conciliacion = 'desviacion_menor'
                else:
                    rec.estado_conciliacion = 'desviacion_mayor'

    def action_calcular_sugerido(self):
        """
        Calcula el gasto fijo mensual sugerido basado en los últimos 6 meses
        de movimientos contables sin proyecto asignado (CC administrativos).
        """
        self.ensure_one()

        hoy = date.today()
        hace_6_meses = hoy - timedelta(days=180)

        movimientos = self.env['sicone.movimiento.contable'].search([
            ('tipo', '=', 'egreso'),
            ('fuente', '=', 'libro_auxiliar'),
            ('proyecto_id', '=', False),
            ('fecha', '>=', hace_6_meses),
            ('fecha', '<=', hoy),
        ])

        if not movimientos:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin datos',
                    'message': 'No se encontraron gastos fijos en los últimos 6 meses.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        por_mes = defaultdict(float)
        for mov in movimientos:
            key = (mov.fecha.year, mov.fecha.month)
            por_mes[key] += mov.monto

        promedio = sum(por_mes.values()) / len(por_mes) if por_mes else 0.0

        self.gastos_fijos_sugeridos = promedio
        self.fecha_ultimo_calculo = hoy

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Sugerido calculado',
                'message': (
                    f'Promedio de {len(por_mes)} mes(es): '
                    f'${promedio:,.0f}/mes basado en gastos fijos administrativos.'
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_aplicar_sugerido(self):
        """Aplica el valor sugerido como gasto fijo mensual"""
        self.ensure_one()
        if self.gastos_fijos_sugeridos:
            self.gastos_fijos_mensuales = self.gastos_fijos_sugeridos

    @api.model
    def get_config(self):
        """Obtiene o crea la configuración activa"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({
                'name': 'Configuración Principal',
                'gastos_fijos_mensuales': 0,
                'semanas_margen': 8,
                'semanas_proyeccion': 8,
            })
        return config

    @api.model
    def action_abrir_dashboard(self):
        """Abre siempre el registro singleton existente — nunca crea uno nuevo."""
        config = self.search([('active', '=', True)], order='id asc', limit=1)
        if not config:
            config = self.create({
                'name': 'Configuración Principal',
                'gastos_fijos_mensuales': 0,
                'semanas_margen': 8,
                'semanas_proyeccion': 8,
                'saldo_inicial_fiducuenta': 310617303.0,
                'saldo_inicial_cuenta': 550820851.0,
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.config.empresa',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'mode': 'edit'},
        }


# ==============================================================================
# MODELO: Consolidado Mensual
# ==============================================================================

class ConsolidadoMes(models.Model):
    """
    Resumen mensual consolidado de todos los proyectos activos.
    Generado por action_recalcular en sicone.config.empresa.
    """
    _name = 'sicone.consolidado.mes'
    _description = 'Cash Flow Consolidado Mensual'
    _order = 'anio, mes'

    anio = fields.Integer(string='Año', required=True)
    mes = fields.Integer(string='Mes', required=True)
    nombre_mes = fields.Char(
        string='Período', compute='_compute_nombre_mes', store=True
    )

    # ── Flujos consolidados ────────────────────────────────────────────────
    ingresos = fields.Monetary(
        string='Ingresos', currency_field='currency_id',
        help='Suma de ingresos reales de todos los proyectos (fuente: carga_historica), solo 2025+'
    )
    egresos_proyectos = fields.Monetary(
        string='Egresos Proyectos', currency_field='currency_id',
        help='Suma de egresos de todos los proyectos activos'
    )
    gastos_fijos = fields.Monetary(
        string='Gastos Fijos', currency_field='currency_id',
        help='Gastos fijos empresariales del mes'
    )
    egresos_total = fields.Monetary(
        string='Egresos Total',
        compute='_compute_egresos_total',
        store=True,
        currency_field='currency_id'
    )
    flujo_neto = fields.Monetary(
        string='Flujo Neto',
        compute='_compute_flujo_neto',
        store=True,
        currency_field='currency_id'
    )
    saldo_acumulado = fields.Monetary(
        string='Saldo Acum.', currency_field='currency_id',
        help='Saldo bancario calculado: saldo inicial real + flujos acumulados desde enero 2025'
    )

    # ── Indicadores de gestión ─────────────────────────────────────────────
    burn_rate_semanal = fields.Monetary(
        string='Burn Rate/Sem', currency_field='currency_id',
        help='Promedio de egresos totales (proyectos + fijos) de las últimas 8 semanas'
    )
    runway_semanas = fields.Float(
        string='Runway (sem)', digits=(6, 1),
        help='Semanas de operación disponibles con el saldo actual'
    )
    margen_proteccion = fields.Monetary(
        string='Margen Prot.', currency_field='currency_id',
        help='Burn rate semanal × semanas_margen configuradas'
    )
    excedente_invertible = fields.Monetary(
        string='Excedente', currency_field='currency_id',
        help='Saldo acumulado − margen de protección'
    )
    estado_liquidez = fields.Selection([
        ('excedente', 'Excedente'),
        ('estable', 'Estable'),
        ('alerta', 'Alerta'),
        ('critico', 'Crítico'),
    ], string='Estado', default='estable')

    # ── Desglose de egresos por categoría ─────────────────────────────────
    egresos_materiales = fields.Monetary(string='Materiales', currency_field='currency_id')
    egresos_mano_obra = fields.Monetary(string='Mano de Obra', currency_field='currency_id')
    egresos_variables = fields.Monetary(string='Variables', currency_field='currency_id')
    egresos_admin = fields.Monetary(string='Administración', currency_field='currency_id')

    # ── Métricas de cartera ────────────────────────────────────────────────
    cartera_cobrada = fields.Monetary(
        string='Cartera Cobrada', currency_field='currency_id',
        help='Suma de cobros recibidos de todos los proyectos activos al final del mes'
    )
    proyectos_activos = fields.Integer(string='Proyectos Activos')
    proyecto_critico = fields.Char(
        string='Proyecto Crítico',
        help='Proyecto con menor saldo acumulado en este mes'
    )

    # ── Compañía ───────────────────────────────────────────────────────────
    config_id = fields.Many2one(
        'sicone.config.empresa',
        string='Configuración',
        ondelete='cascade',
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    @api.depends('anio', 'mes')
    def _compute_nombre_mes(self):
        for rec in self:
            rec.nombre_mes = (
                f"{MESES_ES.get(rec.mes, '')} {rec.anio}"
                if rec.anio and rec.mes else ''
            )

    @api.depends('egresos_proyectos', 'gastos_fijos')
    def _compute_egresos_total(self):
        for rec in self:
            rec.egresos_total = rec.egresos_proyectos + rec.gastos_fijos

    @api.depends('ingresos', 'egresos_total')
    def _compute_flujo_neto(self):
        for rec in self:
            rec.flujo_neto = rec.ingresos - rec.egresos_total


# ==============================================================================
# ACCIÓN DE RECÁLCULO — agregada a ConfigEmpresa
# ==============================================================================

class ConfigEmpresaRecalculo(models.Model):
    """Extensión de ConfigEmpresa con la lógica de recálculo consolidado"""
    _inherit = 'sicone.config.empresa'

    # ── KPIs actuales (del último mes consolidado) ─────────────────────────
    consolidado_ids = fields.One2many(
        'sicone.consolidado.mes', 'config_id',
        string='Consolidado Mensual',
    )

    cf_saldo_actual = fields.Monetary(
        string='Saldo Actual', compute='_compute_kpi_consolidado',
        currency_field='currency_id',
        help='Saldo bancario calculado al último mes del consolidado. '
             'Parte del saldo inicial real ingresado en Conciliación.'
    )
    cf_burn_rate = fields.Monetary(
        string='Burn Rate Semanal', compute='_compute_kpi_consolidado',
        currency_field='currency_id'
    )
    cf_runway = fields.Float(
        string='Runway (semanas)', compute='_compute_kpi_consolidado',
        digits=(6, 1)
    )
    cf_margen = fields.Monetary(
        string='Margen de Protección', compute='_compute_kpi_consolidado',
        currency_field='currency_id'
    )
    cf_excedente = fields.Monetary(
        string='Excedente Invertible', compute='_compute_kpi_consolidado',
        currency_field='currency_id'
    )
    cf_estado = fields.Selection([
        ('excedente', 'Excedente'),
        ('estable', 'Estable'),
        ('alerta', 'Alerta'),
        ('critico', 'Crítico'),
    ], string='Estado Liquidez', compute='_compute_kpi_consolidado')
    cf_proyectos_activos = fields.Integer(
        string='Proyectos Activos', compute='_compute_kpi_consolidado'
    )
    cf_cartera_cobrada = fields.Monetary(
        string='Cartera Cobrada', compute='_compute_kpi_consolidado',
        currency_field='currency_id',
        help='Total de cobros recibidos de los proyectos activos en 2025.'
    )
    cf_proyecto_critico = fields.Char(
        string='Proyecto Critico', compute='_compute_kpi_consolidado'
    )

    # Campo HTML para el widget Waterfall
    waterfall_html = fields.Html(
        string='Cash Flow Waterfall',
        compute='_compute_waterfall_html',
        sanitize=False,
    )

    @api.depends('consolidado_ids.ingresos', 'consolidado_ids.egresos_total',
                 'consolidado_ids.saldo_acumulado', 'consolidado_ids.nombre_mes',
                 'saldo_inicial_fiducuenta', 'saldo_inicial_cuenta')
    def _compute_waterfall_html(self):
        import json as _json
        meses_cortos = {
            1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
            7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'
        }
        for config in self:
            meses = config.consolidado_ids.sorted(lambda r: (r.anio, r.mes))
            if not meses:
                config.waterfall_html = '<p style="color:#999;padding:16px;">Sin datos</p>'
                continue
            datos = []
            for m in meses:
                datos.append({
                    'mes': meses_cortos.get(m.mes, str(m.mes)) + ' ' + str(m.anio)[2:],
                    'ing': m.ingresos,
                    'egr': m.egresos_total,
                    'sal': m.saldo_acumulado,
                })
            si = (config.saldo_inicial_fiducuenta or 0.0) + (config.saldo_inicial_cuenta or 0.0)
            dj = _json.dumps(datos)
            config.waterfall_html = (
                '<div class="sicone-waterfall"'
                ' data-consolidado='' + dj + '''
                ' data-saldo-inicial='' + str(si) + '''
                ' style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:12px;margin-bottom:16px;">'
                '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">'
                '<span style="font-weight:600;font-size:13px;color:#2C3E50;">Cash Flow Consolidado 2025</span>'
                '<div style="display:flex;gap:6px;">'
                '<button class="wf-btn-mensual" style="font-size:11px;padding:3px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:#eee;">Mensual</button>'
                '<button class="wf-btn-anual" style="font-size:11px;padding:3px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:transparent;">Anual</button>'
                '</div></div>'
                '<div style="height:280px;position:relative;"><canvas class="wf-canvas"></canvas></div>'
                '</div>'
            )

    @api.depends('consolidado_ids.saldo_acumulado', 'consolidado_ids.burn_rate_semanal',
                 'consolidado_ids.runway_semanas', 'consolidado_ids.margen_proteccion',
                 'consolidado_ids.excedente_invertible', 'consolidado_ids.estado_liquidez')
    def _compute_kpi_consolidado(self):
        """Lee los KPIs del último mes calculado"""
        for config in self:
            meses = self.env['sicone.consolidado.mes'].search(
                [('company_id', '=', config.company_id.id)],
                order='anio desc, mes desc',
                limit=1
            )
            if meses:
                m = meses[0]
                config.cf_saldo_actual = m.saldo_acumulado
                config.cf_burn_rate = m.burn_rate_semanal
                config.cf_runway = m.runway_semanas
                config.cf_margen = m.margen_proteccion
                config.cf_excedente = m.excedente_invertible
                config.cf_estado = m.estado_liquidez
                config.cf_proyectos_activos = m.proyectos_activos
                config.cf_cartera_cobrada = m.cartera_cobrada
                config.cf_proyecto_critico = m.proyecto_critico or ''
            else:
                config.cf_saldo_actual = 0.0
                config.cf_burn_rate = 0.0
                config.cf_runway = 0.0
                config.cf_margen = 0.0
                config.cf_excedente = 0.0
                config.cf_estado = 'estable'
                config.cf_proyectos_activos = 0
                config.cf_cartera_cobrada = 0.0
                config.cf_proyecto_critico = ''


    @api.model
    def get_waterfall_data(self):
        """
        Retorna los datos del consolidado para el widget waterfall.
        Llamado via RPC desde waterfall.js para evitar sanitizacion
        de atributos data-* en campos Html.
        """
        config = self.search([('active','=',True)], order='id asc', limit=1)
        if not config:
            return {'datos': [], 'saldo_inicial': 0}
        meses_cortos = {
            1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
            7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'
        }
        meses = config.consolidado_ids.sorted(lambda r: (r.anio, r.mes))
        datos = []
        for m in meses:
            datos.append({
                'mes': meses_cortos.get(m.mes, str(m.mes)) + ' ' + str(m.anio)[2:],
                'ing': m.ingresos,
                'egr': m.egresos_total,
                'sal': m.saldo_acumulado,
            })
        si = (config.saldo_inicial_fiducuenta or 0.0) + (config.saldo_inicial_cuenta or 0.0)
        return {'datos': datos, 'saldo_inicial': si}


    # ── Campo HTML para el widget Timeline de Inversiones ─────────────
    timeline_inversiones_html = fields.Html(
        string='Timeline de Vencimientos',
        compute='_compute_timeline_inversiones_html',
        sanitize=False,
    )

    def _compute_timeline_inversiones_html(self):
        """Genera el div contenedor del timeline — el JS lo rellena via RPC."""
        for rec in self:
            rec.timeline_inversiones_html = (
                '<div class="sicone-timeline" '
                'style="background:#fff;border:1px solid #e0e0e0;'
                'border-radius:6px;padding:16px;min-height:120px;">'
                '<span style="font-weight:600;font-size:13px;color:#2C3E50;">'
                'Timeline de Vencimientos — Inversiones Activas</span>'
                '</div>'
            )

    def action_recalcular_consolidado(self):
        """
        Recalcula el cash flow consolidado de todos los proyectos activos.

        NOTA: El return usa 'ir.actions.client' tag='reload' para forzar
        recarga completa de la página. Esto es necesario porque el widget
        One2many de consolidado_ids no refresca su caché al hacer act_window
        al mismo formulario — el reload garantiza que la tabla mensual
        aparezca actualizada sin necesidad de F5 manual.
        """
        self.ensure_one()
        config = self

        # ── Proyectos activos + finalizados (sus movimientos siguen siendo reales) ──
        proyectos = self.env['sicone.proyecto'].search([
            ('estado', 'in', ('contratado', 'ejecucion', 'finalizado')),
            ('active', '=', True),
        ])

        if not proyectos:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin proyectos',
                    'message': 'No hay proyectos en estado Contratado, En Ejecución o Finalizado.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        proyecto_ids = proyectos.ids

        # ── Movimientos de proyectos ───────────────────────────────────────
        movimientos = self.env['sicone.movimiento.contable'].search([
            ('proyecto_id', 'in', proyecto_ids),
        ])

        # ── Egresos corporativos (sin proyecto) ────────────────────────────
        gastos_corp = self.env['sicone.movimiento.contable'].search([
            ('tipo', '=', 'egreso'),
            ('proyecto_id', '=', False),
        ])

        # ── Agrupar por mes ────────────────────────────────────────────────
        meses = defaultdict(lambda: {
            'ingresos': 0.0,
            'egresos_proy': 0.0,       # 7x/5x — desglose por categoría/proyecto
            'egresos_banco': 0.0,      # banco — saldo real de caja
            'gastos_fijos': 0.0,       # 7x/5x sin proyecto — desglose
            'gastos_fijos_banco': 0.0, # banco sin proyecto — saldo real
            'materiales': 0.0,
            'mano_obra': 0.0,
            'variables': 0.0,
            'admin': 0.0,
        })
        semanas_egresos = defaultdict(float)

        for mov in movimientos:
            if mov.tipo == 'ingreso' and mov.fuente == 'carga_historica':
                if mov.fecha.year >= ANIO_CONCILIACION:
                    key = (mov.fecha.year, mov.fecha.month)
                    meses[key]['ingresos'] += mov.monto
            elif mov.tipo == 'egreso':
                key = (mov.fecha.year, mov.fecha.month)
                if mov.fuente == 'banco':
                    # Egreso real de caja — para saldo y burn rate
                    meses[key]['egresos_banco'] += mov.monto
                    semana = mov.fecha - timedelta(days=mov.fecha.weekday())
                    semanas_egresos[semana] += mov.monto
                else:
                    # Causación 7x/5x — para desglose por categoría/proyecto
                    meses[key]['egresos_proy'] += mov.monto
                    cat = mov.categoria or ''
                    if cat == 'materiales':
                        meses[key]['materiales'] += mov.monto
                    elif cat == 'mano_obra':
                        meses[key]['mano_obra'] += mov.monto
                    elif cat == 'variables':
                        meses[key]['variables'] += mov.monto
                    elif cat == 'administracion':
                        meses[key]['admin'] += mov.monto

        gastos_fijos_config = config.gastos_fijos_mensuales or 0.0
        for mov in gastos_corp:
            key = (mov.fecha.year, mov.fecha.month)
            if mov.fuente == 'banco':
                # Gasto fijo real de caja — para saldo y burn rate
                meses[key]['gastos_fijos_banco'] += mov.monto
                semana = mov.fecha - timedelta(days=mov.fecha.weekday())
                semanas_egresos[semana] += mov.monto
            else:
                # Causación 7x/5x — para desglose
                meses[key]['gastos_fijos'] += mov.monto

        if not meses:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin movimientos',
                    'message': 'No se encontraron movimientos contables en los proyectos activos.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # ── Ajustes de conciliación ────────────────────────────────────────
        ajustes = self.env['sicone.ajuste.conciliacion'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ])

        # ── Calcular consolidado mes a mes ─────────────────────────────────
        meses_ord = sorted(
            [(a, m) for (a, m) in meses.keys() if a >= ANIO_CONCILIACION]
        )
        semanas_ord = sorted(semanas_egresos.keys())

        saldo_acum = (config.saldo_inicial_fiducuenta or 0.0) + (config.saldo_inicial_cuenta or 0.0)

        registros = []

        for anio, mes_num in meses_ord:
            d = meses[(anio, mes_num)]

            # Para display — egresos 7x/5x
            gasto_fijo_mes = d['gastos_fijos'] if d['gastos_fijos'] > 0 else gastos_fijos_config
            # Para saldo real de caja — egresos banco
            gasto_fijo_banco_mes = d['gastos_fijos_banco']
            ajuste_mes = sum(aj.get_monto_mes(anio, mes_num) for aj in ajustes)

            saldo_acum += d['ingresos'] - d['egresos_banco'] - gasto_fijo_banco_mes + ajuste_mes

            ultimo_dia = date(anio, mes_num, 28)
            ventana = [s for s in semanas_ord if s <= ultimo_dia][-8:]
            burn_rate = (
                sum(semanas_egresos[s] for s in ventana) / len(ventana)
                if ventana else 0.0
            )
            if d['gastos_fijos_banco'] == 0 and d['gastos_fijos'] == 0 and gastos_fijos_config > 0:
                burn_rate += gastos_fijos_config / 4.33

            margen = burn_rate * config.semanas_margen
            runway = saldo_acum / burn_rate if burn_rate > 0 else 0.0
            excedente = max(0.0, saldo_acum - margen)
            estado = _estado_liquidez(saldo_acum, margen)

            saldos_proyecto = {}
            for proy in proyectos:
                cf_mes = self.env['sicone.proyecto.cashflow'].search([
                    ('proyecto_id', '=', proy.id),
                    ('anio', '=', anio),
                    ('mes', '=', mes_num),
                ], limit=1)
                if cf_mes:
                    saldos_proyecto[proy.name] = cf_mes.saldo_acumulado

            proyecto_critico = (
                min(saldos_proyecto, key=saldos_proyecto.get)
                if saldos_proyecto else ''
            )

            cartera_cobrada = sum(
                pago.monto
                for p in proyectos
                for hito in p.hito_ids
                for pago in hito.pago_ids
                if pago.fecha
                and pago.fecha >= date(ANIO_CONCILIACION, 1, 1)
                and pago.fecha <= date(anio, mes_num, 28)
            )

            registros.append({
                'anio': anio,
                'mes': mes_num,
                'ingresos': d['ingresos'] + max(0.0, ajuste_mes),
                'egresos_proyectos': d['egresos_proy'] + abs(min(0.0, ajuste_mes)),
                'gastos_fijos': gasto_fijo_mes,
                'saldo_acumulado': saldo_acum,
                'burn_rate_semanal': burn_rate,
                'runway_semanas': runway,
                'margen_proteccion': margen,
                'excedente_invertible': excedente,
                'estado_liquidez': estado,
                'egresos_materiales': d['materiales'],
                'egresos_mano_obra': d['mano_obra'],
                'egresos_variables': d['variables'],
                'egresos_admin': d['admin'],
                'cartera_cobrada': cartera_cobrada,
                'proyectos_activos': len(proyectos),
                'proyecto_critico': proyecto_critico,
                'company_id': self.company_id.id,
                'config_id': self.id,
            })

        # ── Reemplazar registros anteriores ───────────────────────────────
        self.env['sicone.consolidado.mes'].search([
            ('company_id', '=', self.company_id.id)
        ]).unlink()
        self.env['sicone.consolidado.mes'].create(registros)

        # ── Reabrir el dashboard como acción nueva ────────────────────────
        # Llamar action_abrir_dashboard fuerza un render completo del
        # formulario — el One2many de consolidado_ids carga los registros
        # frescos desde BD sin depender del caché del widget anterior.
        return self.action_abrir_dashboard()


# ==============================================================================
# MODELO: Ajuste de Conciliación
# ==============================================================================

class AjusteConciliacion(models.Model):
    """
    Ajuste de conciliación — ingresos/egresos no capturados en el libro auxiliar.

    TIPOS:
    - puntual:    Evento con fecha específica y monto único
    - recurrente: Monto mensual entre fecha_inicio y fecha_fin
    """
    _name = 'sicone.ajuste.conciliacion'
    _description = 'Ajuste de Conciliación'
    _order = 'fecha desc, tipo'

    concepto = fields.Char(string='Concepto', required=True)
    categoria = fields.Char(string='Categoría')
    cuenta = fields.Selection([
        ('banco', 'Cuenta Bancaria'),
        ('fiducuenta', 'Fiducuenta'),
        ('otro', 'Otro'),
    ], string='Cuenta', default='banco')

    tipo_registro = fields.Selection([
        ('puntual', 'Puntual'),
        ('recurrente', 'Recurrente'),
    ], string='Tipo de Registro', default='puntual', required=True)

    tipo = fields.Selection([
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ], string='Tipo', required=True)

    # Puntual
    fecha = fields.Date(string='Fecha')
    monto = fields.Monetary(string='Monto', currency_field='currency_id')

    # Recurrente
    monto_mensual = fields.Monetary(string='Monto Mensual', currency_field='currency_id')
    fecha_inicio = fields.Date(string='Fecha Inicio')
    fecha_fin = fields.Date(string='Fecha Fin')

    observaciones = fields.Text(string='Observaciones')
    evidencia = fields.Char(string='Evidencia')
    active = fields.Boolean(default=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    def get_monto_mes(self, anio, mes):
        """Retorna el monto neto que este ajuste aporta al mes (anio, mes)"""
        self.ensure_one()
        signo = 1 if self.tipo == 'ingreso' else -1
        if self.tipo_registro == 'puntual':
            if self.fecha and self.fecha.year == anio and self.fecha.month == mes:
                return signo * self.monto
            return 0.0
        else:
            if not self.fecha_inicio:
                return 0.0
            fecha_mes = date(anio, mes, 1)
            if fecha_mes < date(self.fecha_inicio.year, self.fecha_inicio.month, 1):
                return 0.0
            if self.fecha_fin:
                if fecha_mes > date(self.fecha_fin.year, self.fecha_fin.month, 1):
                    return 0.0
            return signo * self.monto_mensual
