# -*- coding: utf-8 -*-

{
    'name': "Interchange Part Numbers",
    'summary': "Get interchange numbers from AutoPlus",
    'description': """
Get interchange numbers from AutoPlus
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store','product_template_with_listing'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_brand_sync_views.xml',
        'wizard/product_sync_views.xml',
        'wizard/common.xml',
        'views/product_interchange_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
