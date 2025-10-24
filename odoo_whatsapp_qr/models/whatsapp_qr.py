# -*- coding: utf-8 -*-
from odoo import models, fields, api
import docker
import re

class WhatsappQR(models.Model):
    _name = 'whatsapp.qr'
    _description = 'WhatsApp QR vinculación'

    name = fields.Char('Nombre del servicio')
    phone_number = fields.Char('Número de teléfono')
    qr_code = fields.Text('QR Code', compute='_compute_qr_code')

    def _compute_qr_code(self):
        for record in self:
            # Aquí se asume que el nombre del servicio es el nombre del contenedor Docker
            try:
                client = docker.from_env()
                container = client.containers.get(record.name)
                logs = container.logs(tail=100).decode('utf-8')
                # Busca el QR en los logs (ajusta el regex según el formato real)
                match = re.search(r'(data:image\/png;base64,[A-Za-z0-9+/=]+)', logs)
                record.qr_code = match.group(1) if match else 'QR no encontrado'
            except Exception as e:
                record.qr_code = f'Error: {str(e)}'
