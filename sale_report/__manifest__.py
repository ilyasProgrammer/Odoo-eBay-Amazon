# -*- coding: utf-8 -*-

{
    'name': 'Sales Report',
    'summary': 'Sales Report',
    'description': """
This module provides dashboard and custom report of sale.
====================================================================================

    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['sales_team', 'sale_dropship'],
    'data': [
        'data/sale_report_data.xml',
        'views/sale_report_view.xml',
    ],
    'installable': True,
}
