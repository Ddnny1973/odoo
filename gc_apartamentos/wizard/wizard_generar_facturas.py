from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class WizardGenerarFacturas(models.TransientModel):
    """
    Wizard para generar facturas masivas para todos los apartamentos
    """
    _name = 'gc.wizard_generar_facturas'
    _description = 'Generar Facturas de Apartamentos'

    fecha_facturacion = fields.Date(
        string='Fecha de Facturación',
        required=True,
        default=lambda self: date.today(),
        help='Fecha que se asignará a todas las facturas generadas',
    )

    incluir_activos_solo = fields.Boolean(
        string='Solo Apartamentos Activos',
        default=True,
        help='Si está activado, solo genera facturas para apartamentos activos',
    )

    def action_generar_facturas(self):
        """
        Genera facturas para todos los apartamentos en la fecha especificada
        """
        if not self.fecha_facturacion:
            raise UserError('Debe especificar una fecha de facturación.')

        # Obtener los apartamentos según el filtro
        domain = []
        if self.incluir_activos_solo:
            domain.append(('active', '=', True))

        apartamentos = self.env['gc.apartamento'].search(domain)

        if not apartamentos:
            raise UserError('No hay apartamentos disponibles para generar facturas.')

        AccountMove = self.env['account.move']
        facturas_creadas = []
        errores = []

        for apartamento in apartamentos:
            try:
                # Validar que el apartamento tenga propietarios
                if not apartamento.propietario_ids:
                    errores.append(
                        f'Apartamento {apartamento.display_name}: sin propietarios registrados'
                    )
                    continue

                # Obtener el primer propietario como cliente principal
                cliente_principal = apartamento.propietario_ids[0]

                # Crear la factura
                factura = AccountMove.create({
                    'move_type': 'out_invoice',
                    'partner_id': cliente_principal.id,
                    'apartamento_id': apartamento.id,
                    'invoice_date': self.fecha_facturacion,
                    'date': self.fecha_facturacion,
                    'state': 'draft',
                })

                # Ejecutar el onchange para generar líneas automáticas
                factura._onchange_apartamento_o_fecha()

                # Guardar la factura con líneas generadas
                if factura.invoice_line_ids:
                    factura.write({})  # Forzar guardado
                    facturas_creadas.append(factura)
                else:
                    # Si no hay líneas, advertir pero no fallar
                    errores.append(
                        f'Apartamento {apartamento.display_name}: sin líneas generadas (sin conceptos recurrentes activos)'
                    )
                    factura.unlink()  # Eliminar factura vacía

            except Exception as e:
                errores.append(
                    f'Apartamento {apartamento.display_name}: {str(e)}'
                )
                continue

        # Preparar mensaje de resultado
        mensaje = f'Se crearon {len(facturas_creadas)} factura(s) exitosamente.\n'
        if errores:
            mensaje += f'\nAdvertencias/Errores ({len(errores)}):\n'
            mensaje += '\n'.join(errores)

        # Retornar acción para mostrar las facturas creadas
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Generación de Facturas',
                'message': mensaje,
                'type': 'success' if len(facturas_creadas) > 0 else 'warning',
                'sticky': True,
            }
        }
