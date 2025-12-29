# __manifest__.py
{
    'name': 'MB Asesores',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Módulo personalizado para MB Asesores',
    'author': 'Gestor Consultoría',
    'depends': ['base', 'mail'],
    'external_dependencies': {
        'python': [
            'google-auth',
            'google-auth-oauthlib', 
            'google-auth-httplib2',
            'google-api-python-client'
        ]
    },
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/vencimientos_views.xml',
        'views/google_drive_config_views.xml',
        'views/correo_enviado_view.xml',
        'views/mail_plantillas.xml',
        'views/mail_server_gmail_simple.xml',
        'views/gmail_setup_wizard_views.xml',
        'views/gmail_oauth2_config_views.xml',
        'views/gmail_oauth2_templates.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'icon': '/mb_asesores/static/description/icon.png',
    'auto_install': False,

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
}