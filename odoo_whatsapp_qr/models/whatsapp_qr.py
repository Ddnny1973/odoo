# -*- coding: utf-8 -*-
from odoo import models, fields, api
import docker
import re


class WhatsappQR(models.Model):
    _name = 'whatsapp.qr'
    _description = 'WhatsApp QR vinculación'

    name = fields.Char('Nombre del servicio', required=True)
    phone_number = fields.Char('Número de teléfono', required=True)
    user_id = fields.Many2one('res.users', string='Usuario Odoo', required=True)
    qr_code = fields.Text('QR Code', compute='_compute_qr_code', store=True)
    logs_preview = fields.Text('Últimos logs', compute='_compute_logs_preview', store=True)
    
    _sql_constraints = [
        ('unique_phone', 'unique(phone_number)', 'El número de teléfono no puede repetirse.'),
        ('unique_service', 'unique(name)', 'El nombre del servicio no puede repetirse.'),
    ]

    def _compute_qr_code(self):
        for record in self:
            record.qr_code = record._get_qr_from_logs()
    
    def _compute_logs_preview(self):
        for record in self:
            record.logs_preview = record._get_logs_without_qr()

    def action_show_logs(self):
        for record in self:
            record.logs_preview = record._get_logs_without_qr()

    def _get_qr_from_logs(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.name)
            # Obtener más logs para asegurar que tenemos el más reciente
            logs = container.logs(tail=200).decode('utf-8')
            
            # Buscar imagen base64
            match = re.search(r'(data:image\/png;base64,[A-Za-z0-9+/=]+)', logs)
            if match:
                return match.group(1)
            
            # Búsqueda mejorada: encontrar bloques QR puros (solo caracteres de QR)
            # Los QR ASCII tienen un patrón consistente: líneas repetidas y similares en tamaño
            lines = logs.split('\n')
            qr_blocks = []
            current_block = []
            
            for line in lines:
                qr_char_count = line.count('█') + line.count('▀') + line.count('▁') + line.count('▂') + line.count('▓')
                
                # Si la línea tiene muchos caracteres de QR, es parte de un bloque QR
                if qr_char_count > 10:
                    current_block.append(line)
                else:
                    # Si terminamos un bloque (línea sin QR chars)
                    if current_block and len(current_block) > 15:  # Mínimo 15 líneas para ser un QR válido
                        qr_blocks.append('\n'.join(current_block))
                    current_block = []
            
            # No olvidar el último bloque si existe
            if current_block and len(current_block) > 15:
                qr_blocks.append('\n'.join(current_block))
            
            if qr_blocks:
                # Retornar el ÚLTIMO bloque QR (el más reciente)
                last_qr = qr_blocks[-1].strip()
                if last_qr:
                    return last_qr
                
            return 'QR no encontrado. Espera unos segundos y actualiza.'
        except Exception as e:
            return f'Error: {str(e)}'
    
    def _get_logs_without_qr(self):
        """Obtener los logs filtrando los bloques de QR ASCII"""
        try:
            client = docker.from_env()
            container = client.containers.get(self.name)
            logs = container.logs(tail=80).decode('utf-8')
            
            # Eliminar bloques grandes de QR ASCII (líneas con muchos █)
            lines = logs.split('\n')
            filtered_lines = []
            skip_count = 0
            
            for i, line in enumerate(lines):
                # Si la línea tiene muchos █, es parte del QR - saltar esta línea y las siguientes similares
                if line.count('█') > 10:
                    skip_count = 30  # Saltar las siguientes 30 líneas (típicamente el tamaño del QR)
                    continue
                
                if skip_count > 0:
                    skip_count -= 1
                    continue
                    
                filtered_lines.append(line)
            
            return '\n'.join(filtered_lines[-40:])  # Retornar las últimas 40 líneas de logs limpios
        except Exception as e:
            return f'Error obteniendo logs: {str(e)}'

    def action_update_qr(self):
        for record in self:
            record.qr_code = record._get_qr_from_logs()
            record.logs_preview = record._get_logs_without_qr()
