# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale - Custom Dropshipping",

    'summary': """
        Dropshipping with LKQ and PFG""",

    'description': """
        Set routing in sales module depending on availability of stock
        If stock is not available, check dropshippers
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['stock_dropshipping','sale_store', 'purchase', 'ship_shipstation', 'sale_store_ebay', 'sale_store_amazon'],
    'data': [
        'security/ir.model.access.csv',
        'data/dropship_data.xml',
        'data/email_data.xml',
        'wizard/report_sale_details.xml',
        'wizard/purchase_send_po_to_ppr_wizard_views.xml',
        'views/sale_views.xml',
        'views/procurement_views.xml',
        'views/purchase_views.xml',
        'views/purchase_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'views/product_view.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
