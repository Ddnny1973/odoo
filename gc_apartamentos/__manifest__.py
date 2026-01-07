{
    'name': 'GC Apartamentos',
    'version': '1.0.0',
    'author': 'Gestor Consultoría',
    'category': 'Real Estate',
    'summary': 'Gestión de apartamentos y unidades habitacionales',
    'description': 'Módulo para la gestión de apartamentos, edificios y unidades en Odoo Community 18.',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/apartamento_views.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'web_icon': 'gc_apartamentos,static/description/icon.png',
    'installable': True,
    'application': True,
    'auto_install': False,
}
