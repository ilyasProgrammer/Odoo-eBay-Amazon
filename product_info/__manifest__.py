# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Product Info From AutoPlus",
    'summary': "Expose more product information",
    'description': """
Make product information available through a web page
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store', 'sale_dropship'],
    'data': [
        'templates/product_info_templates.xml',
        'templates/assets_templates.xml',
        'wizard/purchase_update_vendor_qty_views.xml',
        'views/product_views.xml'
    ],
    'qweb': [
        'static/xml/product_info.xml'
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
