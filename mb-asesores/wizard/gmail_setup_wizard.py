# wizard/gmail_setup_wizard.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class GmailSetupWizard(models.TransientModel):
    _name = 'gmail.setup.wizard'
    _description = 'Asistente de Configuración Gmail'

    setup_type = fields.Selection([
        ('oauth2', 'OAuth2 Específico (Recomendado)'),
        ('oauth2_specific', 'OAuth2 Específico (Recomendado)'),
        ('oauth2_drive', 'OAuth2 desde Google Drive'),
        ('app_password', 'Contraseña de Aplicación'),
        ('alternative', 'Servidor Alternativo')
    ], string='Tipo de Configuración', required=True, default='oauth2')
    
    gmail_user = fields.Char(string='Email de Gmail', placeholder='tu-email@gmail.com')
    app_password = fields.Char(string='Contraseña de Aplicación', help='Solo para configuración con contraseña de aplicación')
    
    # Configuración alternativa
    smtp_host = fields.Char(string='Servidor SMTP', default='smtp-mail.outlook.com')
    smtp_port = fields.Integer(string='Puerto', default=587)
    smtp_user = fields.Char(string='Usuario')
    smtp_pass = fields.Char(string='Contraseña')
    
    state = fields.Selection([
        ('step1', 'Configuración'),
        ('step2', 'Verificación'),
        ('done', 'Completado')
    ], default='step1')
    
    test_result = fields.Text(string='Resultado de Prueba', readonly=True)

    @api.onchange('setup_type')
    def _onchange_setup_type(self):
        if self.setup_type == 'alternative':
            self.smtp_host = 'smtp-mail.outlook.com'
            self.smtp_port = 587
        else:
            self.smtp_host = 'smtp.gmail.com'
            self.smtp_port = 587

    @api.model
    def create(self, vals):
        """Override create to allow empty wizard creation"""
        # For transient models, we allow creation without validation
        # Validation will happen when user clicks "Next"
        return super(GmailSetupWizard, self).create(vals)

    def write(self, vals):
        """Override write to allow updates without validation"""
        # For transient models, we allow updates without validation
        # Validation will happen when user clicks "Next"
        return super(GmailSetupWizard, self).write(vals)

    def action_next_step(self):
        """Ir al siguiente paso del wizard"""
        # Force refresh to ensure we have the latest field values
        self.ensure_one()
        
        # Check if we need to save first (for field updates from the UI)
        if self.env.context.get('save_first'):
            # The form should already be saved before this method is called
            pass
            
        # Re-read the record to ensure we have latest values
        self.refresh()
        
        if self.state == 'step1':
            self._validate_step1()
            self.state = 'step2'
            return self._return_wizard()
        elif self.state == 'step2':
            return self._create_mail_server()

    def _validate_step1(self):
        """Validar datos del paso 1"""
        # Force refresh to get latest values
        self.refresh()
        
        _logger.info(f"Validando paso 1 - setup_type: {self.setup_type}, gmail_user: '{self.gmail_user}', smtp_user: '{self.smtp_user}'")
        _logger.info(f"Valores de campos: gmail_user='{repr(self.gmail_user)}', len={len(self.gmail_user) if self.gmail_user else 0}")
        
        # Validar campos requeridos según el tipo de configuración
        if self.setup_type in ('oauth2', 'oauth2_specific', 'oauth2_drive', 'app_password'):
            gmail_user_value = self.gmail_user or ''
            gmail_user_clean = gmail_user_value.strip()
            
            if not gmail_user_clean:
                raise UserError(f"El email de Gmail es obligatorio para este tipo de configuración. Valor actual: '{repr(self.gmail_user)}'")
            if '@' not in gmail_user_clean or '.' not in gmail_user_clean:
                raise UserError("Por favor ingresa un email de Gmail válido.")
        elif self.setup_type == 'alternative':
            smtp_user_value = self.smtp_user or ''
            smtp_user_clean = smtp_user_value.strip()
            
            if not smtp_user_clean:
                raise UserError("El usuario SMTP es obligatorio para configuración alternativa.")
            if not self.smtp_pass or not self.smtp_pass.strip():
                raise UserError("La contraseña es obligatoria para configuración alternativa.")
            if not self.smtp_host or not self.smtp_host.strip():
                raise UserError("El servidor SMTP es obligatorio.")
        
        if self.setup_type in ('oauth2', 'oauth2_specific'):
            # Verificar que exista configuración OAuth2 específica
            oauth_config = self.env['gmail.oauth2.config'].get_config_for_email(gmail_user_clean)
            if not oauth_config:
                raise UserError(
                    f"❌ No existe configuración OAuth2 específica para '{gmail_user_clean}'.\n\n"
                    f"💡 SOLUCIÓN:\n"
                    f"1. Ve a Configuración → 📧 OAuth2 Gmail\n"
                    f"2. Crea una nueva configuración para '{gmail_user_clean}'\n"
                    f"3. Completa la autenticación OAuth2\n"
                    f"4. Regresa a este asistente\n\n"
                    f"O cambia a 'OAuth2 desde Google Drive' si la cuenta coincide."
                )
        
        elif self.setup_type == 'oauth2_drive':
            # Verificar que Google Drive esté configurado
            try:
                google_drive_config = self.env['google.drive.config']
                creds, gc, servicio_drive = google_drive_config.autenticar_google_drive()
                if not creds or not creds.valid:
                    raise UserError(
                        "Google Drive no está configurado correctamente. "
                        "Configura Google Drive primero para usar OAuth2."
                    )
                
                # Verificar si podemos obtener el email del usuario de las credenciales
                try:
                    # Crear un servidor temporal para verificar credenciales
                    temp_server = self.env['ir.mail_server'].new({
                        'smtp_user': gmail_user_clean,
                        'smtp_authentication': 'gmail_oauth2_gdrive'
                    })
                    
                    # Intentar obtener el email de las credenciales
                    user_email = temp_server._get_user_email_from_credentials(creds)
                    
                    if user_email and user_email.lower() != gmail_user_clean.lower():
                        raise UserError(
                            f"⚠️ ADVERTENCIA: Las credenciales de Google Drive están configuradas "
                            f"para '{user_email}' pero intentas configurar Gmail para '{gmail_user_clean}'.\n\n"
                            f"OPCIONES:\n"
                            f"1. Usar '{user_email}' como email de Gmail\n"
                            f"2. Cambiar a 'OAuth2 Específico' para '{gmail_user_clean}'\n"
                            f"3. Usar 'Contraseña de Aplicación'"
                        )
                    
                    if user_email:
                        _logger.info(f"Verificación OAuth2 Drive exitosa: cuenta {user_email} coincide con {gmail_user_clean}")
                    else:
                        _logger.warning("No se pudo verificar el email de las credenciales, pero OAuth2 está disponible")
                        
                except Exception as email_check_error:
                    _logger.warning(f"No se pudo verificar la coincidencia de emails: {email_check_error}")
                    # Continuar sin verificación de email - las credenciales podrían funcionar igual
                
            except Exception as e:
                _logger.error(f"Error verificando Google Drive: {e}")
                raise UserError(f"Error verificando Google Drive: {str(e)}")
        
        elif self.setup_type == 'app_password':
            if not self.app_password or not self.app_password.strip():
                raise UserError("Debes proporcionar la contraseña de aplicación de Gmail.")
            # Limpiar espacios y verificar longitud
            clean_password = self.app_password.replace(' ', '').replace('-', '')
            if len(clean_password) != 16:
                raise UserError("La contraseña de aplicación debe tener 16 caracteres.")

    def _create_mail_server(self):
        """Crear o actualizar servidor de correo"""
        try:
            _logger.info(f"Creando servidor de correo - setup_type: {self.setup_type}")
            
            # Buscar servidor existente
            search_user = self.smtp_user if self.setup_type == 'alternative' else self.gmail_user
            existing_server = self.env['ir.mail_server'].search([
                ('smtp_user', '=', search_user)
            ], limit=1)

            values = {
                'name': f'Gmail - {search_user}',
                'smtp_host': self.smtp_host,
                'smtp_port': self.smtp_port,
                'smtp_user': search_user,
                'smtp_encryption': 'starttls',
                'active': True
            }

            if self.setup_type in ('oauth2', 'oauth2_specific'):
                values.update({
                    'smtp_authentication': 'gmail_oauth2',
                    'smtp_pass': ''  # No se necesita contraseña con OAuth2
                })
                _logger.info("Configurando OAuth2 específico para Gmail")
            elif self.setup_type == 'oauth2_drive':
                values.update({
                    'smtp_authentication': 'gmail_oauth2_gdrive',
                    'smtp_pass': ''  # No se necesita contraseña con OAuth2
                })
                _logger.info("Configurando OAuth2 desde Google Drive para Gmail")
            elif self.setup_type == 'app_password':
                values.update({
                    'smtp_authentication': 'login',
                    'smtp_pass': self.app_password.replace(' ', '').replace('-', '')
                })
                _logger.info("Configurando contraseña de aplicación para Gmail")
            else:  # alternative
                values.update({
                    'smtp_authentication': 'login',
                    'smtp_pass': self.smtp_pass
                })
                _logger.info("Configurando servidor SMTP alternativo")

            _logger.info(f"Valores del servidor: {values}")

            if existing_server:
                existing_server.write(values)
                server = existing_server
                action_msg = "actualizado"
                _logger.info(f"Servidor actualizado: {server.id}")
            else:
                server = self.env['ir.mail_server'].create(values)
                action_msg = "creado"
                _logger.info(f"Servidor creado: {server.id}")

            # Probar la conexión
            try:
                test_result = server.test_smtp_connection()
                if test_result.get('params', {}).get('type') == 'success':
                    self.test_result = f"✅ Servidor {action_msg} y probado exitosamente."
                else:
                    self.test_result = f"⚠️ Servidor {action_msg} pero la prueba falló: {test_result.get('params', {}).get('message', 'Error desconocido')}"
            except Exception as e:
                self.test_result = f"⚠️ Servidor {action_msg} pero la prueba falló: {str(e)}"

            self.state = 'done'
            return self._return_wizard()

        except Exception as e:
            raise UserError(f"Error creando servidor de correo: {str(e)}")

    def _return_wizard(self):
        """Retornar acción para mantener el wizard abierto"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gmail.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }

    def action_open_mail_servers(self):
        """Abrir lista de servidores de correo"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Servidores de Correo',
            'res_model': 'ir.mail_server',
            'view_mode': 'tree,form',
            'domain': [('smtp_user', '=', self.gmail_user if self.setup_type != 'alternative' else self.smtp_user)],
            'context': {'create': False}
        }

    def action_view_documentation(self):
        """Abrir documentación"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/mb-asesores/static/SOLUCION_GMAIL_SMTP.md',
            'target': 'new'
        }
