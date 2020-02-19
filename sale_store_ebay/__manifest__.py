# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale - eBay Integration",

    'summary': """
        Integrate with eBay
""",

    'description': """
Available Features
Get orders from eBay
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'category': 'Sales',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_store','ship_shipstation'],

    # always loaded
    'data': [
        'data/ebay_data.xml',
        'wizard/revise_item_wizard_views.xml',
        'views/store_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
