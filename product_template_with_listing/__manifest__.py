# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "Product Templates with Listings",
    'summary': "Products with Listings",
    'description': """
Products with Listings
====================
Store warehouse and vendor data in a new table
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['stock_update_store_real_time'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_listing_views.xml',
        'views/product_template_listed_views.xml'
    ],
    'application': False,
    'license': 'OEEL-1',
}
