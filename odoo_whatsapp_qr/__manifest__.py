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
    'installable': True,
    'application': True,
}
