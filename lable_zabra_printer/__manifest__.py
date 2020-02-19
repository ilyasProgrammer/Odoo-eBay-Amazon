# -*- coding: utf-8 -*-

{
    'name': 'Label Print In Zebra',
    'summary': 'Label Print In Zebra',
    'description': """
This module provides Print Label In Zebra Printre
====================================================================================

    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['sale', 'barcodes', 'product'],
    'data': [
        'views/zebra_printer_view.xml',
        'views/res_company_view.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    'installable': True,
}
