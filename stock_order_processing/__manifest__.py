# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock - Order Processing",
    'summary': "Order Processing",
    'description': """
Order Processing
======================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_dropship','barcodes','stock_packaging','stock_picking_wave', 'amz_merchant_fulfillment'],
    'data': [
        'security/ir.model.access.csv',
        'reports/box_barcodes_report_templates.xml',
        'views/order_processing_templates.xml',
        'views/order_processing_views.xml',
        'views/res_users_views.xml',
        'views/stock_picking_views.xml',
        'wizard/assign_picks_wizard_views.xml',
        'wizard/box_barcodes_wizard_views.xml',
        'wizard/wh_margins_report_wizard_views.xml',
    ],
    'qweb': [
        "static/src/xml/order_processing.xml",
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
