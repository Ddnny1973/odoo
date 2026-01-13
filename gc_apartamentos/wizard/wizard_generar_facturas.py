from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


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

    fecha_vencimiento = fields.Date(
        string='Fecha de Vencimiento',
        required=True,
        default=lambda self: date.today(),
        help='Fecha de vencimiento que se asignará a todas las facturas generadas',
    )

    incluir_activos_solo = fields.Boolean(
        string='Solo Apartamentos Activos',
        default=True,
        help='Si está activado, solo genera facturas para apartamentos activos',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Asignar fecha_vencimiento por defecto igual a fecha_facturacion"""
        for vals in vals_list:
            if 'fecha_facturacion' in vals and 'fecha_vencimiento' not in vals:
                vals['fecha_vencimiento'] = vals['fecha_facturacion']
        return super().create(vals_list)

    @api.onchange('fecha_facturacion')
    def _onchange_fecha_facturacion(self):
        """Cuando cambia la fecha de facturación, la fecha de vencimiento se iguala por defecto"""
        if self.fecha_facturacion:
            self.fecha_vencimiento = self.fecha_facturacion

    def action_generar_facturas(self):
        """
        Genera facturas para todos los apartamentos en la fecha especificada.
        Muestra notificaciones de progreso.
        """
        if not self.fecha_facturacion:
            raise UserError('Debe especificar una fecha de facturación.')
        
        if not self.fecha_vencimiento:
            raise UserError('Debe especificar una fecha de vencimiento.')

        # Obtener los apartamentos según el filtro
        domain = []
        if self.incluir_activos_solo:
            domain.append(('active', '=', True))

        apartamentos = self.env['gc.apartamento'].search(domain)

        if not apartamentos:
            raise UserError('No hay apartamentos disponibles para generar facturas.')

        total_apartamentos = len(apartamentos)
        _logger.info(f'🚀 Iniciando generación de {total_apartamentos} facturas para fecha {self.fecha_facturacion}')

        AccountMove = self.env['account.move']
        facturas_creadas = []
        errores = []

        for idx, apartamento in enumerate(apartamentos, 1):
            try:
                # Mostrar progreso cada 10 apartamentos en logs del servidor
                if idx % 10 == 0:
                    _logger.info(f'📊 Progreso: {idx}/{total_apartamentos} apartamentos procesados')
                
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
                    'invoice_date_due': self.fecha_vencimiento,
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
                _logger.error(f'Error creando factura para {apartamento.display_name}: {str(e)}')
                errores.append(
                    f'Apartamento {apartamento.display_name}: {str(e)}'
                )
                continue

        # Preparar mensaje de resultado
        mensaje = f'✅ Se crearon {len(facturas_creadas)} de {total_apartamentos} factura(s) exitosamente.\n'
        if errores:
            mensaje += f'\n⚠️ Advertencias/Errores ({len(errores)}):\n'
            for error in errores[:10]:  # Mostrar máximo 10 errores
                mensaje += f'  • {error}\n'
            if len(errores) > 10:
                mensaje += f'  ... y {len(errores) - 10} errores más'

        _logger.info(f'✅ Generación completada: {len(facturas_creadas)} facturas creadas, {len(errores)} errores')

        # Retornar acción para mostrar las facturas creadas
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Generación de Facturas Completada',
                'message': mensaje,
                'type': 'success' if len(facturas_creadas) > 0 else 'warning',
                'sticky': True,
            }
        }
