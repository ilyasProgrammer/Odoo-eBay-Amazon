# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock Barcode - Custom",

    'summary': """
        Custom barcode scanning""",

    'description': """
        Allow multiple barcodes to identify a product
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_store','stock_barcode','sale_dropship'],

    # always loaded
    'data': [
        'views/stock_inventory_views.xml',
        'views/stock_barcode_custom_templates.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
