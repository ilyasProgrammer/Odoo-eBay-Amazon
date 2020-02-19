# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Shipping - Amazon Automation",
    'summary': "Shipping - Amazon Automation",
    'description': """
Shipping - Amazon Automation
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['ship_shipstation'],
    'data': [
        'data/cron_data.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
