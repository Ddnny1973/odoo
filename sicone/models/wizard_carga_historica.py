# -*- coding: utf-8 -*-
"""
WIZARD: Carga Histórica Inicial desde JSON de Streamlit
========================================================
Carga el historial de pagos desde archivos JSON exportados de Streamlit.
Soporta carga simultánea de múltiples archivos (hasta 15 proyectos).

COMPORTAMIENTO:
- Acepta hasta 15 archivos JSON simultáneamente.
- Detecta automáticamente el proyecto de cada archivo.
- Reemplaza movimientos históricos individualmente por proyecto.
- Si un archivo falla, continúa con los demás y reporta errores al final.
- El preview muestra un resumen consolidado de todos los archivos.
"""
import base64
import json
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardCargaHistorica(models.TransientModel):
    _name = 'sicone.wizard.carga.historica'
    _description = 'Carga Histórica Inicial desde JSON'

    # ── Archivos (hasta 15) ───────────────────────────────────────────
    archivo_json_1  = fields.Binary(string='Archivo JSON 1')
    archivo_json_2  = fields.Binary(string='Archivo JSON 2')
    archivo_json_3  = fields.Binary(string='Archivo JSON 3')
    archivo_json_4  = fields.Binary(string='Archivo JSON 4')
    archivo_json_5  = fields.Binary(string='Archivo JSON 5')
    archivo_json_6  = fields.Binary(string='Archivo JSON 6')
    archivo_json_7  = fields.Binary(string='Archivo JSON 7')
    archivo_json_8  = fields.Binary(string='Archivo JSON 8')
    archivo_json_9  = fields.Binary(string='Archivo JSON 9')
    archivo_json_10 = fields.Binary(string='Archivo JSON 10')
    archivo_json_11 = fields.Binary(string='Archivo JSON 11')
    archivo_json_12 = fields.Binary(string='Archivo JSON 12')
    archivo_json_13 = fields.Binary(string='Archivo JSON 13')
    archivo_json_14 = fields.Binary(string='Archivo JSON 14')
    archivo_json_15 = fields.Binary(string='Archivo JSON 15')

    # ── Preview consolidado ───────────────────────────────────────────
    archivos_detectados = fields.Integer(
        string='Archivos detectados', readonly=True
    )
    proyectos_detectados = fields.Char(
        string='Proyectos detectados', readonly=True
    )
    total_pagos = fields.Integer(
        string='Total pagos detectados', readonly=True
    )
    total_monto = fields.Monetary(
        string='Monto total', readonly=True, currency_field='currency_id'
    )
    detalle_preview = fields.Text(
        string='Resumen por archivo', readonly=True
    )
    advertencia = fields.Text(
        string='⚠️ Advertencia', readonly=True
    )

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    def _get_archivos(self):
        """Retorna lista de contenidos b64 para archivos cargados."""
        campos = [
            self.archivo_json_1,  self.archivo_json_2,  self.archivo_json_3,
            self.archivo_json_4,  self.archivo_json_5,  self.archivo_json_6,
            self.archivo_json_7,  self.archivo_json_8,  self.archivo_json_9,
            self.archivo_json_10, self.archivo_json_11, self.archivo_json_12,
            self.archivo_json_13, self.archivo_json_14, self.archivo_json_15,
        ]
        return [c for c in campos if c]

    NOMBRE_MAP = {
        'AVelez':        'Casa Arena - Ana Maria Velez',
        'AZabala':       'Aleandra Zabala',
        'ConsSanJuan':   'Maria Paula Jaramillo - Constructora San Juan',
        'FArroyave':     'Felipe Arroyave',
        'FliaArrerondo': 'Alejandro Arredondo - Dispartes',
        'JCalle':        'Nancy Zapata',
        'JGomez':        'Juan Carlos Gomez',
        'Oasis':         'OASIS',
        'Pletorica':     'Luis Alejandro Castano',
        'Sibaris':       'Fredy Quevedo',
    }

    def _resolver_nombre(self, nombre_json):
        return self.NOMBRE_MAP.get(nombre_json, nombre_json)

    def _leer_json(self, b64):
        contenido = base64.b64decode(b64)
        return json.loads(contenido.decode('utf-8'))

    def _extraer_pagos(self, datos):
        pagos = []
        cartera = datos.get('cartera', {})
        for contrato in cartera.get('contratos_cartera', []):
            num_contrato = contrato.get('numero', '')
            for i, hito in enumerate(contrato.get('hitos', [])):
                nombre_hito = hito.get('nombre', f'Hito {i+1}')
                monto_esperado = hito.get('monto_esperado', 0)
                for pago in hito.get('pagos', []):
                    monto = pago.get('monto', 0)
                    if monto and monto > 0:
                        pagos.append({
                            'fecha': pago.get('fecha', ''),
                            'monto': monto,
                            'referencia': pago.get('referencia', ''),
                            'hito_nombre': nombre_hito,
                            'monto_hito_esperado': monto_esperado,
                            'contrato': num_contrato,
                        })
        return sorted(pagos, key=lambda x: x.get('fecha', ''))

    @api.onchange(
        'archivo_json_1',  'archivo_json_2',  'archivo_json_3',
        'archivo_json_4',  'archivo_json_5',  'archivo_json_6',
        'archivo_json_7',  'archivo_json_8',  'archivo_json_9',
        'archivo_json_10', 'archivo_json_11', 'archivo_json_12',
        'archivo_json_13', 'archivo_json_14', 'archivo_json_15',
    )
    def _onchange_archivos(self):
        archivos = self._get_archivos()
        if not archivos:
            return

        lineas = []
        total_pagos = 0
        total_monto = 0.0
        proyectos_nombres = []
        advertencias = []

        for i, b64 in enumerate(archivos, 1):
            try:
                datos = self._leer_json(b64)
                nombre_json = datos.get('proyecto', {}).get('nombre', f'Archivo {i}')
                nombre_proy = self._resolver_nombre(nombre_json)
                pagos = self._extraer_pagos(datos)
                monto = sum(p['monto'] for p in pagos)
                total_pagos += len(pagos)
                total_monto += monto
                proyectos_nombres.append(nombre_json)

                proyecto = self.env['sicone.proyecto'].search(
                    [('name', 'ilike', nombre_proy)], limit=1
                )
                existentes = 0
                if proyecto:
                    existentes = self.env['sicone.movimiento.contable'].search_count([
                        ('proyecto_id', '=', proyecto.id),
                        ('fuente', '=', 'carga_historica'),
                    ])

                estado = f'✅ {nombre_proy}' if proyecto else f'⚠️ {nombre_proy} (no encontrado)'
                reemplazo = f' — reemplaza {existentes} mov.' if existentes > 0 else ''
                lineas.append(
                    f"{estado}{reemplazo}: {len(pagos)} pagos | ${monto:,.0f}"
                )
                if not proyecto:
                    advertencias.append(f'Proyecto no encontrado: "{nombre_proy}"')

            except Exception as e:
                lineas.append(f'❌ Archivo {i}: Error — {str(e)}')

        self.archivos_detectados = len(archivos)
        self.total_pagos = total_pagos
        self.total_monto = total_monto
        self.proyectos_detectados = ', '.join(proyectos_nombres)
        self.detalle_preview = '\n'.join(lineas)

        if advertencias:
            self.advertencia = (
                '⚠️ Proyectos no encontrados automáticamente:\n' +
                '\n'.join(advertencias) +
                '\n\nEstos archivos serán omitidos en la carga.'
            )
        else:
            self.advertencia = (
                f'✅ {len(archivos)} archivos listos.\n'
                f'Los movimientos históricos existentes de cada proyecto '
                f'serán reemplazados individualmente.'
            )

    def action_cargar(self):
        """Carga múltiples JSONs. Reemplaza por proyecto. Reporta errores al final."""
        archivos = self._get_archivos()
        if not archivos:
            raise UserError('Debe cargar al menos un archivo JSON.')

        exitosos = []
        fallidos = []
        total_movimientos = 0
        total_pagos_aplicados = 0

        for i, b64 in enumerate(archivos, 1):
            try:
                datos = self._leer_json(b64)
                nombre_json = datos.get('proyecto', {}).get('nombre', '')
                nombre_proy = self._resolver_nombre(nombre_json)
                pagos = self._extraer_pagos(datos)

                if not pagos:
                    fallidos.append(f'Archivo {i} ({nombre_json}): sin pagos')
                    continue

                proyecto = self.env['sicone.proyecto'].search(
                    [('name', 'ilike', nombre_proy)], limit=1
                )
                if not proyecto:
                    fallidos.append(
                        f'Archivo {i} ({nombre_json} → {nombre_proy}): proyecto no encontrado'
                    )
                    continue

                hitos = proyecto.hito_ids.sorted('secuencia')
                if not hitos:
                    fallidos.append(f'{nombre_proy}: sin hitos configurados')
                    continue

                # ── Eliminar movimientos históricos previos del proyecto ──
                anteriores = self.env['sicone.movimiento.contable'].search([
                    ('proyecto_id', '=', proyecto.id),
                    ('fuente', '=', 'carga_historica'),
                ])
                n_anteriores = len(anteriores)
                pagos_anteriores = anteriores.mapped('pago_id')
                anteriores.unlink()
                pagos_anteriores.unlink()

                # ── Cargar nuevos movimientos ────────────────────────────
                movimientos_proy = 0
                pagos_proy = 0
                hitos_list = list(hitos)
                cobrado_hito = {h.id: 0.0 for h in hitos}
                indice_hito = 0

                for pago in pagos:
                    monto_restante = pago['monto']
                    fecha_str = pago.get('fecha', '')
                    try:
                        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except Exception:
                        fecha = fields.Date.today()

                    movimiento = self.env['sicone.movimiento.contable'].create({
                        'fecha': fecha,
                        'proyecto_id': proyecto.id,
                        'nombre_cuenta': 'Ingreso de Proyecto (Histórico)',
                        'descripcion': f"Carga histórica: {pago.get('hito_nombre', '')}",
                        'detalle': pago.get('referencia', ''),
                        'tipo': 'ingreso',
                        'categoria': 'ingreso_proyecto',
                        'monto': pago['monto'],
                        'credito': pago['monto'],
                        'fuente': 'carga_historica',
                        'nombre_cc': f"HISTÓRICO - {proyecto.name}",
                    })
                    movimientos_proy += 1

                    while monto_restante > 0 and indice_hito < len(hitos_list):
                        hito = hitos_list[indice_hito]
                        saldo_pendiente = hito.monto - cobrado_hito[hito.id]
                        if saldo_pendiente <= 0:
                            indice_hito += 1
                            continue
                        aplicar = min(monto_restante, saldo_pendiente)
                        cobrado_hito[hito.id] += aplicar
                        monto_restante -= aplicar

                        pago_obj = self.env['sicone.pago'].create({
                            'hito_id': hito.id,
                            'fecha': fecha,
                            'monto': aplicar,
                            'referencia': pago.get('referencia', 'Histórico'),
                            'notas': f"Carga histórica JSON — {pago.get('hito_nombre', '')}",
                        })
                        movimiento.write({
                            'hito_id': hito.id,
                            'pago_id': pago_obj.id,
                        })
                        pagos_proy += 1

                        if cobrado_hito[hito.id] >= hito.monto:
                            indice_hito += 1
                        if monto_restante > 0 and indice_hito < len(hitos_list):
                            continue
                        break

                total_movimientos += movimientos_proy
                total_pagos_aplicados += pagos_proy
                exitosos.append(
                    f'✅ {proyecto.name}: {movimientos_proy} movimientos '
                    f'({n_anteriores} reemplazados)'
                )

            except Exception as e:
                fallidos.append(f'❌ Archivo {i}: Error — {str(e)}')

        msg_partes = [
            f'{len(exitosos)} proyectos cargados.',
            f'Total: {total_movimientos} movimientos, {total_pagos_aplicados} pagos.',
        ]
        if exitosos:
            msg_partes.append('\n'.join(exitosos))
        if fallidos:
            msg_partes.append(f'\n⚠️ {len(fallidos)} errores:\n' + '\n'.join(fallidos))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Carga histórica completada',
                'message': '\n'.join(msg_partes),
                'type': 'success' if not fallidos else 'warning',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
