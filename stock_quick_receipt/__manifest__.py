# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock - Quick Receipt Process",
    'summary': "Quick receipt process of inventory",
    'description': """
Quick receipt process of inventory
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['barcodes','purchase'],
    'data': [
        'data/quick_receipt_data.xml',
        'security/ir.model.access.csv',
        'views/quick_receipt_views.xml',
        'views/quick_transfer_views.xml',
        'views/stock_picking_views.xml',
        'views/barcode_assets.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
