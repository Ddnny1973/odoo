from odoo import models, fields, api
from odoo.exceptions import ValidationError

class GcApartamento(models.Model):
    _name = 'gc.apartamento'
    _description = 'Apartamento'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos básicos del apartamento
    numero_apartamento = fields.Integer(
        string='Número de Apartamento',
        required=True,
        help='Número único del apartamento'
    )
    
    torre = fields.Integer(
        string='Torre',
        required=True,
        help='Torre a la que pertenece el apartamento'
    )
    
    parqueadero = fields.Char(
        string='Parqueadero',
        help='Número del parqueadero asignado'
    )
    
    cuarto_util = fields.Char(
        string='Cuarto Útil',
        help='Número del cuarto útil asignado'
    )
    
    SOTANO_OPTIONS = [
        ('S0', 'Piso Principal'),
        ('S1', 'Sótano 1'),
        ('S2', 'Sótano 2'),
        ('S3', 'Sótano 3'),
        ('S4', 'Sótano 4'),
    ]

    sotano_parqueadero = fields.Selection(
        selection=SOTANO_OPTIONS,
        string='Sótano Parqueadero',
        help='Nivel de sótano para el parqueadero'
    )
    
    sotano_cuarto_util = fields.Selection(
        selection=SOTANO_OPTIONS,
        string='Sótano Cuarto Útil',
        help='Nivel de sótano para el cuarto útil'
    )
    
    # Características físicas
    area = fields.Float(
        string='Área (m²)',
        required=True,
        help='Área total del apartamento en metros cuadrados'
    )
    
    area_parqueadero = fields.Float(
    string='Área Parqueadero',
    help='Área del parqueadero en m2'
    )

    area_util = fields.Float(
    string='Área Util',
    help='Área del cuarto útil en m2'
    )

    area_total = fields.Float(
    string='Área Total',
    compute='_compute_area_total',
    store=True,
    help='Suma de área apartamento, parqueadero y útil'
    )

    coeficiente = fields.Float(
        string='Coeficiente',
        compute='_compute_coeficiente',
        help='Coeficiente de participación del apartamento'
    )
    
    @api.depends('area', 'area_parqueadero', 'area_util')
    def _compute_coeficiente(self):
        suma_total = sum(self.env['gc.apartamento'].search([]).mapped('area_total'))
        for rec in self:
            rec.coeficiente = (rec.area_total or 0.0) / suma_total if suma_total else 0.0

    fecha_entrega = fields.Date(
        string='Fecha de Entrega',
        help='Fecha de entrega del inmueble'
    )
    
    # Ocupación
    habitado_por = fields.Selection(
        string='Habitado por',
        selection=[
            ('propietario', 'Propietario'),
            ('arrendatario', 'Arrendatario'),
        ],
        help='Tipo de ocupante del apartamento'
    )
    
    # Relaciones con contactos
    propietario_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='gc_apartamento_propietario_rel',
        column1='apartamento_id',
        column2='propietario_id',
        string='Propietarios',
        help='Propietarios del apartamento'
    )
    
    arrendatario_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='gc_apartamento_arrendatario_rel',
        column1='apartamento_id',
        column2='arrendatario_id',
        string='Arrendatarios',
        help='Arrendatarios del apartamento'
    )
    
    # Observaciones
    observaciones = fields.Text(
        string='Observaciones',
        help='Notas y observaciones adicionales sobre el apartamento'
    )
    
    # Campos de auditoría
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Marca si el apartamento está activo'
    )

    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, ondelete='restrict')
    saldo_admon = fields.Monetary(string='Saldo administración', currency_field='currency_id')
    
    @api.onchange('habitado_por')
    def _onchange_habitado_por(self):
        """Si no es arrendatario, limpiar arrendatarios y advertir al usuario."""
        for rec in self:
            if rec.habitado_por != 'arrendatario' and rec.arrendatario_ids:
                rec.arrendatario_ids = [(5, 0, 0)]
                return {
                    'warning': {
                        'title': 'Atención',
                        'message': 'El campo Arrendatarios sólo está disponible cuando "Habituado por" es "Arrendatario". Se ha limpiado el campo.'
                    }
                }

    @api.constrains('habitado_por', 'arrendatario_ids')
    def _check_arrendatarios_consistency(self):
        for rec in self:
            if rec.habitado_por != 'arrendatario' and rec.arrendatario_ids:
                raise ValidationError(
                    "No puede asignar arrendatarios si 'Habitado por' no es 'Arrendatario'."
                )

    @api.depends('area', 'area_parqueadero', 'area_util')
    def _compute_area_total(self):
        for rec in self:
            rec.area_total = (rec.area or 0.0) + (rec.area_parqueadero or 0.0) + (rec.area_util or 0.0)

    def _compute_display_name(self):
        """Mostrar el número de apartamento como nombre"""
        for record in self:
            record.display_name = f"Apartamento {record.numero_apartamento} - Torre {record.torre}"