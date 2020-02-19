# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale - Amazon Integration",

    'summary': """
        Integrate with Amazon""",

    'description': """
        Available Features
        Get orders from Amazon
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store','ship_shipstation'],
    'data': [
        'views/res_partner_views.xml',
        'views/store_views.xml',
        'cron.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
