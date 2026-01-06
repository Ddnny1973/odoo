{
    'name': 'GC Apartamentos',
    'version': '1.0.0',
    'author': 'Gestor Consultoría',
    'category': 'Real Estate',
    'summary': 'Gestión de apartamentos y unidades habitacionales',
    'description': 'Módulo para la gestión de apartamentos, edificios y unidades en Odoo Community 18.',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/apartamento_views.xml',
    ],
    'demo': [
        # Agrega aquí los archivos XML de datos demo si los hay
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
