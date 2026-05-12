# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from collections import defaultdict


MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}


class ProyectoSicone(models.Model):
    """
    Modelo principal para Proyectos SICONE
    Contiene la información general de cada proyecto de construcción
    """
    _name = 'sicone.proyecto'
    _description = 'Proyecto de Construcción SICONE'
    _inherit = []
    _order = 'fecha_creacion desc'

    # ============================================================================
    # CAMPOS BÁSICOS
    # ============================================================================

    name = fields.Char(
        string='Nombre del Proyecto', required=True, tracking=True,
        help='Nombre identificador del proyecto de construcción'
    )
    codigo = fields.Char(
        string='Código', readonly=True, copy=False,
        help='Código único autogenerado para el proyecto'
    )
    active = fields.Boolean(string='Activo', default=True, tracking=True)

    # ============================================================================
    # INFORMACIÓN DEL CLIENTE
    # ============================================================================

    partner_id = fields.Many2one(
        'res.partner', string='Contacto Principal', required=True, tracking=True,
        help='Contacto o empresa principal asociada al proyecto.'
    )

    # ============================================================================
    # DATOS TÉCNICOS
    # ============================================================================

    area_base = fields.Float(string='Área Base (m²)', digits=(12, 2), tracking=True)
    area_cubierta = fields.Float(string='Área Cubierta (m²)', digits=(12, 2), tracking=True)
    area_entrepiso = fields.Float(string='Área Entrepiso (m²)', digits=(12, 2), tracking=True)
    descripcion = fields.Text(string='Descripción del Proyecto', tracking=True)

    # ============================================================================
    # ESTADO Y FECHAS
    # ============================================================================

    estado = fields.Selection([
        ('prospecto', 'Prospecto'),
        ('cotizacion', 'En Cotización'),
        ('negociacion', 'En Negociación'),
        ('contratado', 'Contratado'),
        ('ejecucion', 'En Ejecución'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ], string='Estado', default='prospecto', required=True, tracking=True)

    fecha_creacion = fields.Datetime(
        string='Fecha de Creación', default=fields.Datetime.now, readonly=True
    )
    fecha_inicio_estimada = fields.Date(
        string='Fecha Inicio (Firma Contrato)', tracking=True,
        help='Fecha de firma del contrato. Se pre-llena con la fecha actual '
             'al crear el proyecto y puede ajustarse manualmente.'
    )
    fecha_fin_estimada = fields.Date(
        string='Fecha Fin Estimada', tracking=True,
        help='Calculada automáticamente desde fecha inicio + semanas de fases. Editable.'
    )

    # Duración de fases en semanas
    semanas_admin = fields.Integer(string='Semanas Adm. y Diseños', default=16)
    semanas_cimentacion = fields.Integer(string='Semanas Cimentación', default=10)
    semanas_obra_gris = fields.Integer(string='Semanas Obra Gris', default=16)
    semanas_cubierta = fields.Integer(string='Semanas Cubierta', default=4)
    semanas_entrega = fields.Integer(string='Semanas Entrega', default=2)

    # ============================================================================
    # RELACIONES
    # ============================================================================

    hito_ids = fields.One2many('sicone.hito', 'proyecto_id', string='Hitos')
    cotizacion_id = fields.Many2one('sicone.cotizacion', string='Cotización de Origen', readonly=True)
    contrato_ids = fields.One2many('sicone.contrato', 'proyecto_id', string='Contratos')
    contrato_count = fields.Integer(compute='_compute_contrato_count', string='N° Contratos')
    cashflow_ids = fields.One2many('sicone.proyecto.cashflow', 'proyecto_id', string='Cash Flow Mensual')

    # ============================================================================
    # RESUMEN FINANCIERO
    # ============================================================================

    monto_contrato1 = fields.Monetary(
        string='Contrato 1 - Obra Gris', compute='_compute_resumen_financiero',
        currency_field='currency_id', store=True,
    )
    monto_contrato2 = fields.Monetary(
        string='Contrato 2 - Cim./Compl.', compute='_compute_resumen_financiero',
        currency_field='currency_id', store=True,
    )
    monto_total_proyecto = fields.Monetary(
        string='Total Proyecto', compute='_compute_resumen_financiero',
        currency_field='currency_id', store=True,
    )
    total_cobrado_proyecto = fields.Monetary(
        string='Total Cobrado', compute='_compute_resumen_financiero',
        currency_field='currency_id', store=True,
    )
    saldo_pendiente_proyecto = fields.Monetary(
        string='Saldo Pendiente', compute='_compute_resumen_financiero',
        currency_field='currency_id', store=True,
    )

    # ============================================================================
    # KPIs DE CASH FLOW
    # ============================================================================

    cf_saldo_actual = fields.Monetary(
        string='Saldo Actual', compute='_compute_kpi_cashflow',
        currency_field='currency_id',
        help='Ingresos reales − egresos reales acumulados'
    )
    cf_burn_rate_semanal = fields.Monetary(
        string='Burn Rate Semanal', compute='_compute_kpi_cashflow',
        currency_field='currency_id',
        help='Promedio de egresos semanales en las últimas 8 semanas'
    )
    cf_runway_semanas = fields.Float(
        string='Runway (semanas)', compute='_compute_kpi_cashflow', digits=(6, 1),
        help='Semanas que puede operar el proyecto sin nuevos ingresos'
    )
    cf_margen_proteccion = fields.Monetary(
        string='Margen de Protección', compute='_compute_kpi_cashflow',
        currency_field='currency_id',
        help='Burn rate × 8 semanas — monto mínimo recomendado en caja'
    )
    cf_excedente_invertible = fields.Monetary(
        string='Excedente Invertible', compute='_compute_kpi_cashflow',
        currency_field='currency_id',
        help='Saldo actual − margen de protección'
    )

    # ============================================================================
    # CONTROL
    # ============================================================================

    usuario_creacion_id = fields.Many2one(
        'res.users', string='Creado por',
        default=lambda self: self.env.user, readonly=True
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.company, required=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )
    notas = fields.Text(string='Notas Internas')

    # ============================================================================
    # MÉTODOS COMPUTE
    # ============================================================================

    @api.depends('contrato_ids')
    def _compute_contrato_count(self):
        for proyecto in self:
            proyecto.contrato_count = len(proyecto.contrato_ids)

    @api.depends('contrato_ids.monto', 'hito_ids.cobrado', 'hito_ids.monto')
    def _compute_resumen_financiero(self):
        for proyecto in self:
            contratos = {c.numero: c for c in proyecto.contrato_ids}
            c1 = contratos.get('1')
            c2 = contratos.get('2')
            proyecto.monto_contrato1 = c1.monto if c1 else 0.0
            proyecto.monto_contrato2 = c2.monto if c2 else 0.0
            proyecto.monto_total_proyecto = proyecto.monto_contrato1 + proyecto.monto_contrato2
            proyecto.total_cobrado_proyecto = sum(proyecto.hito_ids.mapped('cobrado'))
            proyecto.saldo_pendiente_proyecto = (
                proyecto.monto_total_proyecto - proyecto.total_cobrado_proyecto
            )

    @api.depends('cashflow_ids.saldo_acumulado', 'cashflow_ids.burn_rate_semanal',
                 'cashflow_ids.runway_semanas', 'cashflow_ids.margen_proteccion',
                 'cashflow_ids.excedente_invertible')
    def _compute_kpi_cashflow(self):
        """Lee los KPIs del último mes calculado en el cash flow"""
        for proyecto in self:
            ultimo = proyecto.cashflow_ids.sorted(
                lambda r: (r.anio, r.mes), reverse=True
            )[:1]
            if ultimo:
                proyecto.cf_saldo_actual = ultimo.saldo_acumulado
                proyecto.cf_burn_rate_semanal = ultimo.burn_rate_semanal
                proyecto.cf_runway_semanas = ultimo.runway_semanas
                proyecto.cf_margen_proteccion = ultimo.margen_proteccion
                proyecto.cf_excedente_invertible = ultimo.excedente_invertible
            else:
                proyecto.cf_saldo_actual = 0.0
                proyecto.cf_burn_rate_semanal = 0.0
                proyecto.cf_runway_semanas = 0.0
                proyecto.cf_margen_proteccion = 0.0
                proyecto.cf_excedente_invertible = 0.0

    # ============================================================================
    # ONCHANGE
    # ============================================================================

    @api.onchange('fecha_inicio_estimada', 'semanas_admin', 'semanas_cimentacion',
                  'semanas_obra_gris', 'semanas_cubierta', 'semanas_entrega')
    def _onchange_calcular_fecha_fin(self):
        """Recalcula fecha_fin_estimada cuando cambia fecha inicio o semanas de fases"""
        if self.fecha_inicio_estimada:
            total_semanas = (
                (self.semanas_admin or 0) + (self.semanas_cimentacion or 0) +
                (self.semanas_obra_gris or 0) + (self.semanas_cubierta or 0) +
                (self.semanas_entrega or 0)
            )
            self.fecha_fin_estimada = self.fecha_inicio_estimada + timedelta(weeks=total_semanas)

    # ============================================================================
    # CRUD Y CONSTRAINTS
    # ============================================================================

    @api.model
    def create(self, vals):
        if not vals.get('codigo'):
            vals['codigo'] = self.env['ir.sequence'].next_by_code('sicone.proyecto') or 'PROY/NEW'
        if not vals.get('fecha_inicio_estimada'):
            vals['fecha_inicio_estimada'] = fields.Date.today()
        if not vals.get('fecha_fin_estimada') and vals.get('fecha_inicio_estimada'):
            fi = vals['fecha_inicio_estimada']
            if isinstance(fi, str):
                from datetime import datetime
                fi = datetime.strptime(fi, '%Y-%m-%d').date()
            total_semanas = (
                int(vals.get('semanas_admin', 16)) + int(vals.get('semanas_cimentacion', 10)) +
                int(vals.get('semanas_obra_gris', 16)) + int(vals.get('semanas_cubierta', 4)) +
                int(vals.get('semanas_entrega', 2))
            )
            vals['fecha_fin_estimada'] = fi + timedelta(weeks=total_semanas)
        return super(ProyectoSicone, self).create(vals)

    @api.constrains('area_base', 'area_cubierta', 'area_entrepiso')
    def _check_areas(self):
        for proyecto in self:
            if proyecto.area_base and proyecto.area_base < 0:
                raise ValidationError('El área base no puede ser negativa')
            if proyecto.area_cubierta and proyecto.area_cubierta < 0:
                raise ValidationError('El área cubierta no puede ser negativa')
            if proyecto.area_entrepiso and proyecto.area_entrepiso < 0:
                raise ValidationError('El área entrepiso no puede ser negativa')

    @api.constrains('fecha_inicio_estimada', 'fecha_fin_estimada')
    def _check_fechas(self):
        for proyecto in self:
            if proyecto.fecha_inicio_estimada and proyecto.fecha_fin_estimada:
                if proyecto.fecha_fin_estimada < proyecto.fecha_inicio_estimada:
                    raise ValidationError('La fecha fin debe ser posterior a la fecha inicio')

    # ============================================================================
    # GESTIÓN DE ESTADO DEL PROYECTO
    # ============================================================================

    def action_finalizar_proyecto(self):
        """
        Marca el proyecto como Finalizado.
        Solo aplica desde En Ejecución.
        El tracking registra automáticamente el cambio de estado y el usuario.
        """
        for rec in self:
            if rec.estado != 'ejecucion':
                raise UserError('Solo se pueden finalizar proyectos En Ejecución.')
            rec.estado = 'finalizado'

    def action_reactivar_proyecto(self):
        """
        Reactiva un proyecto Finalizado o Cancelado a En Ejecución.
        Permite corregir un cierre prematuro o retomar un proyecto cancelado.
        """
        for rec in self:
            if rec.estado not in ('finalizado', 'cancelado'):
                raise UserError('Solo se pueden reactivar proyectos Finalizados o Cancelados.')
            rec.estado = 'ejecucion'

    def action_cancelar_proyecto(self):
        """
        Cancela un proyecto Contratado o En Ejecución.
        El proyecto puede reactivarse posteriormente si es necesario.
        """
        for rec in self:
            if rec.estado not in ('contratado', 'ejecucion'):
                raise UserError('Solo se pueden cancelar proyectos Contratados o En Ejecución.')
            rec.estado = 'cancelado'

    # ============================================================================
    # CASH FLOW — Recálculo mensual
    # ============================================================================

    def action_recalcular_cashflow(self):
        """
        Recalcula el cash flow mensual del proyecto desde sus movimientos contables.

        INGRESOS: solo fuente='carga_historica' para evitar duplicar FVs del libro auxiliar.
        BURN RATE: promedio móvil de las últimas 8 semanas con egresos hasta cada mes.
        RUNWAY: saldo_acumulado / burn_rate_semanal.
        MARGEN DE PROTECCIÓN: burn_rate_semanal × 8.
        EXCEDENTE INVERTIBLE: max(0, saldo_acumulado - margen_proteccion).
        """
        self.ensure_one()

        movimientos = self.env['sicone.movimiento.contable'].search([
            ('proyecto_id', '=', self.id)
        ])

        if not movimientos:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin datos',
                    'message': 'No hay movimientos contables para este proyecto.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        meses = defaultdict(lambda: {
            'ingresos': 0.0, 'egresos': 0.0,
            'materiales': 0.0, 'mano_obra': 0.0,
            'variables': 0.0, 'admin': 0.0, 'fijos': 0.0,
        })
        semanas_egresos = defaultdict(float)

        for mov in movimientos:
            key = (mov.fecha.year, mov.fecha.month)
            if mov.tipo == 'ingreso' and mov.fuente == 'carga_historica':
                meses[key]['ingresos'] += mov.monto
            elif mov.tipo == 'egreso':
                meses[key]['egresos'] += mov.monto
                cat = mov.categoria or ''
                meses[key]['materiales'] += mov.monto if cat == 'materiales' else 0
                meses[key]['mano_obra'] += mov.monto if cat == 'mano_obra' else 0
                meses[key]['variables'] += mov.monto if cat == 'variables' else 0
                meses[key]['admin'] += mov.monto if cat == 'administracion' else 0
                meses[key]['fijos'] += mov.monto if cat == 'gasto_fijo' else 0
                semana = mov.fecha - timedelta(days=mov.fecha.weekday())
                semanas_egresos[semana] += mov.monto

        if not meses:
            return

        meses_ord = sorted(meses.keys())
        semanas_ord = sorted(semanas_egresos.keys())
        saldo_acum = 0.0
        registros = []

        for anio, mes in meses_ord:
            d = meses[(anio, mes)]
            saldo_acum += d['ingresos'] - d['egresos']

            ultimo_dia = date(anio, mes, 28)
            ventana = [s for s in semanas_ord if s <= ultimo_dia][-8:]
            burn_rate = (
                sum(semanas_egresos[s] for s in ventana) / len(ventana)
                if ventana else 0.0
            )
            margen = burn_rate * 8
            runway = saldo_acum / burn_rate if burn_rate > 0 else 0.0
            excedente = max(0.0, saldo_acum - margen)

            registros.append({
                'proyecto_id': self.id,
                'anio': anio,
                'mes': mes,
                'fase': self._get_fase_del_mes(anio, mes),
                'ingresos': d['ingresos'],
                'egresos': d['egresos'],
                'saldo_acumulado': saldo_acum,
                'burn_rate_semanal': burn_rate,
                'runway_semanas': runway,
                'margen_proteccion': margen,
                'excedente_invertible': excedente,
                'egresos_materiales': d['materiales'],
                'egresos_mano_obra': d['mano_obra'],
                'egresos_variables': d['variables'],
                'egresos_admin': d['admin'],
                'egresos_fijos': d['fijos'],
                'company_id': self.company_id.id,
            })

        self.cashflow_ids.unlink()
        self.env['sicone.proyecto.cashflow'].create(registros)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sicone.proyecto',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_fase_del_mes(self, anio, mes):
        """Fase predominante del proyecto en un mes dado, por semanas configuradas"""
        if not self.fecha_inicio_estimada:
            return ''
        fi = self.fecha_inicio_estimada
        semanas_transcurridas = (date(anio, mes, 1) - fi).days / 7.0
        acum = 0
        for nombre, semanas in [
            ('Adm. y Diseños', self.semanas_admin or 16),
            ('Cimentación',    self.semanas_cimentacion or 10),
            ('Obra Gris',      self.semanas_obra_gris or 16),
            ('Cubierta',       self.semanas_cubierta or 4),
            ('Entrega',        self.semanas_entrega or 2),
        ]:
            acum += semanas
            if semanas_transcurridas <= acum:
                return nombre
        return 'Finalizado'

    def _compute_display_name(self):
        for proyecto in self:
            partner = proyecto.partner_id.display_name if proyecto.partner_id else ''
            name = f"[{proyecto.codigo}] {proyecto.name}" if proyecto.codigo else proyecto.name or ''
            if partner:
                name = f"{name} - {partner}"
            proyecto.display_name = name


