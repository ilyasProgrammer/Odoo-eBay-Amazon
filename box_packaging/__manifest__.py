# -*- coding: utf-8 -*-

{
    'name': 'Box Packaging',
    'summary': 'Inventory of box packaging',
    'description': """
This module provides to manage the inventory of box packaging in odoo.
====================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['sale_stock'],
    'data': [
        'views/box_packaging.xml',
        'wizard/select_exist_box_view.xml',
    ],
    'installable': True,
}
