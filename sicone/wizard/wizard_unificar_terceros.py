# -*- coding: utf-8 -*-
"""
WIZARD: Detección y Unificación de Terceros
=============================================
Escanea los movimientos contables y detecta nombres de terceros
con alta similitud para que el usuario confirme si son el mismo.

UMBRALES:
  >= 85%  → Sugerencia automática (alta confianza)
  70-84%  → Sugerencia manual (requiere confirmación)
  < 70%   → No se muestra (muy diferente)
"""
from difflib import SequenceMatcher
from collections import defaultdict
from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardDeteccionTerceros(models.TransientModel):
    _name = 'sicone.wizard.deteccion.terceros'
    _description = 'Detectar y Unificar Terceros Similares'

    # ── Configuración ─────────────────────────────────────────────
    umbral_auto = fields.Integer(
        string='Umbral auto-sugerencia (%)',
        default=85,
        help='Similitud mínima para marcar como sugerencia automática'
    )
    umbral_manual = fields.Integer(
        string='Umbral revisión manual (%)',
        default=70,
        help='Similitud mínima para mostrar como candidato a revisar'
    )
    solo_sin_canonico = fields.Boolean(
        string='Solo terceros sin canónico',
        default=True,
        help='Ignorar terceros que ya tienen nombre canónico asignado'
    )

    # ── Resultados ────────────────────────────────────────────────
    estado = fields.Selection([
        ('borrador', 'Sin escanear'),
        ('resultados', 'Resultados listos'),
        ('aplicado', 'Unificaciones aplicadas'),
    ], default='borrador')
    total_terceros = fields.Integer(string='Terceros únicos', readonly=True)
    total_grupos = fields.Integer(string='Grupos detectados', readonly=True)
    linea_ids = fields.One2many(
        'sicone.wizard.deteccion.terceros.linea',
        'wizard_id',
        string='Candidatos a unificar'
    )
    resumen = fields.Text(string='Resumen', readonly=True)

    def action_escanear(self):
        """Escanea movimientos y detecta nombres similares"""
        self.ensure_one()

        # Obtener todos los nombres únicos de terceros en movimientos
        self.env.cr.execute("""
            SELECT DISTINCT nombre_tercero, COUNT(*) as freq,
                   SUM(monto) as total
            FROM sicone_movimiento_contable
            WHERE nombre_tercero IS NOT NULL
              AND nombre_tercero != ''
            GROUP BY nombre_tercero
            ORDER BY COUNT(*) DESC
        """)
        terceros_db = self.env.cr.fetchall()  # (nombre, freq, total)

        if not terceros_db:
            raise UserError('No hay terceros en los movimientos contables.')

        nombres = [t[0] for t in terceros_db]
        freq_map = {t[0]: t[1] for t in terceros_db}
        total_map = {t[0]: t[2] for t in terceros_db}

        # Calcular similitudes entre todos los pares
        grupos = []  # [(nombre_a, nombre_b, score)]
        procesados = set()

        for i, nombre_a in enumerate(nombres):
            if nombre_a in procesados:
                continue
            grupo_actual = [nombre_a]
            scores = {}

            for nombre_b in nombres[i+1:]:
                if nombre_b in procesados:
                    continue
                score = SequenceMatcher(
                    None,
                    nombre_a.upper(),
                    nombre_b.upper()
                ).ratio() * 100

                if score >= self.umbral_manual:
                    grupo_actual.append(nombre_b)
                    scores[nombre_b] = round(score)

            if len(grupo_actual) > 1:
                # El nombre con mayor frecuencia es el candidato a canónico
                canonico = max(grupo_actual, key=lambda n: freq_map.get(n, 0))
                for nombre in grupo_actual:
                    if nombre != canonico:
                        grupos.append({
                            'nombre_a': canonico,
                            'nombre_b': nombre,
                            'score': scores.get(nombre, 100),
                            'freq_a': freq_map.get(canonico, 0),
                            'freq_b': freq_map.get(nombre, 0),
                            'total_a': total_map.get(canonico, 0),
                            'total_b': total_map.get(nombre, 0),
                        })
                procesados.update(grupo_actual)

        # Limpiar líneas anteriores
        self.linea_ids.unlink()

        # Crear líneas
        lineas = []
        for g in sorted(grupos, key=lambda x: -x['score']):
            confirmar = g['score'] >= self.umbral_auto
            lineas.append({
                'wizard_id': self.id,
                'nombre_canonico_sugerido': g['nombre_a'],
                'nombre_alias': g['nombre_b'],
                'similitud': g['score'],
                'frecuencia_canonico': g['freq_a'],
                'frecuencia_alias': g['freq_b'],
                'monto_canonico': g['total_a'],
                'monto_alias': g['total_b'],
                'confirmar': confirmar,
                'nivel': 'auto' if confirmar else 'manual',
            })

        if lineas:
            self.env['sicone.wizard.deteccion.terceros.linea'].create(lineas)

        self.write({
            'estado': 'resultados',
            'total_terceros': len(nombres),
            'total_grupos': len(grupos),
            'resumen': (
                f"Se encontraron {len(grupos)} pares similares de {len(nombres)} terceros únicos.\n"
                f"Auto-sugeridos (≥{self.umbral_auto}%): "
                f"{sum(1 for g in grupos if g['score'] >= self.umbral_auto)}\n"
                f"Revisión manual ({self.umbral_manual}-{self.umbral_auto-1}%): "
                f"{sum(1 for g in grupos if self.umbral_manual <= g['score'] < self.umbral_auto)}"
            )
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_aplicar(self):
        """Aplica las unificaciones confirmadas"""
        self.ensure_one()
        lineas_confirmadas = self.linea_ids.filtered(lambda l: l.confirmar)

        if not lineas_confirmadas:
            raise UserError('No hay unificaciones confirmadas. Marque al menos una.')

        aplicados = 0
        creados = 0

        for linea in lineas_confirmadas:
            canonico = linea.nombre_canonico_sugerido.strip()
            alias = linea.nombre_alias.strip()

            # Buscar o crear el tercero canónico
            tercero = self.env['sicone.tercero'].search([
                ('nombre_canonico', '=', canonico)
            ], limit=1)

            if not tercero:
                tercero = self.env['sicone.tercero'].create({
                    'nombre_canonico': canonico,
                    'aliases': alias,
                })
                creados += 1
            else:
                # Agregar alias si no existe
                aliases_actuales = [
                    a.strip() for a in (tercero.aliases or '').split(',')
                    if a.strip()
                ]
                if alias not in aliases_actuales:
                    aliases_actuales.append(alias)
                    tercero.write({'aliases': ', '.join(aliases_actuales)})

            # Actualizar movimientos contables
            movimientos = self.env['sicone.movimiento.contable'].search([
                ('nombre_tercero', '=', alias)
            ])
            if movimientos:
                movimientos.write({'nombre_tercero': canonico})
                aplicados += len(movimientos)

            linea.write({'estado': 'aplicado'})

        self.write({'estado': 'aplicado'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Unificación completada',
                'message': (
                    f"{len(lineas_confirmadas)} aliases unificados.\n"
                    f"{creados} terceros canónicos creados.\n"
                    f"{aplicados} movimientos actualizados."
                ),
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_marcar_todos_auto(self):
        """Confirma todas las sugerencias automáticas"""
        self.linea_ids.filtered(
            lambda l: l.nivel == 'auto'
        ).write({'confirmar': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_desmarcar_todos(self):
        """Desmarca todas las confirmaciones"""
        self.linea_ids.write({'confirmar': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class WizardDeteccionTercerosLinea(models.TransientModel):
    _name = 'sicone.wizard.deteccion.terceros.linea'
    _description = 'Línea de candidato a unificación'
    _order = 'similitud desc'

    wizard_id = fields.Many2one(
        'sicone.wizard.deteccion.terceros',
        ondelete='cascade'
    )
    nombre_canonico_sugerido = fields.Char(
        string='Nombre Canónico (sugerido)',
        readonly=True
    )
    nombre_alias = fields.Char(
        string='Alias (variante)',
        readonly=True
    )
    similitud = fields.Integer(string='Similitud %', readonly=True)
    nivel = fields.Selection([
        ('auto',   'Auto ≥85%'),
        ('manual', 'Revisar 70-84%'),
    ], string='Nivel', readonly=True)
    frecuencia_canonico = fields.Integer(string='Freq. Canónico', readonly=True)
    frecuencia_alias = fields.Integer(string='Freq. Alias', readonly=True)
    monto_canonico = fields.Float(string='Monto Canónico', readonly=True)
    monto_alias = fields.Float(string='Monto Alias', readonly=True)
    confirmar = fields.Boolean(string='Unificar', default=False)
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aplicado',  'Aplicado'),
    ], default='pendiente', readonly=True)


class WizardAlias(models.TransientModel):
    """Wizard simple para agregar alias a un tercero existente"""
    _name = 'sicone.wizard.alias'
    _description = 'Agregar Alias a Tercero'

    tercero_id = fields.Many2one('sicone.tercero', string='Tercero', required=True)
    nuevo_alias = fields.Char(string='Nuevo Alias', required=True)

    def action_agregar(self):
        self.ensure_one()
        t = self.tercero_id
        actuales = [a.strip() for a in (t.aliases or '').split(',') if a.strip()]
        if self.nuevo_alias.strip() not in actuales:
            actuales.append(self.nuevo_alias.strip())
            t.write({'aliases': ', '.join(actuales)})
        return {'type': 'ir.actions.act_window_close'}
