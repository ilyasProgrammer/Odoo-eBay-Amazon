# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "UPS SurePost Integration",
    'summary': "UPS SurePost Integration",
    'description': """
UPS SurePost Integration
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['ship_shipstation','ship_ups'],
    'data': [
        'data/ups_surepost_data.xml',
        'views/carrier_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
