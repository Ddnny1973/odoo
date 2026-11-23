# -*- coding: utf-8 -*-
import json
import logging
import re
import urllib.error
import urllib.request

from odoo import fields, models

_logger = logging.getLogger(__name__)

# Frases que el JavaScript del portal reconoce como "no hay QR que dibujar" (ver displayQR en la plantilla).
SIN_QR = 'QR no encontrado'


class WhatsappQR(models.Model):
    _name = 'whatsapp.qr'
    _description = 'WhatsApp QR vinculación'

    name = fields.Char('Nombre del servicio', required=True)
    phone_number = fields.Char('Número de teléfono', required=True)
    user_id = fields.Many2one('res.users', string='Usuario Odoo', required=True)
    fuente = fields.Selection(
        [('api', 'API del contenedor (recomendado)'), ('docker', 'Logs de Docker (legado)')],
        string='Cómo se obtiene el QR', default='docker', required=True, groups='base.group_system',
        help="API: Odoo pide el QR por HTTP al contenedor de WhatsApp (GET /qr con token); no necesita "
             "el socket de Docker. Docker (legado): lee los logs del contenedor con el socket de Docker; "
             "solo para contenedores que aun no tienen /qr (p. ej. wppapi_mb) y se puede retirar cuando "
             "todos usen la API.")
    api_url = fields.Char(
        'URL de la API', groups='base.group_system',
        help="Ej.: http://wppapi_ejemplo:3000 (si Odoo y el contenedor comparten red de Docker) o "
             "http://10.0.0.6:8061 (puerto publicado en la red privada). Si se deja vacío se usa "
             "http://<nombre del servicio>:3000.")
    api_token = fields.Char(
        'Token de la API', groups='base.group_system',
        help="Mismo valor que WPP_QR_TOKEN del contenedor de WhatsApp. Sin token no se entrega ningún QR.")
    # Calculados al leer (no se guardan): el QR y el estado nunca quedan en la base de datos de Odoo.
    qr_code = fields.Text('QR Code', compute='_compute_qr_code')
    logs_preview = fields.Text('Estado de la sesión', compute='_compute_logs_preview')

    _sql_constraints = [
        ('unique_phone', 'unique(phone_number)', 'El número de teléfono no puede repetirse.'),
        ('unique_service', 'unique(name)', 'El nombre del servicio no puede repetirse.'),
    ]

    def _compute_qr_code(self):
        for record in self:
            record.qr_code = record._get_qr()

    def _compute_logs_preview(self):
        for record in self:
            record.logs_preview = record._get_estado()

    def action_show_logs(self):
        # Refresca el estado en pantalla (los campos se calculan al leer).
        return True

    def action_update_qr(self):
        return True

    # ------------------------------------------------------------------ modo API (recomendado)
    def _consultar_api(self):
        """GET /qr del contenedor. Devuelve el JSON o lanza ValueError con un mensaje legible."""
        self.ensure_one()
        base = (self.api_url or f'http://{self.name}:3000').rstrip('/')
        if not base.startswith(('http://', 'https://')):
            raise ValueError('La URL de la API debe empezar por http:// o https://')
        if not self.api_token:
            raise ValueError('Falta el token de la API (lo configura el administrador).')
        req = urllib.request.Request(f'{base}/qr', headers={'x-wpp-token': self.api_token})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise ValueError('El token no coincide con el del contenedor.')
            if e.code == 503:
                raise ValueError('El contenedor no tiene configurado WPP_QR_TOKEN.')
            raise ValueError(f'El contenedor respondió {e.code}.')
        except Exception as e:  # noqa: BLE001
            _logger.warning('whatsapp.qr %s: no se pudo consultar la API: %s', self.name, e)
            raise ValueError('No se pudo conectar con el contenedor (¿está encendido y en la misma red?).')

    # ------------------------------------------------------------------ interfaz usada por el portal
    def _get_qr(self):
        """Texto que entiende el portal: data URL PNG, bloque ASCII o un aviso que empieza por
        'QR no encontrado' / 'Error'."""
        self.ensure_one()
        if self.fuente == 'api':
            try:
                datos = self._consultar_api()
            except ValueError as e:
                return f'Error: {e}'
            if datos.get('estado') == 'listo':
                return f'{SIN_QR}: la sesión ya está vinculada.'
            return datos.get('qr') or f'{SIN_QR}. Espera unos segundos y actualiza.'
        return self._get_qr_from_logs()

    def _get_estado(self):
        """Resumen de estado para mostrar (sin logs del contenedor en modo API: los logs de wppapi
        incluyen nombres y el inicio de los mensajes)."""
        self.ensure_one()
        if self.fuente == 'api':
            try:
                d = self._consultar_api()
            except ValueError as e:
                return f'Error: {e}'
            textos = {
                'listo': 'Sesión vinculada y lista.',
                'esperando_qr': 'Esperando que escanees el QR (se renueva solo cada ~20 s).',
                'iniciando': 'El servicio está iniciando; espera unos segundos.',
            }
            lineas = [f"Estado: {textos.get(d.get('estado'), d.get('estado'))}"]
            if d.get('qr_emitido'):
                lineas.append(f"Último QR emitido: {d['qr_emitido']}")
            return '\n'.join(lineas)
        return self._get_logs_without_qr()

    # ------------------------------------------------------------------ modo Docker (legado)
    def _contenedor_docker(self):
        import docker  # solo si hay registros en modo legado
        return docker.from_env().containers.get(self.name)

    def _get_qr_from_logs(self):
        try:
            logs = self._contenedor_docker().logs(tail=200).decode('utf-8')

            match = re.search(r'(data:image\/png;base64,[A-Za-z0-9+/=]+)', logs)
            if match:
                return match.group(1)

            # Bloques QR ASCII: líneas con muchos caracteres de bloque; se devuelve el último (más reciente)
            qr_blocks, current_block = [], []
            for line in logs.split('\n'):
                qr_char_count = sum(line.count(c) for c in '█▀▄▁▂▓')
                if qr_char_count > 10:
                    current_block.append(line)
                else:
                    if current_block and len(current_block) > 15:
                        qr_blocks.append('\n'.join(current_block))
                    current_block = []
            if current_block and len(current_block) > 15:
                qr_blocks.append('\n'.join(current_block))
            if qr_blocks:
                last_qr = qr_blocks[-1].strip()
                if last_qr:
                    return last_qr
            return f'{SIN_QR}. Espera unos segundos y actualiza.'
        except Exception as e:  # noqa: BLE001
            return f'Error: {e}'

    def _get_logs_without_qr(self):
        """Logs del contenedor sin los bloques de QR ASCII (solo modo legado)."""
        try:
            logs = self._contenedor_docker().logs(tail=80).decode('utf-8')
            filtered_lines, skip_count = [], 0
            for line in logs.split('\n'):
                if sum(line.count(c) for c in '█▀▄▓') > 10:
                    skip_count = 30
                    continue
                if skip_count > 0:
                    skip_count -= 1
                    continue
                filtered_lines.append(line)
            return '\n'.join(filtered_lines[-40:])
        except Exception as e:  # noqa: BLE001
            return f'Error obteniendo logs: {e}'
