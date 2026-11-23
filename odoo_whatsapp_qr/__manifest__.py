# __manifest__.py
# Módulo Odoo para mostrar el QR de WhatsApp
{
    'name': 'WhatsApp QR Connector',
    'version': '1.1',
    'summary': 'Permite mostrar el QR de vinculación de WhatsApp desde Odoo',
    'author': 'Tu Nombre',
    'category': 'Tools',
    'depends': ['base', 'portal', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'security/whatsapp_qr_security.xml',
        'views/whatsapp_qr_view.xml',
        'views/portal_whatsapp_qr_templates.xml',
        'views/portal_home_inherit.xml',
    ],
    'icon': '/odoo_whatsapp_qr/static/description/icon.png',
    'installable': True,
    'application': True,
}
