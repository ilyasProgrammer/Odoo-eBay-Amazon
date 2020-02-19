# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sales - Shipstation Integration",

    'summary': """
    Integrate with Shipstation""",

    'description': """
    Send order to shipstation
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store', 'stock_barcode', 'lable_zabra_printer'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/sale_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/shipment_from_vendor_views.xml',
        'views/store_views.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
