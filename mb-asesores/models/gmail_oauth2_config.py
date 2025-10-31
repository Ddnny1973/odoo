# models/gmail_oauth2_config.py
import os
import pickle
import logging
import json
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class GmailOAuth2Config(models.Model):
    _name = 'gmail.oauth2.config'
    _description = 'Configuración OAuth2 específica para Gmail'
    _rec_name = 'email'

    email = fields.Char(
        string='Email de Gmail',
        required=True,
        help='Email de la cuenta Gmail que enviará los correos'
    )
    
    client_id = fields.Char(
        string='Client ID',
        required=True,
        help='Client ID del proyecto Google Cloud Console'
    )
    
    client_secret = fields.Char(
        string='Client Secret',
        required=True,
        help='Client Secret del proyecto Google Cloud Console'
    )
    
    credentials_json = fields.Text(
        string='Archivo credentials.json',
        help='Contenido del archivo JSON de credenciales descargado de Google Cloud Console'
    )
    
    token_pickle = fields.Binary(
        string='Token Pickle',
        help='Token de autenticación generado (automático)',
        readonly=True
    )
    
    is_authenticated = fields.Boolean(
        string='Autenticado',
        default=False,
        readonly=True
    )
    
    last_auth_date = fields.Datetime(
        string='Última Autenticación',
        readonly=True
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )

    @api.model
    def create(self, vals):
        # Verificar que no exista otra configuración para el mismo email
        existing = self.search([('email', '=', vals.get('email'))])
        if existing:
            raise UserError(f"Ya existe una configuración OAuth2 para {vals.get('email')}")
        
        return super().create(vals)

    def action_authenticate(self):
        """Iniciar proceso de autenticación OAuth2"""
        self.ensure_one()
        
        if not self.credentials_json:
            raise UserError("Debes subir el archivo credentials.json primero")
        
        try:
            # Crear archivo de credenciales temporal desde el JSON
            self._create_temp_credentials_file()
            
            # Iniciar flujo OAuth2 web (compatible con Docker/proxy reverso)
            return self._start_web_oauth_flow()
            
        except Exception as e:
            _logger.error(f"Error en autenticación OAuth2: {e}")
            raise UserError(f"Error iniciando autenticación: {str(e)}")

    def _start_web_oauth_flow(self):
        """Iniciar flujo OAuth2 web para entornos Docker/proxy reverso"""
        try:
            from google_auth_oauthlib.flow import Flow
            
            SCOPES = [
                'https://www.googleapis.com/auth/gmail.send'
                # Removido 'https://mail.google.com/' para reducir permisos requeridos
                # Esto puede ayudar a evitar errores access_denied
            ]
            
            creds_path = self._get_temp_credentials_path()
            
            # Crear flow web en lugar de InstalledAppFlow
            flow = Flow.from_client_secrets_file(
                creds_path,
                scopes=SCOPES
            )
            
            # Configurar URL de redirección usando la URL base del sistema
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if not base_url:
                raise UserError("La URL base del sistema no está configurada. Ve a Configuración > Parámetros del sistema y configura 'web.base.url'")
            
            # Limpiar la URL base y asegurar que use HTTPS para OAuth2
            base_url = base_url.rstrip('/')
            
            # Para OAuth2, Google requiere HTTPS en producción
            # Convertir HTTP a HTTPS automáticamente si es un dominio público
            if base_url.startswith('http://') and not base_url.startswith('http://localhost'):
                base_url = base_url.replace('http://', 'https://', 1)
                _logger.info(f"Convirtiendo HTTP a HTTPS para OAuth2: {base_url}")
            
            redirect_uri = f"{base_url}/gmail/oauth2/callback"
            
            flow.redirect_uri = redirect_uri
            
            _logger.info(f"Iniciando OAuth2 web para {self.email} con redirect_uri: {redirect_uri}")
            
            # Generar URL de autorización
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Forzar pantalla de consentimiento para obtener refresh_token
            )
            
            # Guardar datos del flow para el callback
            self._save_flow_data(state, SCOPES, redirect_uri)
            
            return {
                'type': 'ir.actions.act_url',
                'url': auth_url,
                'target': 'new',
            }
            
        except Exception as e:
            _logger.error(f"Error generando URL OAuth2: {e}")
            raise UserError(f"Error generando URL OAuth2: {str(e)}")

    def _create_temp_credentials_file(self):
        """Crear archivo de credenciales temporal desde el JSON"""
        try:
            # Parsear el JSON para validarlo
            creds_data = json.loads(self.credentials_json)
            
            # Asegurar que es un formato válido
            if 'installed' not in creds_data and 'web' not in creds_data:
                # Si no tiene el formato correcto, intentar detectar el tipo
                if 'client_id' in creds_data and 'client_secret' in creds_data:
                    # Parece ser el contenido directo, envolver en 'web'
                    creds_data = {'web': creds_data}
                else:
                    raise UserError("El formato del archivo JSON no es válido")
            
            # Guardar archivo temporal
            temp_creds_path = self._get_temp_credentials_path()
            with open(temp_creds_path, 'w') as f:
                json.dump(creds_data, f, indent=2)
                
            _logger.info(f"Archivo de credenciales temporal creado: {temp_creds_path}")
            
        except json.JSONDecodeError as e:
            raise UserError(f"El archivo JSON no es válido: {str(e)}")
        except Exception as e:
            _logger.error(f"Error creando archivo temporal: {e}")
            raise UserError(f"Error procesando credenciales: {str(e)}")

    def _save_credentials_to_pickle(self, creds):
        """Guardar credenciales en formato pickle"""
        try:
            import pickle
            token_data = pickle.dumps(creds)
            encoded_token = base64.b64encode(token_data)
            
            self.sudo().write({
                'token_pickle': encoded_token
            })
            
        except Exception as e:
            _logger.error(f"Error guardando credenciales: {e}")
            raise

    def _cleanup_temp_files(self):
        """Limpiar archivos temporales"""
        try:
            import os
            temp_creds = self._get_temp_credentials_path()
            if os.path.exists(temp_creds):
                os.remove(temp_creds)
        except Exception as e:
            _logger.warning(f"Error limpiando archivos temporales: {e}")

    def _get_temp_credentials_path(self):
        """Obtener ruta temporal para credentials.json"""
        addon_path = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(addon_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, f'credentials_{self.id}.json')

    def _get_token_pickle_path(self):
        """Obtener ruta para el token pickle"""
        addon_path = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(addon_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, f'gmail_token_{self.id}.pickle')

    def _start_oauth_flow(self):
        """Iniciar flujo OAuth2 y devolver URL de autorización"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = [
                'https://www.googleapis.com/auth/gmail.send'
                # Removido 'https://mail.google.com/' para reducir permisos requeridos
            ]
            
            creds_path = self._get_temp_credentials_path()
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            
            # Usar URI de redirección estándar para aplicaciones de escritorio
            # Google permite esta URI sin configuración adicional
            redirect_uri = "http://localhost:8080"
            
            _logger.info(f"Iniciando OAuth2 para {self.email} con redirect_uri: {redirect_uri}")
            
            flow.redirect_uri = redirect_uri
            
            # Generar URL de autorización
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            # Guardar datos del flow (no el objeto completo para evitar problema con pickle)
            self._save_flow_data(state, SCOPES, redirect_uri)
            
            return auth_url
            
        except Exception as e:
            _logger.error(f"Error generando URL OAuth2: {e}")
            raise

    def _save_flow_data(self, state, scopes, redirect_uri):
        """Guardar datos del flow para el callback"""
        addon_path = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(addon_path, 'temp')
        flow_data_path = os.path.join(temp_dir, f'flow_data_{self.id}.json')
        
        flow_data = {
            'config_id': self.id,
            'state': state,
            'scopes': scopes,
            'credentials_path': self._get_temp_credentials_path(),
            'redirect_uri': redirect_uri
        }
        
        with open(flow_data_path, 'w') as f:
            json.dump(flow_data, f)
        
        # También guardar mapeo state -> config_id para el callback
        state_map_path = os.path.join(temp_dir, 'oauth_state_map.json')
        try:
            with open(state_map_path, 'r') as f:
                state_map = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            state_map = {}
        
        state_map[state] = self.id
        
        with open(state_map_path, 'w') as f:
            json.dump(state_map, f)

    def complete_oauth_flow(self, authorization_code):
        """Completar flujo OAuth2 con el código de autorización"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            # Cargar datos del flow guardados
            addon_path = os.path.dirname(os.path.dirname(__file__))
            flow_data_path = os.path.join(addon_path, 'temp', f'flow_data_{self.id}.json')
            
            with open(flow_data_path, 'r') as f:
                flow_data = json.load(f)
            
            # Recrear el flow desde los datos guardados
            flow = InstalledAppFlow.from_client_secrets_file(
                flow_data['credentials_path'], 
                flow_data['scopes']
            )
            flow.redirect_uri = flow_data['redirect_uri']
            
            # Intercambiar código por token
            flow.fetch_token(code=authorization_code)
            creds = flow.credentials
            
            # Guardar credenciales
            token_path = self._get_token_pickle_path()
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
            
            # Guardar en Odoo
            with open(token_path, 'rb') as f:
                self.token_pickle = base64.b64encode(f.read())
            
            self.is_authenticated = True
            self.last_auth_date = fields.Datetime.now()
            
            # Limpiar archivos temporales
            self._cleanup_temp_files()
            
            _logger.info(f"OAuth2 completado exitosamente para {self.email}")
            
        except Exception as e:
            _logger.error(f"Error completando OAuth2: {e}")
            raise UserError(f"Error completando autenticación: {str(e)}")

    def get_credentials(self):
        """Obtener credenciales válidas para usar en SMTP"""
        if not self.is_authenticated:
            raise UserError("Esta configuración no está autenticada. Ejecuta la autenticación OAuth2 primero.")
        
        try:
            # Cargar credenciales desde pickle
            token_path = self._get_token_pickle_path()
            
            # Si no existe el archivo, intentar recrearlo desde el campo binario
            if not os.path.exists(token_path) and self.token_pickle:
                with open(token_path, 'wb') as f:
                    f.write(base64.b64decode(self.token_pickle))
            
            with open(token_path, 'rb') as f:
                creds = pickle.load(f)
            
            # Verificar si necesita refresh
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                
                # Guardar credenciales actualizadas
                with open(token_path, 'wb') as f:
                    pickle.dump(creds, f)
                
                with open(token_path, 'rb') as f:
                    self.token_pickle = base64.b64encode(f.read())
            
            return creds
            
        except Exception as e:
            _logger.error(f"Error obteniendo credenciales para {self.email}: {e}")
            raise UserError(f"Error obteniendo credenciales: {str(e)}")

    def test_credentials(self):
        """Probar las credenciales"""
        try:
            creds = self.get_credentials()
            
            # Probar enviando un email de prueba
            from googleapiclient.discovery import build
            
            service = build('gmail', 'v1', credentials=creds)
            
            # Verificar que podemos acceder al perfil
            profile = service.users().getProfile(userId='me').execute()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Credenciales Válidas',
                    'message': f'Credenciales OAuth2 funcionando correctamente para {profile.get("emailAddress", self.email)}',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"Error probando credenciales: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ Error en Credenciales',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                }
            }

    def _cleanup_temp_files(self):
        """Limpiar archivos temporales"""
        try:
            addon_path = os.path.dirname(os.path.dirname(__file__))
            temp_dir = os.path.join(addon_path, 'temp')
            
            files_to_remove = [
                f'credentials_{self.id}.json',
                f'flow_data_{self.id}.json'
            ]
            
            for filename in files_to_remove:
                file_path = os.path.join(temp_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Limpiar entrada del mapeo de states
            try:
                state_map_path = os.path.join(temp_dir, 'oauth_state_map.json')
                if os.path.exists(state_map_path):
                    with open(state_map_path, 'r') as f:
                        state_map = json.load(f)
                    
                    # Remover entradas que apunten a este config_id
                    state_map = {k: v for k, v in state_map.items() if v != self.id}
                    
                    with open(state_map_path, 'w') as f:
                        json.dump(state_map, f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass  # El archivo no existe o está corrupto, no hay problema
                    
        except Exception as e:
            _logger.warning(f"No se pudieron limpiar archivos temporales: {e}")

    @api.model
    def get_config_for_email(self, email):
        """Obtener configuración OAuth2 para un email específico"""
        config = self.search([
            ('email', '=', email),
            ('active', '=', True),
            ('is_authenticated', '=', True)
        ], limit=1)
        
        return config if config else None

    @api.model
    def get_config_by_state(self, state):
        """Obtener configuración OAuth2 por estado de autorización"""
        try:
            addon_path = os.path.dirname(os.path.dirname(__file__))
            state_map_path = os.path.join(addon_path, 'temp', 'oauth_state_map.json')
            
            with open(state_map_path, 'r') as f:
                state_map = json.load(f)
            
            config_id = state_map.get(state)
            if config_id:
                return self.browse(config_id)
            
            return None
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            _logger.warning(f"No se encontró configuración para state: {state}")
            return None

    def _get_addon_path(self):
        """Obtener ruta del addon (método público para el controlador)"""
        return os.path.dirname(os.path.dirname(__file__))

    def action_auto_configure_mail_server(self):
        """Auto-configurar servidor de correo después de autenticación exitosa"""
        self.ensure_one()
        
        if not self.is_authenticated:
            raise UserError("Primero debes completar la autenticación OAuth2")
        
        try:
            # Buscar si ya existe un servidor para este email
            existing_server = self.env['ir.mail_server'].search([
                ('smtp_user', '=', self.email)
            ], limit=1)
            
            server_values = {
                'name': f'Gmail OAuth2 - {self.email}',
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_user': self.email,
                'smtp_pass': '',  # OAuth2 no usa contraseña
                'smtp_encryption': 'starttls',
                'smtp_authentication': 'gmail_oauth2',  # Usar nuestro tipo personalizado
                'active': True,
                'sequence': 1  # Prioridad alta
            }
            
            if existing_server:
                # Actualizar servidor existente
                existing_server.write(server_values)
                server = existing_server
                action_msg = "actualizado"
            else:
                # Crear nuevo servidor
                server = self.env['ir.mail_server'].create(server_values)
                action_msg = "creado"
            
            # Opcionalmente, desactivar otros servidores para evitar conflictos
            other_servers = self.env['ir.mail_server'].search([
                ('id', '!=', server.id),
                ('active', '=', True)
            ])
            if other_servers:
                _logger.info(f"Desactivando {len(other_servers)} servidores de correo existentes")
                # No los desactivamos automáticamente, solo informamos
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Servidor de Correo Configurado!',
                    'message': f'Servidor de correo {action_msg} exitosamente para {self.email}. Ve a Configuración → Email → Servidores de Correo para ver la configuración.',
                    'type': 'success',
                    'sticky': True,
                    'links': [{
                        'label': 'Ver Servidores de Correo',
                        'url': '/web#action=base.action_ir_mail_server_list'
                    }]
                }
            }
            
        except Exception as e:
            _logger.error(f"Error auto-configurando servidor de correo: {e}")
            raise UserError(f"Error configurando servidor de correo: {str(e)}")
