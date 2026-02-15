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
            logs = container.logs(tail=150).decode('utf-8')
            # Log para depuración
            with open('/tmp/odoo_qr_debug.log', 'w', encoding='utf-8') as f:
                f.write(logs)
            
            # Buscar imagen base64
            match = re.search(r'(data:image\/png;base64,[A-Za-z0-9+/=]+)', logs)
            if match:
                return match.group(1)
            
            # Buscar el QR ASCII más reciente usando el patrón de wppconnect
            # El QR aparece precedido por texto como "Escanea este QR para vincular"
            qr_marker_pattern = r'Escanea este QR.*?[\r\n]+(.*?)(?=\n\n|\n[^\s█]|$)'
            qr_match = re.findall(qr_marker_pattern, logs, re.DOTALL | re.IGNORECASE)
            
            if qr_match:
                # Retornar el ÚLTIMO QR encontrado (el más reciente)
                qr_ascii = qr_match[-1].strip()
                # Validar que tenga el patrón de bloques del QR
                if '█' in qr_ascii and len(qr_ascii) > 200:
                    return qr_ascii
            
            # Fallback: buscar bloques que contengan el carácter █ (típico de QR ASCII)
            # Dividir los logs en bloques y buscar el que tenga el patrón QR
            qr_blocks = re.split(r'\n\s*\n', logs)
            qr_candidates = [block for block in qr_blocks if '█' in block and block.count('\n') > 15]
            
            if qr_candidates:
                # Retornar el ÚLTIMO bloque QR encontrado
                return qr_candidates[-1].strip()
                
            return 'QR no encontrado. Espera unos segundos y actualiza.'
        except Exception as e:
            with open('/tmp/odoo_qr_debug.log', 'a', encoding='utf-8') as f:
                f.write(f'\n--- Error: {str(e)} ---\n')
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
