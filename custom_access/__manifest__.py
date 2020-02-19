# -*- coding: utf-8 -*-

{
    'name': "custom_access",
    'summary': "custom_access rights",
    'description': """custom_access""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_dropship',
                'product_auto_attributes',
                'stock_update_store_real_time',
                'custom_business_reports',
                ],
    'data': [
        'groups.xml',
        'ir.model.access.csv',
        'menu.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
}
