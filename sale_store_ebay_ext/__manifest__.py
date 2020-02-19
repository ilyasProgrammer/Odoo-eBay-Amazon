# -*- coding: utf-8 -*-

{
    'name': "sale_store_ebay_ext",
    'summary': """sale_store_ebay_ext""",
    'description': """Extention""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'category': 'Sales',
    'version': '1.0',
    'depends': ['sale_store','listing_template'],
    'data': [
        'views/store_views.xml',
        'views/order.xml',
        'data.xml'
    ],
    'application': False,
    'license': 'OEEL-1',
}
