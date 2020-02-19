# -*- coding: utf-8 -*-

{
    'name': "Stock - Packaging",
    'summary': "Track packages used",
    'description': """Track packages used in shipments""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['purchase_more_details'],
    'data': [
        'data/cron_data.xml',
        'data/mail_data.xml',
        'security/ir.model.access.csv',
        'wizard/packaging_warning_views.xml',
        'views/product_views.xml',
        'views/purchase_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_config_settings_views.xml',
        'views/box_lines.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
