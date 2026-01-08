from odoo import models, fields, api
from odoo.exceptions import UserError


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

    @api.onchange('apartamento_id')
    def _onchange_apartamento_id(self):
        """
        Al seleccionar un apartamento:
        1. Establece el cliente principal (primer propietario)
        2. Llena propietarios adicionales con los demás propietarios
        """
        if self.apartamento_id:
            propietarios = self.apartamento_id.propietario_ids
            
            if not propietarios:
                # Si el apartamento no tiene propietarios, limpiar campos y advertir
                self.partner_id = False
                self.propietarios_adicionales_ids = [(5, 0, 0)]
                return {
                    'warning': {
                        'title': 'Apartamento sin Propietarios',
                        'message': f'El apartamento {self.apartamento_id.display_name} no tiene propietarios asignados. Por favor, asigne al menos un propietario antes de facturar.',
                    }
                }
            
            # Establecer el primer propietario como cliente principal
            propietario_principal = propietarios[0]
            self.partner_id = propietario_principal
            
            # Si hay más propietarios, agregarlos a propietarios adicionales
            if len(propietarios) > 1:
                propietarios_adicionales = propietarios[1:]
                self.propietarios_adicionales_ids = [(6, 0, propietarios_adicionales.ids)]
            else:
                # Si solo hay un propietario, limpiar propietarios adicionales
                self.propietarios_adicionales_ids = [(5, 0, 0)]
        else:
            # Si se limpia el apartamento, limpiar también propietarios adicionales
            # pero mantener el partner_id por si se eligió manualmente
            self.propietarios_adicionales_ids = [(5, 0, 0)]

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
