# models/mail_server_gmail.py
import base64
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

_logger = logging.getLogger(__name__)

class MailServerGmail(models.Model):
    _inherit = 'ir.mail_server'
    
    # Extender campo de autenticación para incluir OAuth2
    smtp_authentication = fields.Selection(
        selection_add=[
            ('gmail_oauth2', 'OAuth2 Específico'),
            ('gmail_oauth2_gdrive', 'OAuth2 desde Google Drive')
        ],
        ondelete={
            'gmail_oauth2': 'set default',
            'gmail_oauth2_gdrive': 'set default'
        }
    )
    
    @api.depends('smtp_authentication')
    def _compute_smtp_authentication_info(self):
        """Override para incluir información de OAuth2"""
        for server in self:
            if server.smtp_authentication == 'gmail_oauth2':
                server.smtp_authentication_info = _(
                    'Autenticación OAuth2 específica para Gmail.\n'
                    'Requiere configuración OAuth2 independiente en Configuración → Email → 📧 OAuth2 Gmail.\n'
                    'Esta es la forma más segura y recomendada para cualquier cuenta Gmail.'
                )
            elif server.smtp_authentication == 'gmail_oauth2_gdrive':
                server.smtp_authentication_info = _(
                    'Autenticación OAuth2 reutilizando credenciales de Google Drive.\n'
                    'Solo funciona si el email es exactamente la misma cuenta configurada en Google Drive.\n'
                    'Requiere que Google Drive esté configurado previamente.'
                )
            else:
                # Llamar al método padre para otros tipos de autenticación
                super(MailServerGmail, self)._compute_smtp_authentication_info()
    
    def _get_google_credentials(self):
        """Obtener credenciales de Google específicas para Gmail"""
        try:
            # Buscar configuración OAuth2 específica para este email
            oauth_config = self.env['gmail.oauth2.config'].get_config_for_email(self.smtp_user)
            
            if oauth_config:
                _logger.info(f"✅ Usando configuración OAuth2 específica para {self.smtp_user}")
                return oauth_config.get_credentials()
            
            # Si no hay configuración específica, verificar si hay configuración de Google Drive
            # y solo usarla si el usuario la configuró explícitamente como fallback
            if self.smtp_authentication == 'gmail_oauth2_gdrive':
                _logger.info(f"🔄 Usando credenciales de Google Drive como fallback explícito para {self.smtp_user}")
                
                google_drive_config = self.env['google.drive.config']
                creds, gc, servicio_drive = google_drive_config.autenticar_google_drive()
                
                if creds and creds.valid:
                    # Verificar la cuenta de email asociada
                    user_email = self._get_user_email_from_credentials(creds)
                    _logger.info(f"Email de credenciales Google Drive: {user_email}")
                    _logger.info(f"Email del servidor SMTP: {self.smtp_user}")
                    
                    if user_email and self.smtp_user:
                        if user_email.lower() != self.smtp_user.lower():
                            raise UserError(
                                f"❌ Las credenciales de Google Drive están configuradas para '{user_email}' "
                                f"pero el servidor SMTP está configurado para '{self.smtp_user}'.\n\n"
                                f"💡 SOLUCIONES:\n"
                                f"1. Configurar OAuth2 específico para Gmail: Configuración → 📧 OAuth2 Gmail\n"
                                f"2. Usar la misma cuenta '{user_email}' para el servidor SMTP\n"
                                f"3. Usar contraseña de aplicación en lugar de OAuth2"
                            )
                    
                    return creds
                else:
                    raise UserError(
                        "❌ No se encontraron credenciales de Google Drive válidas.\n\n"
                        "💡 OPCIONES:\n"
                        "1. Configurar OAuth2 específico para Gmail: Configuración → 📧 OAuth2 Gmail\n"
                        "2. Configurar Google Drive correctamente\n"
                        "3. Usar contraseña de aplicación"
                    )
            else:
                # No hay configuración OAuth2 específica y no está configurado el fallback
                raise UserError(
                    f"❌ No se encontró configuración OAuth2 para '{self.smtp_user}'.\n\n"
                    f"💡 CONFIGURA OAUTH2 ESPECÍFICO:\n"
                    f"1. Ve a Configuración → Email → 📧 OAuth2 Gmail\n"
                    f"2. Crea una nueva configuración para '{self.smtp_user}'\n"
                    f"3. Sigue la guía paso a paso\n"
                    f"4. Luego cambia este servidor a 'OAuth2 Específico'\n\n"
                    f"🔄 ALTERNATIVA - Usar Google Drive (solo si es la misma cuenta):\n"
                    f"• Cambia la autenticación a 'OAuth2 desde Google Drive'\n\n"
                    f"🔑 OPCIÓN SIMPLE:\n"
                    f"• Usa 'Contraseña de Aplicación' en lugar de OAuth2"
                )
        except Exception as e:
            _logger.error(f"Error obteniendo credenciales de Google: {e}")
            raise UserError(f"Error al obtener credenciales de Google: {str(e)}")
    
    def _get_user_email_from_credentials(self, creds):
        """Obtener el email del usuario desde las credenciales"""
        try:
            if hasattr(creds, 'id_token') and creds.id_token:
                # Decodificar ID token para obtener el email
                import json
                import base64
                
                # El ID token es un JWT, tomamos la parte del payload
                parts = creds.id_token.split('.')
                if len(parts) >= 2:
                    # Agregar padding si es necesario
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    
                    decoded = base64.urlsafe_b64decode(payload)
                    token_data = json.loads(decoded)
                    return token_data.get('email')
            
            # Si no podemos obtener el email del token, usar la API de Google
            try:
                from googleapiclient.discovery import build
                service = build('oauth2', 'v2', credentials=creds)
                user_info = service.userinfo().get().execute()
                return user_info.get('email')
            except Exception as api_error:
                _logger.warning(f"No se pudo obtener email desde la API: {api_error}")
                return None
                
        except Exception as e:
            _logger.warning(f"No se pudo obtener email del usuario: {e}")
            return None
    
    def _generate_oauth2_string(self, username, access_token):
        """Generar string de autenticación OAuth2 para SMTP"""
        auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"
        return base64.b64encode(auth_string.encode()).decode()
    
    def _smtp_login_oauth2(self, connection, smtp_user):
        """Realizar login SMTP usando OAuth2"""
        try:
            # Obtener credenciales de Google
            creds = self._get_google_credentials()
            
            # Refrescar token si es necesario
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            
            # Generar string de autenticación OAuth2
            oauth2_string = self._generate_oauth2_string(smtp_user, creds.token)
            
            # Realizar autenticación
            connection.ehlo()
            connection.docmd('AUTH', f'XOAUTH2 {oauth2_string}')
            
            _logger.info(f"✅ Autenticación OAuth2 exitosa para {smtp_user}")
            return True
            
        except Exception as e:
            _logger.error(f"❌ Error en autenticación OAuth2: {e}")
            raise UserError(f"Error en autenticación OAuth2: {str(e)}")
    
    def _smtp_login(self, connection, smtp_user, smtp_password):
        """Override del método de login SMTP para soportar OAuth2"""
        if self.smtp_authentication in ['gmail_oauth2', 'gmail_oauth2_gdrive'] and 'gmail' in (self.smtp_host or '').lower():
            return self._smtp_login_oauth2(connection, smtp_user)
        else:
            # Usar autenticación normal
            return super()._smtp_login(connection, smtp_user, smtp_password)
    
    def test_smtp_connection(self):
        """Probar conexión SMTP con mejor manejo de errores"""
        try:
            _logger.info(f"Probando conexión SMTP - Autenticación: {self.smtp_authentication}")
            
            smtp = None
            if self.smtp_authentication in ['gmail_oauth2', 'gmail_oauth2_gdrive']:
                _logger.info(f"Probando conexión OAuth2 para Gmail ({self.smtp_authentication})")
                
                # Verificar credenciales antes de intentar conexión
                creds = self._get_google_credentials()
                if not creds:
                    raise UserError("No se encontraron credenciales válidas")
                
                _logger.info(f"Credenciales válidas encontradas, expiran: {creds.expiry}")
                
                # Probar conexión OAuth2
                smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)
                smtp.starttls()
                self._smtp_login_oauth2(smtp, self.smtp_user)
                smtp.quit()
                
                auth_type = "OAuth2 Específico" if self.smtp_authentication == 'gmail_oauth2' else "OAuth2 desde Google Drive"
                _logger.info(f"Conexión {auth_type} exitosa")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': f'✅ Conexión {auth_type} Exitosa',
                        'message': f'Conexión establecida correctamente con {self.smtp_host}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                _logger.info("Usando autenticación estándar")
                # Usar método padre para otras autenticaciones
                return super().test_smtp_connection()
                
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Error en test_smtp_connection: {error_msg}")
            
            # Detectar errores específicos y dar soluciones
            if "Username and Password not accepted" in error_msg:
                suggestion = (
                    "Se requiere contraseña de aplicación o OAuth2. "
                    "Habilita 'Gmail OAuth2' o genera una contraseña de aplicación en Gmail."
                )
            elif "BadCredentials" in error_msg:
                suggestion = "Credenciales inválidas. Verifica la configuración de Google Drive."
            else:
                suggestion = "Verifica la configuración del servidor SMTP."
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '❌ Error de Conexión',
                    'message': f'{error_msg}\n\n💡 Sugerencia: {suggestion}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        finally:
            if smtp:
                try:
                    smtp.quit()
                except:
                    pass

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_debug=False, smtp_session=None):
        """Override para mejor logging de errores SMTP"""
        try:
            return super().send_email(
                message, mail_server_id, smtp_server, smtp_port,
                smtp_user, smtp_password, smtp_encryption,
                smtp_debug, smtp_session
            )
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"💥 Error enviando email: {error_msg}")
            
            # Log detallado para debugging
            _logger.error(f"📧 Detalles del envío:")
            _logger.error(f"   Server: {smtp_server or self.smtp_host}")
            _logger.error(f"   Port: {smtp_port or self.smtp_port}")
            _logger.error(f"   User: {smtp_user or self.smtp_user}")
            _logger.error(f"   Encryption: {smtp_encryption or self.smtp_encryption}")
            
            # Propagar el error para que lo maneje el método enviar_correo
            raise
