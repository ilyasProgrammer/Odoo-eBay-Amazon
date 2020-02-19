# -*- coding: utf-8 -*-

{
    'name': "Returns Management",
    'summary': """
        Process returns from Amazon and eBay""",
    'description': """
        Process returns from Amazon and eBay
    """,
    'author': 'Ilyas',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_dropship', 'ship_shipstation', 'barcodes', 'stock_landed_costs_custom', 'autoplus_interchange'],
    'external_dependencies': {
        'python' : ['openpyxl'],
    },
    'data': [
        'data/returns_data.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'wizard/sale_return_wizard.xml',
        'wizard/load_returns.xml',
        'views/amz_return_message_views.xml',
        'views/barcode_assets.xml',
        'views/label_printing_assets.xml',
        'views/purchase_views.xml',
        'views/quick_return_views.xml',
        'views/return_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
        'views/store_views.xml',
        'views/attachment.xml',
        'views/returns_processing_templates.xml',
    ],
    'qweb': [
        "static/src/xml/returns_processing.xml",
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