# ==============================================================================
# MODELO: Cash Flow Mensual por Proyecto
# ==============================================================================

class ProyectoCashflow(models.Model):
    """
    Resumen mensual de cash flow por proyecto.
    Generado por action_recalcular_cashflow en sicone.proyecto.
    """
    _name = 'sicone.proyecto.cashflow'
    _description = 'Cash Flow Mensual del Proyecto'
    _order = 'proyecto_id, anio, mes'

    proyecto_id = fields.Many2one(
        'sicone.proyecto', string='Proyecto',
        required=True, ondelete='cascade', index=True
    )
    anio = fields.Integer(string='Año', required=True)
    mes = fields.Integer(string='Mes', required=True)
    nombre_mes = fields.Char(string='Período', compute='_compute_nombre_mes', store=True)
    fase = fields.Char(string='Fase')

    ingresos = fields.Monetary(string='Ingresos', currency_field='currency_id')
    egresos = fields.Monetary(string='Egresos', currency_field='currency_id')
    flujo_neto = fields.Monetary(
        string='Flujo Neto', compute='_compute_flujo_neto',
        store=True, currency_field='currency_id'
    )
    saldo_acumulado = fields.Monetary(string='Saldo Acumulado', currency_field='currency_id')

    burn_rate_semanal = fields.Monetary(
        string='Burn Rate Semanal', currency_field='currency_id',
        help='Promedio de egresos de las últimas 8 semanas'
    )
    runway_semanas = fields.Float(string='Runway (sem.)', digits=(6, 1))
    margen_proteccion = fields.Monetary(
        string='Margen Protección', currency_field='currency_id',
        help='Burn rate × 8 semanas'
    )
    excedente_invertible = fields.Monetary(
        string='Excedente Invertible', currency_field='currency_id',
        help='Saldo acumulado − margen de protección'
    )

    egresos_materiales = fields.Monetary(string='Materiales', currency_field='currency_id')
    egresos_mano_obra = fields.Monetary(string='Mano de Obra', currency_field='currency_id')
    egresos_variables = fields.Monetary(string='Variables', currency_field='currency_id')
    egresos_admin = fields.Monetary(string='Administración', currency_field='currency_id')
    egresos_fijos = fields.Monetary(string='Gastos Fijos', currency_field='currency_id')

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

    @api.depends('ingresos', 'egresos')
    def _compute_flujo_neto(self):
        for rec in self:
            rec.flujo_neto = rec.ingresos - rec.egresos


