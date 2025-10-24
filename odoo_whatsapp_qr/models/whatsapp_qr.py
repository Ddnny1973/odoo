# -*- coding: utf-8 -*-
from odoo import models, fields, api
import docker
import re


class WhatsappQR(models.Model):
    logs_preview = fields.Text('Últimos logs', readonly=True)

    def action_show_logs(self):
        for record in self:
            try:
                client = docker.from_env()
                container = client.containers.get(record.name)
                logs = container.logs(tail=50).decode('utf-8')
                record.logs_preview = logs
            except Exception as e:
                record.logs_preview = f'Error: {str(e)}'
    _name = 'whatsapp.qr'
    _description = 'WhatsApp QR vinculación'

    name = fields.Char('Nombre del servicio', required=True)
    phone_number = fields.Char('Número de teléfono', required=True)
    user_id = fields.Many2one('res.users', string='Usuario Odoo', required=True)
    qr_code = fields.Text('QR Code', compute='_compute_qr_code', store=True)
    _sql_constraints = [
        ('unique_phone', 'unique(phone_number)', 'El número de teléfono no puede repetirse.'),
        ('unique_service', 'unique(name)', 'El nombre del servicio no puede repetirse.'),
    ]

    def _compute_qr_code(self):
        for record in self:
            record.qr_code = record._get_qr_from_logs()

    def _get_qr_from_logs(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.name)
            logs = container.logs(tail=80).decode('utf-8')
            # Log para depuración
            with open('/tmp/odoo_qr_debug.log', 'w', encoding='utf-8') as f:
                f.write(logs)
            # Buscar imagen base64
            match = re.search(r'(data:image\/png;base64,[A-Za-z0-9+/=]+)', logs)
            if match:
                return match.group(1)
            # Si no hay imagen, buscar el bloque de QR en ASCII
            qr_blocks = re.findall(r'([\s\S]{100,})', logs)
            if qr_blocks:
                qr_ascii = max(qr_blocks, key=len)
                return qr_ascii  # texto plano, sin HTML
            return 'QR no encontrado'
        except Exception as e:
            with open('/tmp/odoo_qr_debug.log', 'a', encoding='utf-8') as f:
                f.write(f'\n--- Error: {str(e)} ---\n')
            return f'Error: {str(e)}'

    def action_update_qr(self):
        for record in self:
            record.qr_code = record._get_qr_from_logs()
