# -*- coding: utf-8 -*-
"""
WIZARD: Carga de Ajustes de Conciliación Inicial
==================================================
Carga los ajustes de conciliación (ingresos/egresos no capturados en el
libro auxiliar) desde el archivo JSON de ajustes iniciales.

COMPORTAMIENTO:
- Elimina TODOS los ajustes existentes antes de cargar los nuevos.
- Puede usarse múltiples veces — siempre reemplaza, nunca acumula.
- El preview se activa con el botón "Previsualizar" después de subir el archivo.

NOTA TÉCNICA — Por qué no se usa @api.onchange:
  En Odoo 18 el decorador @api.onchange sobre campos Binary no se dispara
  automáticamente cuando el usuario sube un archivo. El widget binary asigna
  el valor directamente sin pasar por el mecanismo de onchange del ORM.
  La solución correcta es un botón explícito que el usuario presiona
  después de seleccionar el archivo.
"""
import base64
import json
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardCargaAjustes(models.TransientModel):
    _name = 'sicone.wizard.carga.ajustes'
    _description = 'Carga de Ajustes de Conciliación'

    # ── Archivo ────────────────────────────────────────────────────────
    archivo_json = fields.Binary(
        string='Archivo JSON de Ajustes',
        required=True,
        help='Archivo JSON con ajustes de conciliación '
             '(ajustes_conciliacion_inicial_XXXX.json)'
    )
    archivo_nombre = fields.Char(string='Nombre del archivo')

    # ── Preview ────────────────────────────────────────────────────────
    total_registros = fields.Integer(string='Registros detectados', readonly=True)
    total_ingresos_preview = fields.Monetary(
        string='Total ingresos', readonly=True, currency_field='currency_id'
    )
    total_egresos_preview = fields.Monetary(
        string='Total egresos', readonly=True, currency_field='currency_id'
    )
    periodo = fields.Char(string='Período', readonly=True)
    detalle_preview = fields.Text(string='Detalle de ajustes', readonly=True)

    # ── Estado ─────────────────────────────────────────────────────────
    existentes = fields.Integer(
        string='Registros existentes', readonly=True,
        help='Registros actuales en BD que serán eliminados al cargar.'
    )
    advertencia = fields.Text(string='⚠️ Advertencia', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    def action_preview(self):
        """
        Previsualiza el contenido del JSON antes de cargar.

        En Odoo 18 el @api.onchange sobre campos Binary no se dispara
        automáticamente al subir un archivo — el widget binary asigna
        el valor directamente sin pasar por el mecanismo de onchange.
        Por eso se usa este botón explícito que el usuario presiona
        después de seleccionar el archivo.
        """
        self.ensure_one()
        if not self.archivo_json:
            raise UserError('Selecciona un archivo JSON antes de previsualizar.')
        try:
            datos = self._leer_json()
            if not isinstance(datos, list):
                self.advertencia = 'El archivo no tiene el formato esperado (debe ser una lista).'
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name, 'res_id': self.id,
                    'view_mode': 'form', 'target': 'new',
                }

            self.total_registros = len(datos)
            self.total_ingresos_preview = sum(
                r.get('monto', 0) for r in datos if r.get('tipo') == 'Ingreso'
            )
            self.total_egresos_preview = sum(
                r.get('monto', 0) for r in datos if r.get('tipo') == 'Egreso'
            )

            # Período
            fechas = [r.get('fecha', '') for r in datos if r.get('fecha')]
            if fechas:
                self.periodo = f"{min(fechas)} → {max(fechas)}"

            # Detalle línea por línea
            lineas = []
            for r in datos:
                emoji = '📈' if r.get('tipo') == 'Ingreso' else '📉'
                lineas.append(
                    f"{emoji} {r.get('fecha','')} | "
                    f"${r.get('monto', 0):,.0f} | "
                    f"{r.get('concepto', '')[:60]}"
                )
            self.detalle_preview = '\n'.join(lineas)

            # Advertencia según existentes
            existentes = self.env['sicone.ajuste.conciliacion'].search_count([
                ('company_id', '=', self.env.company.id),
            ])
            self.existentes = existentes
            if existentes > 0:
                self.advertencia = (
                    f'⚠️ ATENCIÓN: Existen {existentes} ajustes actualmente en el sistema.\n'
                    f'Al confirmar la carga, TODOS serán eliminados y reemplazados\n'
                    f'por los {len(datos)} registros del archivo.'
                )
            else:
                self.advertencia = (
                    f'Se cargarán {len(datos)} ajustes de conciliación.\n'
                    f'Ingresos: ${self.total_ingresos_preview:,.0f} | '
                    f'Egresos: ${self.total_egresos_preview:,.0f}'
                )

        except Exception as e:
            self.advertencia = f'Error al leer el archivo: {str(e)}'

        # Reabrir el mismo wizard para mostrar el preview actualizado
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _leer_json(self):
        contenido = base64.b64decode(self.archivo_json)
        return json.loads(contenido.decode('utf-8'))

    def action_cargar(self):
        """
        Importa los ajustes de conciliación desde el JSON.
        SIEMPRE elimina los registros existentes antes de cargar los nuevos.
        """
        self.ensure_one()

        datos = self._leer_json()
        if not isinstance(datos, list) or not datos:
            raise UserError('No se encontraron ajustes válidos en el archivo.')

        # ── Calcular totales desde el JSON (no depender del preview) ──
        total_ingresos = sum(
            r.get('monto', 0) for r in datos if r.get('tipo') == 'Ingreso'
        )
        total_egresos = sum(
            r.get('monto', 0) for r in datos if r.get('tipo') == 'Egreso'
        )
        n_ingresos = sum(1 for r in datos if r.get('tipo') == 'Ingreso')
        n_egresos  = sum(1 for r in datos if r.get('tipo') == 'Egreso')

        # ── Eliminar registros existentes ──────────────────────────────
        anteriores = self.env['sicone.ajuste.conciliacion'].search([
            ('company_id', '=', self.company_id.id),
        ])
        n_eliminados = len(anteriores)
        anteriores.unlink()

        # ── Mapeos ────────────────────────────────────────────────────
        tipo_map = {'Ingreso': 'ingreso', 'Egreso': 'egreso'}
        cuenta_map = {
            'Cuenta Bancaria': 'banco',
            'Fiducuenta': 'fiducuenta',
        }

        # ── Crear registros nuevos ────────────────────────────────────
        creados = 0
        for r in datos:
            tipo_odoo = tipo_map.get(r.get('tipo'), 'egreso')
            cuenta_odoo = cuenta_map.get(r.get('cuenta'), 'banco')

            fecha = None
            fecha_str = r.get('fecha')
            if fecha_str:
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except Exception:
                    pass

            self.env['sicone.ajuste.conciliacion'].create({
                'concepto':      r.get('concepto', 'Sin concepto'),
                'categoria':     r.get('categoria', ''),
                'cuenta':        cuenta_odoo,
                'tipo_registro': 'puntual',
                'tipo':          tipo_odoo,
                'fecha':         fecha,
                'monto':         r.get('monto', 0),
                'observaciones': r.get('observaciones', ''),
                'evidencia':     r.get('evidencia', ''),
                'company_id':    self.company_id.id,
            })
            creados += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Ajustes cargados correctamente',
                'message': (
                    f'{n_eliminados} registros anteriores eliminados.\n'
                    f'{creados} ajustes cargados: '
                    f'{n_ingresos} ingresos (${total_ingresos:,.0f}) | '
                    f'{n_egresos} egresos (${total_egresos:,.0f})'
                ),
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
