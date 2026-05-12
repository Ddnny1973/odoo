# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta


class SiconeHito(models.Model):
    """Hitos de pago de un proyecto SICONE"""
    _name = 'sicone.hito'
    _description = 'Hito de Pago SICONE'
    _order = 'proyecto_id, secuencia'

    proyecto_id = fields.Many2one(
        'sicone.proyecto', string='Proyecto',
        required=True, ondelete='cascade'
    )
    secuencia = fields.Integer(string='Secuencia', default=10)
    nombre = fields.Char(string='Hito', required=True)

    contrato_ref = fields.Selection([
        ('c1', 'Contrato 1'),
        ('c2', 'Contrato 2'),
        ('ambos', 'Ambos Contratos'),
    ], string='Contrato', required=True)

    pct_c1 = fields.Float(string='% Contrato 1', digits=(5, 2))
    pct_c2 = fields.Float(string='% Contrato 2', digits=(5, 2))

    monto = fields.Monetary(
        string='Monto Esperado',
        currency_field='currency_id',
        compute='_compute_monto', store=True
    )

    fecha_estimada = fields.Date(
        string='Fecha Estimada',
        compute='_compute_fecha_estimada', store=True
    )

    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('parcial', 'Pago Parcial'),
        ('pagado', 'Pagado'),
    ], string='Estado', default='pendiente')

    cobrado = fields.Monetary(
        string='Total Cobrado',
        currency_field='currency_id',
        compute='_compute_cobrado', store=True
    )

    saldo = fields.Monetary(
        string='Saldo',
        currency_field='currency_id',
        compute='_compute_cobrado', store=True
    )

    pago_ids = fields.One2many(
        'sicone.pago', 'hito_id', string='Pagos'
    )

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    @api.depends('proyecto_id.contrato_ids', 'pct_c1', 'pct_c2', 'contrato_ref')
    def _compute_monto(self):
        for h in self:
            proyecto = h.proyecto_id
            contratos = {c.numero: c for c in proyecto.contrato_ids}
            monto = 0.0
            if h.contrato_ref in ('c1', 'ambos'):
                c1 = contratos.get('1')
                if c1:
                    monto += c1.monto * (h.pct_c1 / 100.0)
            if h.contrato_ref in ('c2', 'ambos'):
                c2 = contratos.get('2')
                if c2:
                    monto += c2.monto * (h.pct_c2 / 100.0)
            h.monto = monto

    @api.depends(
        'proyecto_id.fecha_inicio_estimada',
        'proyecto_id.semanas_admin',
        'proyecto_id.semanas_cimentacion',
        'proyecto_id.semanas_obra_gris',
        'proyecto_id.semanas_cubierta',
        'proyecto_id.semanas_entrega',
        'secuencia'
    )
    def _compute_fecha_estimada(self):
        for h in self:
            p = h.proyecto_id
            if not p.fecha_inicio_estimada:
                h.fecha_estimada = False
                continue
            base = p.fecha_inicio_estimada
            if h.secuencia == 10:
                h.fecha_estimada = base
            elif h.secuencia == 20:
                h.fecha_estimada = base + timedelta(weeks=p.semanas_admin or 0)
            elif h.secuencia == 30:
                h.fecha_estimada = base + timedelta(
                    weeks=(p.semanas_admin or 0) + (p.semanas_cimentacion or 0)
                )
            elif h.secuencia == 40:
                h.fecha_estimada = base + timedelta(
                    weeks=(p.semanas_admin or 0) + (p.semanas_cimentacion or 0) +
                    (p.semanas_obra_gris or 0) + (p.semanas_cubierta or 0) +
                    (p.semanas_entrega or 0)
                )

    @api.depends('pago_ids.monto', 'monto')
    def _compute_cobrado(self):
        TOLERANCIA = 1.0  # $1 de tolerancia para diferencias de redondeo
        for h in self:
            cobrado = sum(h.pago_ids.mapped('monto'))
            saldo = h.monto - cobrado
            h.cobrado = cobrado
            # Redondear saldo a 2 decimales para evitar $0.01 fantasmas
            h.saldo = round(saldo, 2)
            if cobrado <= 0:
                h.estado = 'pendiente'
            elif saldo <= TOLERANCIA:
                # Pagado: cubre el monto o diferencia de redondeo <= $1
                h.estado = 'pagado'
                h.saldo = 0.0
            else:
                h.estado = 'parcial'


class SiconePago(models.Model):
    """Pagos recibidos por hito"""
    _name = 'sicone.pago'
    _description = 'Pago de Hito SICONE'
    _order = 'fecha desc'

    hito_id = fields.Many2one(
        'sicone.hito', string='Hito',
        required=True, ondelete='cascade'
    )
    proyecto_id = fields.Many2one(
        related='hito_id.proyecto_id', store=True
    )
    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    monto = fields.Monetary(string='Monto', currency_field='currency_id', required=True)
    referencia = fields.Char(string='Referencia / Recibo')
    notas = fields.Text(string='Notas')

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )
