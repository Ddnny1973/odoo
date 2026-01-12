from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import date


class AccountMoveLine(models.Model):
    """Extensión de líneas de factura para incluir coeficiente de apartamento"""
    _inherit = 'account.move.line'

    coeficiente = fields.Float(
        string='Coeficiente',
        help='Coeficiente de participación del apartamento',
        digits=(16, 5),
        compute='_compute_gc_coeficiente',
        store=True,
        readonly=True,
    )
    
    gc_multa_id = fields.Many2one(
        'gc.multas',
        string='Multa Facturada',
        readonly=True,
        help='Multa asociada a esta línea de factura (si aplica)',
    )
    
    @api.depends('move_id.apartamento_id', 'move_id.apartamento_id.coeficiente', 'move_id.invoice_date', 'product_id')
    def _compute_gc_coeficiente(self):
        ValoresConceptos = self.env['gc.valores_conceptos']
        hoy = date.today()
        for line in self:
            coef = 0.0
            if not line.move_id or not line.move_id.apartamento_id or not line.product_id:
                line.coeficiente = 0.0
                continue

            fecha_ref = line.move_id.invoice_date or hoy
            valor_concepto = ValoresConceptos.search([
                ('producto_id', '=', line.product_id.id),
                ('activo', '=', True),
                ('fecha_inicial', '<=', fecha_ref),
                '|',
                ('fecha_final', '=', False),
                ('fecha_final', '>=', fecha_ref),
            ], limit=1, order='fecha_inicial desc')

            if valor_concepto and valor_concepto.usar_coeficiente:
                coef = line.move_id.apartamento_id.coeficiente or 0.0
            line.coeficiente = coef

    @api.onchange('product_id')
    def _onchange_product_id_gc(self):
        """
        Al seleccionar un producto manualmente en la línea de la factura:
        Busca si el producto tiene una configuración en gc.valores_conceptos
        para aplicar el coeficiente y el monto automáticamente.
        """
        # Solo actuar en facturas de cliente
        if not self.product_id or self.move_id.move_type not in ('out_invoice', 'out_refund'):
            return

        # En autosave/cambios de pestaña Odoo puede evaluar onchanges con el move aún incompleto.
        # No borrar coeficientes existentes por falta temporal de apartamento en cache.
        if not self.move_id.apartamento_id:
            return

        # Buscar la configuración vigente para este producto
        # Priorizamos el registro más reciente que esté activo
        fecha_ref = self.move_id.invoice_date or date.today()
        valor_concepto = self.env['gc.valores_conceptos'].search([
            ('producto_id', '=', self.product_id.id),
            ('activo', '=', True),
            ('fecha_inicial', '<=', fecha_ref),
            '|',
            ('fecha_final', '=', False),
            ('fecha_final', '>=', fecha_ref),
        ], limit=1, order='fecha_inicial desc')

        if valor_concepto:
            coef = self.move_id.apartamento_id.coeficiente

            # Aplicar configuración de coeficiente
            if valor_concepto.usar_coeficiente:
                self.price_unit = valor_concepto.monto * coef
            else:
                self.price_unit = valor_concepto.monto
        else:
            # Si el producto no está en la tabla de conceptos, 
            # podemos optar por poner coeficiente 0 o el del apartamento
            # Por seguridad, lo dejamos en 0 si no es un concepto predefinido
            return


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Campo para seleccionar el apartamento
    apartamento_id = fields.Many2one(
        comodel_name='gc.apartamento',
        string='Apartamento',
        help='Seleccione el apartamento para esta factura',
        tracking=True,
        domain=[('active', '=', True)],
    )

    # Campo para mostrar propietarios adicionales (solo informativo)
    propietarios_adicionales_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='account_move_propietarios_adicionales_rel',
        column1='move_id',
        column2='partner_id',
        string='Propietarios Adicionales',
        help='Otros propietarios del apartamento (solo información)',
        readonly=True,
    )

    @api.onchange('apartamento_id', 'invoice_date')
    def _onchange_apartamento_o_fecha(self):
        """
        Evento unificado para manejar cambios en apartamento o fecha.
        Sincroniza propietarios y genera líneas de cobro recurrentes.
        """
        if self.move_type not in ('out_invoice', 'out_refund'):
            return

        # 1. Sincronizar propietarios si hay apartamento
        if self.apartamento_id:
            propietarios = self.apartamento_id.propietario_ids
            
            if not propietarios:
                # Si el apartamento no tiene propietarios, limpiar campos y advertir
                self.propietarios_adicionales_ids = [Command.clear()]
                return {
                    'warning': {
                        'title': 'Apartamento sin Propietarios',
                        'message': f'El apartamento {self.apartamento_id.display_name} no tiene propietarios asignados. Por favor, asigne al menos un propietario.',
                    }
                }
            
            # Establecer el primer propietario como cliente principal
            if self.partner_id != propietarios[0]:
                self.partner_id = propietarios[0]
            
            # Sincronizar propietarios adicionales
            propietarios_adicionales = propietarios[1:]
            if set(self.propietarios_adicionales_ids.ids) != set(propietarios_adicionales.ids):
                self.propietarios_adicionales_ids = [Command.set(propietarios_adicionales.ids)]
            
            # 2. Generar/ajustar líneas en borrador (idempotente, no duplica)
            if self.invoice_date and self.state == 'draft':
                self._crear_lineas_conceptos()
        else:
            # Si se limpia el apartamento, limpiar también propietarios adicionales
            self.propietarios_adicionales_ids = [Command.clear()]

    def _crear_lineas_conceptos(self):
        """
        Genera/actualiza las líneas de factura basadas en conceptos recurrentes y multas.
        Importante: debe ser idempotente para que autosave/cambio de pestaña no duplique líneas.
        """
        if not self.apartamento_id or not self.invoice_date:
            return

        if self.state != 'draft':
            return
        
        # Buscar valores recurrentes y activos que sean vigentes en la fecha
        valores_conceptos = self.env['gc.valores_conceptos'].search([
            ('recurrente', '=', True),
            ('activo', '=', True),
            ('fecha_inicial', '<=', self.invoice_date),
            '|',
            ('fecha_final', '=', False),
            ('fecha_final', '>=', self.invoice_date),
        ], order='fecha_inicial desc')
        
        # Preparar datos deseados
        datos_lineas_recurrentes_por_producto = {}
        datos_lineas_multas = []
        coef = self.apartamento_id.coeficiente
        
        # 1. PROCESAR CONCEPTOS RECURRENTES
        productos_vigentes = {}
        for valor in valores_conceptos:
            producto_id = valor.producto_id.id
            if producto_id not in productos_vigentes:
                productos_vigentes[producto_id] = valor
        
        for valor in productos_vigentes.values():
            # Calcular precio: monto * coeficiente o monto fijo según configuración
            if valor.usar_coeficiente:
                precio_unit = valor.monto * coef
            else:
                precio_unit = valor.monto
            
            # Solo añadir si el precio es mayor a 0
            if precio_unit > 0:
                datos_lineas_recurrentes_por_producto[valor.producto_id.id] = {
                    'product_id': valor.producto_id.id,
                    'quantity': 1.0,
                    'price_unit': precio_unit,
                    'name': valor.producto_id.name,
                }
        
        # 2. PROCESAR MULTAS DEL MISMO MES (gc.multas)
        # Buscar multas no facturadas del mismo mes/año que la factura
        primer_dia_mes = self.invoice_date.replace(day=1)
        if self.invoice_date.month == 12:
            ultimo_dia_mes = self.invoice_date.replace(year=self.invoice_date.year + 1, month=1, day=1)
        else:
            ultimo_dia_mes = self.invoice_date.replace(month=self.invoice_date.month + 1, day=1)
        
        # Buscar multas pendientes (no facturadas) del mismo mes que la factura
        multas = self.env['gc.multas'].search([
            ('num_apartamento_id', '=', self.apartamento_id.id),
            ('estado', '=', 'pendiente'),  # Solo multas pendientes
            ('fecha_multa', '>=', primer_dia_mes),
            ('fecha_multa', '<', ultimo_dia_mes),
        ])
        
        for multa in multas:
            if multa.monto_multa > 0:
                datos_lineas_multas.append({
                    'product_id': multa.concepto_multa.id,
                    'quantity': 1.0,
                    'price_unit': multa.monto_multa,
                    'name': f'{multa.concepto_multa.name} - Multa ({multa.fecha_multa})',
                    'gc_multa_id': multa.id,  # Guardar referencia a la multa
                })

        # --- Aplicar de forma idempotente ---
        line_model = self.env['account.move.line']

        # 1) Recurrentes: actualizar si ya existe línea del producto, crear si no.
        for product_id, datos in datos_lineas_recurrentes_por_producto.items():
            # Preferimos actualizar líneas "simples" del producto (name exacto) si existen.
            existente = self.invoice_line_ids.filtered(
                lambda l: l.product_id.id == product_id and (l.name or '') == datos['name']
            )[:1]
            if existente:
                # Si existe duplicado en cero para el mismo producto, lo removemos.
                ceros = self.invoice_line_ids.filtered(
                    lambda l: l.product_id.id == product_id and l.id != existente.id and (l.price_unit == 0 or l.price_unit is False)
                )
                if ceros:
                    self.invoice_line_ids -= ceros

                existente.price_unit = datos['price_unit']
                existente.quantity = datos['quantity']
            else:
                # En onchange no se puede hacer `+= [Command.create(...)]` (eso produce TypeError).
                # Creamos un registro virtual y lo concatenamos al one2many.
                self.invoice_line_ids += line_model.new(datos)

        # 2) Multas: pueden existir múltiples; evitamos duplicar por (product_id, name).
        for datos in datos_lineas_multas:
            ya_existe = self.invoice_line_ids.filtered(
                lambda l: l.product_id.id == datos['product_id'] and (l.name or '') == datos['name']
            )[:1]
            if ya_existe:
                continue
            
            # Extraer gc_multa_id de los datos (sin pop, para que no se afecten los datos)
            gc_multa_id = datos.get('gc_multa_id')
            
            # Crear línea sin el gc_multa_id en el diccionario inicial
            datos_sin_multa = {k: v for k, v in datos.items() if k != 'gc_multa_id'}
            nueva_linea = line_model.new(datos_sin_multa)
            
            # Asignar el gc_multa_id después de crear la línea
            if gc_multa_id:
                nueva_linea.gc_multa_id = gc_multa_id
            
            self.invoice_line_ids += nueva_linea

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Extender el onchange de partner_id para validar coherencia con apartamento
        """
        res = super()._onchange_partner_id()
        
        # Solo aplicar validación en facturas de cliente
        if self.apartamento_id and self.partner_id and self.move_type == 'out_invoice':
            # Verificar que el partner seleccionado sea uno de los propietarios
            propietarios = self.apartamento_id.propietario_ids
            if self.partner_id not in propietarios:
                return {
                    'warning': {
                        'title': 'Cliente no es Propietario',
                        'message': f'El cliente seleccionado no es propietario del apartamento {self.apartamento_id.display_name}. Se recomienda seleccionar uno de los propietarios registrados.',
                    }
                }
        
        return res

    def write(self, vals):
        """
        Sobreescribir write para mantener sincronización al cambiar apartamento
        """
        # Si se está cambiando el apartamento, recalcular propietarios
        if 'apartamento_id' in vals and vals['apartamento_id']:
            apartamento = self.env['gc.apartamento'].browse(vals['apartamento_id'])
            propietarios = apartamento.propietario_ids
            
            if propietarios:
                # Actualizar propietarios adicionales
                if len(propietarios) > 1:
                    vals['propietarios_adicionales_ids'] = [(6, 0, propietarios[1:].ids)]
                else:
                    vals['propietarios_adicionales_ids'] = [(5, 0, 0)]
        
        # Si se limpia el apartamento, limpiar propietarios adicionales
        if 'apartamento_id' in vals and not vals['apartamento_id']:
            vals['propietarios_adicionales_ids'] = [(5, 0, 0)]
        
        return super().write(vals)

    @api.model
    def create(self, vals):
        """
        Sobreescribir create para establecer propietarios adicionales en creación
        """
        # Si se crea con apartamento, establecer propietarios adicionales
        if vals.get('apartamento_id'):
            apartamento = self.env['gc.apartamento'].browse(vals['apartamento_id'])
            propietarios = apartamento.propietario_ids
            
            if propietarios and len(propietarios) > 1:
                vals['propietarios_adicionales_ids'] = [(6, 0, propietarios[1:].ids)]
        
        resultado = super().create(vals)
        
        # Marcar multas como facturadas después de crear la factura
        resultado._marcar_multas_facturadas()
        
        return resultado
    
    def write(self, vals):
        """
        Sobreescribir write para mantener sincronización al cambiar apartamento
        """
        # Si se está cambiando el apartamento, recalcular propietarios
        if 'apartamento_id' in vals and vals['apartamento_id']:
            apartamento = self.env['gc.apartamento'].browse(vals['apartamento_id'])
            propietarios = apartamento.propietario_ids
            
            if propietarios:
                # Actualizar propietarios adicionales
                if len(propietarios) > 1:
                    vals['propietarios_adicionales_ids'] = [(6, 0, propietarios[1:].ids)]
                else:
                    vals['propietarios_adicionales_ids'] = [(5, 0, 0)]
        
        # Si se limpia el apartamento, limpiar propietarios adicionales
        if 'apartamento_id' in vals and not vals['apartamento_id']:
            vals['propietarios_adicionales_ids'] = [(5, 0, 0)]
        
        resultado = super().write(vals)
        
        # Marcar multas como facturadas después de escribir la factura
        self._marcar_multas_facturadas()
        
        return resultado
    
    def _marcar_multas_facturadas(self):
        """
        Marca como facturadas las multas que están en líneas de esta factura.
        Solo marca como facturada si la factura está en estado 'posted'.
        Si la factura vuelve a draft o se cancela, revierte el estado de la multa.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        for factura in self:
            _logger.warning(f"🔍 GC_APARTAMENTOS - Procesando factura {factura.id} en estado '{factura.state}'")
            
            if factura.state == 'posted':
                # La factura está confirmada: marcar multas como facturadas
                _logger.warning(f"✅ Factura confirmada - Marcando multas como facturadas")
                
                if factura.apartamento_id:
                    multas_pendientes = self.env['gc.multas'].search([
                        ('num_apartamento_id', '=', factura.apartamento_id.id),
                        ('estado', '=', 'pendiente'),
                    ])
                    _logger.warning(f"📋 Multas pendientes encontradas: {len(multas_pendientes)}")
                    
                    for multa in multas_pendientes:
                        # Buscar línea que corresponda a esta multa
                        lineas_multa = factura.invoice_line_ids.filtered(
                            lambda l: l.product_id.id == multa.concepto_multa.id 
                            and 'Multa' in (l.name or '') 
                            and str(multa.fecha_multa) in (l.name or '')
                        )
                        
                        if lineas_multa:
                            linea = lineas_multa[0]
                            if not multa.facturada:
                                _logger.warning(f"🔗 Asignando gc_multa_id {multa.id} a línea {linea.id}")
                                linea.write({'gc_multa_id': multa.id})
                                
                                _logger.warning(f"✅ Marcando multa {multa.id} como facturada")
                                multa.write({
                                    'facturada': True,
                                    'factura_line_id': linea.id,
                                })
            
            elif factura.state in ('draft', 'cancel'):
                # La factura está en borrador o cancelada: revertir multas a pendiente
                _logger.warning(f"⚠️ Factura en {factura.state} - Revertiendo multas a pendiente")
                
                # Buscar multas que fueron facturadas por esta factura
                multas_en_lineas = self.env['gc.multas'].search([
                    ('factura_line_id', 'in', factura.invoice_line_ids.ids),
                    ('facturada', '=', True),
                ])
                
                for multa in multas_en_lineas:
                    _logger.warning(f"↩️ Revirtiendo multa {multa.id} a pendiente")
                    multa.write({
                        'facturada': False,
                        'factura_line_id': False,
                    })

    def action_post(self):
        """
        Sobreescribir action_post para marcar multas cuando la factura se confirma
        """
        resultado = super().action_post()
        # Marcar multas como facturadas cuando se confirma la factura
        self._marcar_multas_facturadas()
        return resultado

    def button_draft(self):
        """
        Sobreescribir button_draft para revertir multas cuando la factura vuelve a borrador
        """
        resultado = super().button_draft()
        # Revertir multas a pendiente cuando la factura vuelve a draft
        self._marcar_multas_facturadas()
        return resultado

    def button_cancel(self):
        """
        Sobreescribir button_cancel para revertir multas cuando la factura se cancela
        """
        resultado = super().button_cancel()
        # Revertir multas a pendiente cuando la factura se cancela
        self._marcar_multas_facturadas()
        return resultado
