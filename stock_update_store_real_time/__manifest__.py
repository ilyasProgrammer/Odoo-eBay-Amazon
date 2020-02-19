# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock - Real-Time Update of Stores",
    'summary': "Real-time update of stores",
    'description': """
Real-time update of stores
=================================================================================
Update handling time and inventory in Amazon when stock is sold out
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_dropship'],
    'data': [
        'data/repricer_data.xml',
        'data/mail_data.xml',
        'security/ir.model.access.csv',
        'views/product_listing_views.xml',
        'views/product_template_views.xml',
        'views/repricer_scheme_views.xml',
        'views/repricer_competitor_views.xml',
        # 'views/repricer_update_line_views.xml',
        'views/sales_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/store_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
