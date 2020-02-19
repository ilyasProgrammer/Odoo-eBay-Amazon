# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock - ZPL Printing",

    'summary': """
        Print barcodes/labels thru QZ Tray API""",

    'description': """
        Print barcodes and shipping labels in
        * Stock Picking Document
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store','stock_barcode'],
    'data': [
        'templates/stock_picking_templates.xml',
        'views/stock_picking_views.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
