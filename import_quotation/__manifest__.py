# -*- coding: utf-8 -*-

{
    'name': 'Import Quotation',
    'summary': 'Import Quotation',
    'version': '1.0',
    'description': """
This module provides import quotation
====================================================================================

    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['sale_store', 'sale_dropship'],
    'data': [
        'views/sale_order_views.xml',
        'wizard/create_quotation_wiz.xml',
        'wizard/import_quotation_wiz.xml',
    ],
    'installable': True,
}
