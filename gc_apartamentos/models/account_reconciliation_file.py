# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountReconciliationFile(models.Model):

    _name = 'account.reconciliation.file'
    _description = 'Archivo de Conciliación'
    _order = 'fecha desc'

    # Campos básicos
    fecha = fields.Date(
        string='Fecha',
        required=True
    )
    
    descripcion = fields.Text(
        string='Descripción',
        required=True
    )
    
    # Campos de referencia
    sucursal_canal = fields.Char(
        string='Sucursal/Canal',
        size=100
    )
    
    referencia_1 = fields.Char(
        string='Referencia 1',
        size=50
    )
    
    referencia_2 = fields.Char(
        string='Referencia 2',
        size=100
    )
    
    documento = fields.Char(
        string='Documento',
        size=50
    )
    
    # Datos económicos
    valor = fields.Monetary(
        string='Valor',
        required=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )
    
    # Archivo
    filename = fields.Char(
        string='Nombre del Archivo',
        size=255
    )
    
    hash_file = fields.Char(
        string='Hash del Archivo',
        size=64,
        index=True,
        unique=True
    )
    
    # Pasarela
    pasarela = fields.Char(
        string='Pasarela',
        size=100
    )
    
    # Apartamento vinculado
    apartamento_id = fields.Many2one(
        comodel_name='gc.apartamento',
        string='Apartamento',
        readonly=False,
        help='Apartamento asociado a este pago'
    )

    # Pago relacionado
    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='Pago relacionado',
        readonly=True,
        help='Pago generado a partir de este archivo de conciliación'
    )
    
    # Estado
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('done', 'Procesado')
        ],
        string='Estado',
        default='draft'
    )

    @api.model
    def create(self, vals):
        """Buscar apartamento y crear pago al crear el registro"""
        _logger.info(f"🔄 Creando archivo de conciliación: {vals.get('documento')}")

        if not vals.get('apartamento_id'):
            # Intentar buscar por documento (cédula) o por referencia_1 (número apt)
            apartamento_id = self._buscar_apartamento(
                numero_apt=vals.get('referencia_1'),
                cedula=vals.get('documento')
            )
            if apartamento_id:
                vals['apartamento_id'] = apartamento_id
                _logger.info(f"✅ Apartamento asignado: {apartamento_id}")
            else:
                _logger.warning(f"⚠️ No se encontró apartamento para documento: {vals.get('documento')}")

        record = super().create(vals)

        # Si hay apartamento, intentar crear pago y asociar
        if record.apartamento_id:
            # Buscar propietario principal (primer propietario)
            propietario = record.apartamento_id.propietario_ids[:1]
            if propietario:
                try:
                    payment = self.env['account.payment'].create_from_reconciliation(
                        partner_id=propietario.id,
                        amount=record.valor,
                        payment_date=record.fecha,
                        currency_id=record.currency_id.id,
                        reference=record.documento or record.filename or record.descripcion,
                        reconciliation_file_id=record.id
                    )
                    record.payment_id = payment.id
                    _logger.info(f"✅ Pago creado y asociado: {payment.id}")
                except Exception as e:
                    _logger.error(f"❌ Error creando pago: {e}")
            else:
                _logger.warning(f"⚠️ Apartamento sin propietarios: {record.apartamento_id.id}")
        else:
            _logger.info("No se crea pago porque no hay apartamento asociado.")

        return record

    def _buscar_apartamento(self, numero_apt=None, cedula=None):
        """
        Buscar apartamento por número o cédula del propietario.
        Retorna el ID del apartamento o None
        """
        _logger.info(f"🔍 Buscando apartamento - Número: {numero_apt}, Cédula: {cedula}")
        
        # Buscar por número de apartamento primero
        if numero_apt:
            try:
                num = int(numero_apt)
                apartamento = self.env['gc.apartamento'].search(
                    [('numero_apartamento', '=', num)],
                    limit=1
                )
                if apartamento:
                    _logger.info(f"✅ Apartamento encontrado por número: {num} → ID: {apartamento.id}")
                    return apartamento.id
            except (ValueError, TypeError):
                _logger.debug(f"⚠️ No se pudo convertir número de apartamento: {numero_apt}")
        
        # Buscar por cédula del propietario
        if cedula:
            _logger.info(f"🔍 Buscando partner con cédula: {cedula}")
            partner = self.env['res.partner'].search(
                [('vat', '=', cedula)],
                limit=1
            )
            if partner:
                _logger.info(f"✅ Partner encontrado: {partner.name}")
                # Buscar apartamento donde este partner sea propietario
                apartamento = self.env['gc.apartamento'].search(
                    [('propietario_ids', 'in', [partner.id])],
                    limit=1
                )
                if apartamento:
                    _logger.info(f"✅ Apartamento encontrado por cédula: {cedula} → ID: {apartamento.id}")
                    return apartamento.id
                else:
                    _logger.warning(f"⚠️ Partner {partner.name} no tiene apartamentos asociados")
            else:
                _logger.warning(f"⚠️ No se encontró partner con cédula: {cedula}")
        
        return None

    def unlink(self):
        """Solo permitir eliminar registros en estado draft"""
        for record in self:
            if record.state != 'draft':
                from odoo.exceptions import UserError
                raise UserError(
                    f"No se puede eliminar el registro '{record.documento}' porque está en estado '{record.get_state_display()}'. "
                    "Solo se pueden eliminar registros en estado 'Borrador'."
                )
        return super().unlink()
    
    def get_state_display(self):
        """Retorna el valor visual del estado"""
        state_dict = dict(self._fields['state'].selection)
        return state_dict.get(self.state, self.state)
    
    def action_generar_pago_masivo(self):
        """
        Acción masiva: genera y asocia el pago para los registros seleccionados que no tengan pago relacionado.
        """
        _logger.info(f"▶️ Acción masiva: Generar pagos para conciliaciones seleccionadas ({len(self)})")
        creados = 0
        for record in self:
            # Si ya tiene pago relacionado, omitir
            if hasattr(record, 'payment_id') and record.payment_id:
                _logger.info(f"Registro {record.id} ya tiene pago asociado: {record.payment_id.id}")
                continue
            if not record.apartamento_id:
                _logger.warning(f"Registro {record.id} sin apartamento asociado")
                continue
            propietario = record.apartamento_id.propietario_ids[:1]
            if not propietario:
                _logger.warning(f"Registro {record.id} sin propietario principal")
                continue
            try:
                payment = self.env['account.payment'].create_from_reconciliation(
                    partner_id=propietario.id,
                    amount=record.valor,
                    payment_date=record.fecha,
                    currency_id=record.currency_id.id,
                    reference=record.documento or record.filename or record.descripcion
                )
                if hasattr(record, 'payment_id'):
                    record.payment_id = payment.id
                _logger.info(f"✅ Pago creado y asociado para registro {record.id}: {payment.id}")
                creados += 1
            except Exception as e:
                _logger.error(f"❌ Error creando pago para registro {record.id}: {e}")
        _logger.info(f"▶️ Pagos generados y asociados: {creados}")
        return True
