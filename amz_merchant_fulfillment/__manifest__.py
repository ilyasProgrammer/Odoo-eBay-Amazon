# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Amazon - Merchant Fulfillment",
    'summary': "Amazon - Merchant Fulfillment",
    'description': """
Merchant Fulfillment for Amazon
====================
* Additional workflow for order processing
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': [
        'sale_store_amazon',
        'stock_update_store_real_time',
        'amz_feedback_request',
        # 'returns_management',
    ],
    'data': [
        # 'data/fbm_data.xml',
        'data/cron_data.xml',
        'security/ir.model.access.csv',
        'wizard/get_order_wizard_views.xml',
        'wizard/update_shipping_template_wizard_views.xml',
        'views/carrier_views.xml',
        'views/product_listing_views.xml',
        'views/sale_order_views.xml',
        'views/store_views.xml',
        'views/stock_picking_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
