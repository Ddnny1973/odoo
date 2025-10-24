# __manifest__.py
# Módulo Odoo para mostrar el QR de WhatsApp
{
    'name': 'WhatsApp QR Connector',
    'version': '1.0',
    'summary': 'Permite mostrar el QR de vinculación de WhatsApp desde Odoo',
    'author': 'Tu Nombre',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_qr_view.xml',
    ],
    'icon': '/odoo_whatsapp_qr/static/description/icon.png',
    'installable': True,
    'application': True,
}
