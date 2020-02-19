# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sales - Online Stores Integration",

    'summary': """
        Integrate with Amazon and eBay Stores""",

    'description': """
        This is the base module to enable connecting to Amazon and eBay stores
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale','stock', 'sale_stock', 'mrp'],
    'external_dependencies': {'python': ['pymssql']},
    'data': [
        'data/sale_store_data.xml',
        'security/ir.model.access.csv',
        'wizard/add_listing_wizard_views.xml',
        'wizard/bulk_listing_wizard_views.xml',
        'wizard/get_order_views.xml',
        'views/carrier_views.xml',
        'views/product_views.xml',
        'views/store_views.xml',
        'views/sale_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/stock_pack_operation_views.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
