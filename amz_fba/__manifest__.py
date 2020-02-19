# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Amazon - FBA",
    'summary': "Amazon - FBA",
    'description': """
Amazon FBA
====================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['stock',
                'stock_landed_costs_custom',
                'sale_store_amazon',
                'lable_zabra_printer',
                'amz_merchant_fulfillment'],
    'data': [
        'wizard/print_fba_label_wizard_views.xml',
        'views/assets.xml',
        'views/fba_demand_views.xml',
        'views/product_listing_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'data/amz_data.xml',
        'views/stock_quant_views.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [
    ],
    # 'post_init_hook': 'set_amz_order_type',
    'application': False,
    'license': 'OEEL-1',
}
