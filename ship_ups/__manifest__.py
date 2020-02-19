# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "UPS Integration",
    'summary': """
        Integrate with UPS tracking API""",

    'description': """
        Get status of a tracking number
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['ship_shipstation', 'stock'],
    'data': [
        'views/carrier_views.xml'
    ],
    'license': 'OEEL-1',
}
