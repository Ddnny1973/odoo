from odoo import models, fields, api

class GcMultas(models.Model):
    _name = 'gc.multas'
    _description = 'Multas y Sanciones'
    _order = 'id desc'

    num_apartamento_id = fields.Many2one(
        'gc.apartamento',
        string='Apartamento',
        required=True,
        help='Apartamento relacionado con la multa'
    )
    
    fecha_multa = fields.Date(
        string='Fecha de Multa',
        required=True
    )
    
    concepto_multa = fields.Many2one(
        'product.product',
        string='Concepto de Multa',
        required=True,
        domain="[('categ_id.name', '=', 'Multas y Sanciones'), ('categ_id.parent_id.name', '=', 'Conceptos Condominio')]",
        help='Producto asociado a la multa, filtrado por categoría "Conceptos Condominio / Multas y Sanciones"'
    )
    
    monto_multa = fields.Float(
        string='Monto de la Multa',
        required=True,
        default=0.0,
        help='Monto de la multa a cobrar'
    )
    
    facturada = fields.Boolean(
        string='Facturada',
        default=False,
        help='Indica si la multa ya ha sido incluida en una factura'
    )
    
    factura_line_id = fields.Many2one(
        'account.move.line',
        string='Línea de Factura',
        readonly=True,
        help='Línea de factura donde se incluyó esta multa'
    )
    
    estado = fields.Selection(
        [
            ('pendiente', 'Pendiente'),
            ('facturada', 'Facturada'),
            ('pagada', 'Pagada'),
        ],
        string='Estado',
        default='pendiente',
        compute='_compute_estado',
        store=True,
        help='Estado de la multa'
    )
    
    @api.depends('facturada', 'factura_line_id', 'factura_line_id.move_id.payment_state')
    def _compute_estado(self):
        """Calcula el estado de la multa según facturación y pago"""
        for multa in self:
            if not multa.facturada:
                multa.estado = 'pendiente'
            elif multa.factura_line_id and multa.factura_line_id.move_id:
                # Revisar estado de pago de la factura
                move = multa.factura_line_id.move_id
                if move.payment_state == 'paid':
                    multa.estado = 'pagada'
                else:
                    multa.estado = 'facturada'
            else:
                multa.estado = 'facturada'

    @api.onchange('concepto_multa', 'fecha_multa')
    def _onchange_concepto_monto(self):
        """Autocompletar monto desde gc.valores_conceptos cuando se selecciona el concepto"""
        if not self.concepto_multa:
            return
        
        # Si no hay fecha, usar la fecha actual
        fecha_ref = self.fecha_multa or fields.Date.today()
        
        # Buscar valor vigente del concepto en la fecha de la multa
        valor = self.env['gc.valores_conceptos'].search([
            ('producto_id', '=', self.concepto_multa.id),
            ('activo', '=', True),
            ('fecha_inicial', '<=', fecha_ref),
            '|',
            ('fecha_final', '=', False),
            ('fecha_final', '>=', fecha_ref),
        ], limit=1, order='fecha_inicial desc')
        
        if valor:
            self.monto_multa = valor.monto
        else:
            # Si no encuentra valor vigente, mantener o establecer en 0.0
            if not self.monto_multa:
                self.monto_multa = 0.0
