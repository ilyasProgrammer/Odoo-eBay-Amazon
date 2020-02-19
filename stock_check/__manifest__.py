# -*- coding: utf-8 -*-

{
    'name': "Stock Checks",
    'description': """
Database provision for scheduled store stock checks
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['stock', 'sale_store_ebay', 'sale_store_amazon', 'sale_dropship'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_report_views.xml',
        'views/quant_views.xml',
        'views/stock_change_product_qty_views.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
