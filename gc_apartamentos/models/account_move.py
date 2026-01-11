from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import date


class AccountMoveLine(models.Model):
    """Extensión de líneas de factura para incluir coeficiente de apartamento"""
    _inherit = 'account.move.line'

    coeficiente = fields.Float(
        string='Coeficiente',
        help='Coeficiente de participación del apartamento',
        default=0.0,
        digits=(16, 5),
    )

    @api.onchange('product_id')
    def _onchange_product_id_gc(self):
        """
        Al seleccionar un producto manualmente en la línea de la factura:
        Busca si el producto tiene una configuración en gc.valores_conceptos
        para aplicar el coeficiente y el monto automáticamente.
        """
        # Solo actuar en facturas de cliente y si hay producto/apartamento
        if not self.product_id or not self.move_id.apartamento_id or self.move_id.move_type not in ('out_invoice', 'out_refund'):
            # Si no hay apartamento, asegurar que el coeficiente sea 0
            if not self.move_id.apartamento_id:
                self.coeficiente = 0.0
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
                self.coeficiente = coef
                self.price_unit = valor_concepto.monto * coef
            else:
                self.coeficiente = 0.0
                self.price_unit = valor_concepto.monto
        else:
            # Si el producto no está en la tabla de conceptos, 
            # podemos optar por poner coeficiente 0 o el del apartamento
            # Por seguridad, lo dejamos en 0 si no es un concepto predefinido
            self.coeficiente = 0.0


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
            
            # 2. Generar líneas SOLO si es la primera vez (no hay líneas)
            if self.invoice_date and not self.invoice_line_ids:
                self._crear_lineas_conceptos()
        else:
            # Si se limpia el apartamento, limpiar también propietarios adicionales
            self.propietarios_adicionales_ids = [Command.clear()]

    def _crear_lineas_conceptos(self):
        """
        Genera las líneas de factura basadas en conceptos recurrentes vigentes.
        """
        if not self.apartamento_id or not self.invoice_date:
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
        
        if not valores_conceptos:
            return
        
        # Agrupar por producto y seleccionar el más reciente
        productos_vigentes = {}
        for valor in valores_conceptos:
            producto_id = valor.producto_id.id
            if producto_id not in productos_vigentes:
                productos_vigentes[producto_id] = valor
        
        # Preparar lista de comandos: primero limpiar TODO, luego añadir
        # Usamos Command.clear() y Command.create() para mayor estabilidad en Odoo 18
        comandos_lineas = [Command.clear()]
        coef = self.apartamento_id.coeficiente
        
        for valor in productos_vigentes.values():
            # Calcular precio: monto * coeficiente o monto fijo según configuración
            if valor.usar_coeficiente:
                precio_unit = valor.monto * coef
            else:
                precio_unit = valor.monto
            
            # Solo añadir si el precio es mayor a 0 (evita líneas basura en la UI)
            if precio_unit > 0:
                comandos_lineas.append(Command.create({
                    'product_id': valor.producto_id.id,
                    'quantity': 1.0,
                    'price_unit': precio_unit,
                    'coeficiente': coef if valor.usar_coeficiente else 0.0,
                    'name': valor.producto_id.name,
                }))
        
        # Solo aplicar si realmente generamos algo para evitar limpiar líneas manuales si no hay conceptos
        if len(comandos_lineas) > 1:
            self.invoice_line_ids = comandos_lineas

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
        
        return super().create(vals)
