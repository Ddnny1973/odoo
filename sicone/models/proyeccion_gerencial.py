# -*- coding: utf-8 -*-
"""
MÓDULO: Proyecciones Gerenciales
==================================
Proyecta el flujo de caja a 2-6 meses en 3 escenarios basados en:
  - Ingresos: hitos pendientes/parciales con fecha estimada
  - Egresos: histórico consolidado mensual (excluyendo outliers min/max)
  - Gastos fijos: histórico consolidado mensual
  - Inversiones: vencimientos futuros como ingresos

ESCENARIOS:
  Conservador → Q3 egresos/GF, recuperación 75%/50% de atrasos moderados/severos
  Moderado    → Mediana egresos/GF, recuperación 100%/75% de atrasos moderados/severos
  Optimista   → Mínimo egresos/GF, recuperación 100%/100% de atrasos moderados/severos
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import json
from odoo import models, fields, api
from odoo.exceptions import UserError

MESES_ES = {
    1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
    7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'
}


class ProyeccionGerencial(models.Model):
    _name = 'sicone.proyeccion.gerencial'
    _description = 'Proyecciones Gerenciales — 3 Escenarios'
    _rec_name = 'nombre'

    nombre = fields.Char(string='Nombre', default='Proyección Actual', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    # ── Parámetros generales ──────────────────────────────────────
    meses_proyeccion = fields.Integer(
        string='Meses a proyectar', default=6,
        help='Horizonte de proyección: 2 a 6 meses'
    )
    semanas_burn_rate = fields.Integer(
        string='Semanas para burn rate', default=8,
        help='Semanas históricas para calcular max/avg/min del burn rate'
    )

    # ── Gastos fijos ──────────────────────────────────────────────
    gastos_fijos_calculados = fields.Monetary(
        string='Gastos Fijos Calculados (sistema)',
        compute='_compute_gastos_calculados', store=False,
        help='Promedio mensual de egresos corporativos del banco (últimos 12 meses)'
    )
    gastos_fijos_estimados = fields.Monetary(
        string='Gastos Fijos Estimados (gerencia)', default=50000000,
        help='Estimación manual de la gerencia'
    )
    pct_optimizacion = fields.Float(
        string='% Optimización costos (escenario optimista)', default=10.0,
        help='Reducción % de gastos fijos en el escenario optimista'
    )

    # ── Parámetros de ingresos por escenario ─────────────────────
    pct_hitos_sin_fecha_moderado = fields.Float(
        string='% hitos sin fecha — Moderado', default=50.0,
        help='% del valor de hitos sin fecha estimada incluidos en moderado'
    )
    pct_hitos_sin_fecha_optimista = fields.Float(
        string='% hitos sin fecha — Optimista', default=100.0,
        help='% del valor de hitos sin fecha incluidos en optimista'
    )

    # ── Resultados ────────────────────────────────────────────────
    ultimo_calculo = fields.Datetime(string='Último cálculo', readonly=True)
    linea_ids = fields.One2many('sicone.proyeccion.linea', 'proyeccion_id', string='Líneas')
    datos_grafico = fields.Text(string='Datos gráfico', readonly=True)
    grafico_html = fields.Html(
        string='Gráfico Proyecciones',
        compute='_compute_grafico_html',
        store=False,
        sanitize=False,
    )

    # ── KPIs resumidos ────────────────────────────────────────────
    saldo_actual = fields.Monetary(
        string='Saldo Actual', compute='_compute_kpis', store=False
    )
    egr_proy_conservador = fields.Monetary(
        string='Egr. Proyectos Conservador/mes', compute='_compute_kpis', store=False
    )
    egr_proy_moderado = fields.Monetary(
        string='Egr. Proyectos Moderado/mes', compute='_compute_kpis', store=False
    )
    egr_proy_optimista = fields.Monetary(
        string='Egr. Proyectos Optimista/mes', compute='_compute_kpis', store=False
    )
    gf_conservador = fields.Monetary(
        string='GF Conservador/mes', compute='_compute_kpis', store=False
    )
    gf_moderado = fields.Monetary(
        string='GF Moderado/mes', compute='_compute_kpis', store=False
    )
    gf_optimista = fields.Monetary(
        string='GF Optimista/mes', compute='_compute_kpis', store=False
    )
    alerta = fields.Selection([
        ('ok',       'Sin alerta'),
        ('atencion', 'Atención'),
        ('critico',  'Crítico'),
    ], string='Alerta', compute='_compute_kpis', store=False)

    @api.depends('company_id')
    def _compute_gastos_calculados(self):
        for rec in self:
            meses = rec.env['sicone.consolidado.mes'].search(
                [('company_id', '=', rec.company_id.id)],
                order='anio desc, mes desc', limit=12
            )
            if meses:
                rec.gastos_fijos_calculados = sum(meses.mapped('gastos_fijos')) / len(meses)
            else:
                rec.gastos_fijos_calculados = 0.0

    @api.depends('linea_ids')
    def _compute_kpis(self):
        for rec in self:
            ultimo_mes = rec.env['sicone.consolidado.mes'].search(
                [('company_id', '=', rec.company_id.id)],
                order='anio desc, mes desc', limit=1
            )
            rec.saldo_actual = ultimo_mes.saldo_acumulado if ultimo_mes else 0.0

            egresos_hist = rec._calcular_egresos_historicos()
            rec.egr_proy_conservador = egresos_hist['conservador']['proyectos']
            rec.egr_proy_moderado = egresos_hist['moderado']['proyectos']
            rec.egr_proy_optimista = egresos_hist['optimista']['proyectos']
            rec.gf_conservador = egresos_hist['conservador']['fijos']
            rec.gf_moderado = egresos_hist['moderado']['fijos']
            rec.gf_optimista = egresos_hist['optimista']['fijos']

            # Runway basado en saldo actual y flujos proyectados
            lineas_c = rec.linea_ids.filtered(lambda l: l.escenario == 'conservador')
            lineas_m = rec.linea_ids.filtered(lambda l: l.escenario == 'moderado')

            def calc_runway(lineas):
                if not lineas:
                    return 0.0
                saldo = rec.saldo_actual
                for l in lineas.sorted('fecha'):
                    saldo += l.flujo_neto
                    if saldo <= 0:
                        return 0.0
                avg_egr = sum(l.egresos_total for l in lineas) / len(lineas)
                return (saldo / avg_egr) * 4.33 if avg_egr > 0 else 99.0

            rc = calc_runway(lineas_c)
            rm = calc_runway(lineas_m)
            min_r = min(rc, rm) if rc and rm else max(rc, rm)

            if min_r < 4:
                rec.alerta = 'critico'
            elif min_r < 8:
                rec.alerta = 'atencion'
            else:
                rec.alerta = 'ok'

    # ── Método principal ──────────────────────────────────────────
    def action_calcular(self):
        self.ensure_one()
        self.linea_ids.unlink()

        ultimo_mes = self.env['sicone.consolidado.mes'].search(
            [('company_id', '=', self.company_id.id)],
            order='anio desc, mes desc', limit=1
        )
        saldo_ini = ultimo_mes.saldo_acumulado if ultimo_mes else 0.0

        egresos_hist = self._calcular_egresos_historicos()

        params = {
            'conservador': {
                'egr_proy': egresos_hist['conservador']['proyectos'],
                'gf': egresos_hist['conservador']['fijos'],
                'pct_sin_fecha': 0.0,
            },
            'moderado': {
                'egr_proy': egresos_hist['moderado']['proyectos'],
                'gf': egresos_hist['moderado']['fijos'],
                'pct_sin_fecha': self.pct_hitos_sin_fecha_moderado,
            },
            'optimista': {
                'egr_proy': egresos_hist['optimista']['proyectos'],
                'gf': egresos_hist['optimista']['fijos'],
                'pct_sin_fecha': self.pct_hitos_sin_fecha_optimista,
            },
        }

        hitos_clasificados = self._obtener_hitos()
        inversiones = self._obtener_inversiones()
        total_sin_fecha = sum(h['saldo'] for h in hitos_clasificados['sin_fecha'])

        # Proyectar desde mes siguiente al último mes con datos reales
        if ultimo_mes:
            fecha_inicio = date(ultimo_mes.anio, ultimo_mes.mes, 1) + relativedelta(months=1)
        else:
            fecha_inicio = date.today().replace(day=1) + relativedelta(months=1)
        lineas = []

        # Precalcular distribución de atrasos por escenario (una vez)
        dist_atrasos_por_escenario = {}
        for escenario in ['conservador', 'moderado', 'optimista']:
            dist_atrasos_por_escenario[escenario] = self._distribuir_atrasos(
                hitos_clasificados, escenario, self.meses_proyeccion, fecha_inicio
            )

        for i in range(self.meses_proyeccion):
            mes_fecha = fecha_inicio + relativedelta(months=i)
            anio, mes = mes_fecha.year, mes_fecha.month

            # Ingresos de hitos futuros (programados naturalmente en este mes)
            ing_hitos_futuros = sum(
                h['saldo'] for h in hitos_clasificados['futuros']
                if h['fecha'] and h['fecha'].year == anio and h['fecha'].month == mes
            )
            
            ing_inversiones_mes = sum(
                inv['capital_final'] for inv in inversiones
                if inv['vencimiento'] and
                inv['vencimiento'].year == anio and inv['vencimiento'].month == mes
            )
            egr_inversiones_mes = sum(
                inv['monto'] for inv in inversiones
                if inv['fecha_inicio'] and
                inv['fecha_inicio'].year == anio and inv['fecha_inicio'].month == mes
            )
            sin_fecha_mensual = total_sin_fecha / self.meses_proyeccion

            for escenario, p in params.items():
                # Ingresos de recuperación de atrasos para este mes
                ing_atrasos_mes = dist_atrasos_por_escenario[escenario].get(i, 0.0)
                ing_sf = sin_fecha_mensual * p['pct_sin_fecha'] / 100
                ingresos = ing_hitos_futuros + ing_atrasos_mes + ing_sf + ing_inversiones_mes
                egresos_op = p['egr_proy']
                egresos_tot = egresos_op + p['gf'] + egr_inversiones_mes

                lineas.append({
                    'proyeccion_id': self.id,
                    'escenario': escenario,
                    'anio': anio,
                    'mes': mes,
                    'fecha': mes_fecha,
                    'label': f"{MESES_ES[mes]} {anio}",
                    'ingresos_hitos': ing_hitos_futuros + ing_atrasos_mes + ing_sf,
                    'ingresos_inversiones': ing_inversiones_mes,
                    'ingresos_total': ingresos,
                    'egresos_operativos': egresos_op,
                    'gastos_fijos': p['gf'],
                    'egresos_total': egresos_tot,
                    'flujo_neto': ingresos - egresos_tot,
                    'burn_rate_aplicado': egresos_op,
                })

        self.env['sicone.proyeccion.linea'].create(lineas)
        self._generar_datos_grafico(saldo_ini)
        self.write({'ultimo_calculo': fields.Datetime.now()})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'main',
            'context': {'notify_title': 'Proyeccion calculada',
                        'notify_msg': f'{self.meses_proyeccion} meses · 3 escenarios'},
        }

    def _calcular_egresos_historicos(self):
        """
        Calcula egresos desde consolidado mensual histórico con estadísticas IQR.
        Excluye el máximo y mínimo para moderar outliers estacionales.
        """
        self.env.cr.execute("""
            WITH ranked AS (
                SELECT 
                    egresos_proyectos,
                    gastos_fijos,
                    egresos_total,
                    ROW_NUMBER() OVER (ORDER BY egresos_total ASC) as rn_asc,
                    ROW_NUMBER() OVER (ORDER BY egresos_total DESC) as rn_desc
                FROM sicone_consolidado_mes
                WHERE anio = 2025 AND company_id = %s
            ),
            filtered AS (
                SELECT egresos_proyectos, gastos_fijos
                FROM ranked
                WHERE rn_asc > 1 AND rn_desc > 1  -- Excluye min y max
            )
            SELECT 
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY egresos_proyectos) as conservador_proy,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY egresos_proyectos) as moderado_proy,
                MIN(egresos_proyectos) as optimista_proy,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY gastos_fijos) as conservador_gf,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY gastos_fijos) as moderado_gf,
                MIN(gastos_fijos) as optimista_gf
            FROM filtered
        """, (self.company_id.id,))
        
        result = self.env.cr.fetchone()
        if not result:
            # Fallback si no hay datos históricos
            config = self.env['sicone.config.empresa'].search(
                [('company_id', '=', self.company_id.id)], limit=1
            )
            base_proy = (config.gastos_fijos_mensuales if config else 200000000) * 4
            base_gf = config.gastos_fijos_mensuales if config else 50000000
            return {
                'conservador': {'proyectos': base_proy * 1.2, 'fijos': base_gf * 1.2},
                'moderado': {'proyectos': base_proy, 'fijos': base_gf},
                'optimista': {'proyectos': base_proy * 0.8, 'fijos': base_gf * 0.8}
            }
        
        return {
            'conservador': {'proyectos': result[0], 'fijos': result[3]},
            'moderado': {'proyectos': result[1], 'fijos': result[4]},
            'optimista': {'proyectos': result[2], 'fijos': result[5]}
        }

    def _obtener_hitos(self):
        """Clasifica hitos por estado de fecha y severidad de atraso"""
        hoy = date.today()
        proyectos = self.env['sicone.proyecto'].search([
            ('estado', 'in', ['contratado', 'ejecucion']),
            ('active', '=', True)
        ])
        
        futuros = []
        atrasados_leve = []
        atrasados_moderado = []
        atrasados_severo = []
        sin_fecha = []
        
        for p in proyectos:
            for h in p.hito_ids.filtered(lambda x: x.estado in ('pendiente', 'parcial')):
                saldo = h.monto - h.cobrado
                if saldo <= 0:
                    continue
                
                if not h.fecha_estimada:
                    sin_fecha.append({'proyecto': p.name, 'saldo': saldo, 'fecha': None})
                    continue
                
                entry = {'proyecto': p.name, 'saldo': saldo, 'fecha': h.fecha_estimada}
                
                if h.fecha_estimada >= hoy:
                    futuros.append(entry)
                else:
                    semanas_atraso = (hoy - h.fecha_estimada).days / 7.0
                    if semanas_atraso < 4:
                        atrasados_leve.append(entry)
                    elif semanas_atraso < 20:
                        atrasados_moderado.append(entry)
                    else:
                        atrasados_severo.append(entry)
        
        return {
            'futuros': futuros,
            'atrasados_leve': atrasados_leve,
            'atrasados_moderado': atrasados_moderado,
            'atrasados_severo': atrasados_severo,
            'sin_fecha': sin_fecha
        }

    def _distribuir_atrasos(self, hitos_clasificados, escenario, meses_proyeccion, fecha_inicio):
        """
        Distribuye atrasos según escenario y severidad en el horizonte de proyección.
        
        CONSERVADOR: Leves 100%, Moderados 75%, Severos 50%
        MODERADO: Leves 100%, Moderados 100%, Severos 75%
        OPTIMISTA: Leves 100%, Moderados 100%, Severos 100%
        """
        leve = hitos_clasificados['atrasados_leve']
        moderado = hitos_clasificados['atrasados_moderado']
        severo = hitos_clasificados['atrasados_severo']
        
        total_leve = sum(h['saldo'] for h in leve)
        total_moderado = sum(h['saldo'] for h in moderado)
        total_severo = sum(h['saldo'] for h in severo)
        
        # Distribución mensual inicializada en 0
        distribucion = {i: 0.0 for i in range(meses_proyeccion)}
        
        if escenario == 'conservador':
            # Leves: 100% en meses 0-1
            if total_leve > 0:
                distribucion[0] += total_leve * 0.5
                if meses_proyeccion > 1:
                    distribucion[1] += total_leve * 0.5
            # Moderados: 75% distribuido uniformemente
            if total_moderado > 0:
                por_mes = (total_moderado * 0.75) / meses_proyeccion
                for i in range(meses_proyeccion):
                    distribucion[i] += por_mes
            # Severos: 50% distribuido uniformemente
            if total_severo > 0:
                por_mes = (total_severo * 0.5) / meses_proyeccion
                for i in range(meses_proyeccion):
                    distribucion[i] += por_mes
                    
        elif escenario == 'moderado':
            # Leves: 100% en meses 0-1
            if total_leve > 0:
                distribucion[0] += total_leve * 0.5
                if meses_proyeccion > 1:
                    distribucion[1] += total_leve * 0.5
            # Moderados: 100% en 2/3 del horizonte
            if total_moderado > 0:
                meses_mod = max(1, int(meses_proyeccion * 2 / 3))
                por_mes = total_moderado / meses_mod
                for i in range(meses_mod):
                    distribucion[i] += por_mes
            # Severos: 75% distribuido uniformemente
            if total_severo > 0:
                por_mes = (total_severo * 0.75) / meses_proyeccion
                for i in range(meses_proyeccion):
                    distribucion[i] += por_mes
                    
        elif escenario == 'optimista':
            # Leves: 100% en mes 0
            if total_leve > 0:
                distribucion[0] += total_leve
            # Moderados: 100% en 1/2 del horizonte
            if total_moderado > 0:
                meses_mod = max(1, int(meses_proyeccion / 2))
                por_mes = total_moderado / meses_mod
                for i in range(meses_mod):
                    distribucion[i] += por_mes
            # Severos: 100% en 2/3 del horizonte
            if total_severo > 0:
                meses_sev = max(1, int(meses_proyeccion * 2 / 3))
                por_mes = total_severo / meses_sev
                for i in range(meses_sev):
                    distribucion[i] += por_mes
        
        return distribucion

    def _obtener_inversiones(self):
        hoy = date.today()
        invs = self.env['sicone.inversion.temporal'].search([
            ('estado', '=', 'activa'),
            ('fecha_vencimiento', '>=', hoy),
        ])
        return [{'monto': inv.monto or 0, 'capital_final': inv.capital_final or 0, 'vencimiento': inv.fecha_vencimiento, 'fecha_inicio': inv.fecha_inicio} for inv in invs]

    def _generar_datos_grafico(self, saldo_ini):
        """Genera JSON continuo: histórico + proyectado (punto de unión compartido)"""
        historicos = self.env['sicone.consolidado.mes'].search(
            [('company_id', '=', self.company_id.id)],
            order='anio, mes'
        )
        labels_h = [f"{MESES_ES[h.mes]} {h.anio}" for h in historicos]
        hist     = [round(h.saldo_acumulado / 1e6, 2) for h in historicos]

        # Burn rate promedio mensual historico
        burn_promedio = sum(h.burn_rate_semanal * 4.33 for h in historicos) / len(historicos) if historicos else 0
        burn_promedio_millones = round(burn_promedio / 1e6, 2)
        lineas = self.linea_ids.sorted('fecha')

        def saldos_esc(esc):
            saldo = saldo_ini
            res = []
            for l in lineas.filtered(lambda x: x.escenario == esc):
                saldo += l.flujo_neto
                res.append(round(saldo / 1e6, 2))
            return res

        labels_p = []
        seen = set()
        for l in lineas.filtered(lambda x: x.escenario == 'conservador').sorted('fecha'):
            if l.label not in seen:
                labels_p.append(l.label)
                seen.add(l.label)

        # Punto de continuidad: último valor histórico al inicio de las 3 líneas
        ult = hist[-1] if hist else 0

        self.datos_grafico = json.dumps({
            'labels_hist': labels_h,
            'hist':        hist,
            'labels_proy': ([labels_h[-1]] if labels_h else []) + labels_p,
            'conservador': [ult] + saldos_esc('conservador'),
            'moderado':    [ult] + saldos_esc('moderado'),
            'optimista':   [ult] + saldos_esc('optimista'),
            'burn_promedio': burn_promedio_millones,
        })

    @api.depends('datos_grafico')
    def _compute_grafico_html(self):
        for rec in self:
            if not rec.datos_grafico:
                rec.grafico_html = '<p style="color:#999;padding:16px;">Sin datos — calcule primero las proyecciones.</p>'
                continue
            rec.grafico_html = (
                '<div class="sicone-proyeccion-chart"'
                ' data-record-id="' + str(rec.id) + '"'
                ' style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:12px;">'
                '<div style="height:320px;position:relative;"><canvas class="proy-canvas"></canvas></div>'
                '</div>'
            )

    def get_proyeccion_data(self):
        self.ensure_one()
        if not self.datos_grafico:
            return {}
        import json as _json
        return _json.loads(self.datos_grafico)


class ProyeccionLinea(models.Model):
    _name = 'sicone.proyeccion.linea'
    _description = 'Línea mensual de proyección gerencial'
    _order = 'escenario, fecha'

    proyeccion_id = fields.Many2one('sicone.proyeccion.gerencial', ondelete='cascade')
    escenario = fields.Selection([
        ('conservador', 'Conservador'),
        ('moderado',    'Moderado'),
        ('optimista',   'Optimista'),
    ], string='Escenario')
    anio  = fields.Integer()
    mes   = fields.Integer()
    fecha = fields.Date()
    label = fields.Char(string='Período')

    ingresos_hitos       = fields.Monetary(currency_field='currency_id')
    ingresos_inversiones = fields.Monetary(currency_field='currency_id')
    ingresos_total       = fields.Monetary(currency_field='currency_id')
    egresos_operativos   = fields.Monetary(currency_field='currency_id')
    gastos_fijos         = fields.Monetary(currency_field='currency_id')
    egresos_total        = fields.Monetary(currency_field='currency_id')
    flujo_neto           = fields.Monetary(currency_field='currency_id')
    burn_rate_aplicado   = fields.Monetary(currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency', related='proyeccion_id.currency_id', readonly=True
    )