# ==============================================================================
# MODELO: Contrato
# ==============================================================================

class SiconeContrato(models.Model):
    """Contratos generados al aceptar una cotización"""
    _name = 'sicone.contrato'
    _description = 'Contrato SICONE'
    _inherit = []
    _order = 'proyecto_id, numero'

    proyecto_id = fields.Many2one(
        'sicone.proyecto', string='Proyecto',
        required=True, ondelete='cascade', tracking=True
    )
    cotizacion_id = fields.Many2one(
        'sicone.cotizacion', string='Cotización',
        required=True, ondelete='restrict', tracking=True
    )
    numero = fields.Selection([
        ('1', 'Contrato 1 - Obra Gris'),
        ('2', 'Contrato 2 - Cimentación y Complementarios'),
    ], string='Contrato', required=True)

    name = fields.Char(string='Nombre', compute='_compute_name', store=True)
    monto = fields.Monetary(string='Monto', currency_field='currency_id', tracking=True)
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('activo', 'Activo'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ], string='Estado', default='activo', tracking=True)

    fecha_inicio = fields.Date(string='Fecha Inicio', tracking=True)
    fecha_fin_estimada = fields.Date(string='Fecha Fin Estimada', tracking=True)
    notas = fields.Text(string='Notas')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    @api.depends('numero', 'proyecto_id')
    def _compute_name(self):
        for c in self:
            nombres = {
                '1': 'Contrato 1 - Obra Gris',
                '2': 'Contrato 2 - Cimentación y Complementarios'
            }
            c.name = f"{nombres.get(c.numero, '')} — {c.proyecto_id.name or ''}"
