# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sales - Custom Scripts",
    'summary': """
        Miscellaneous scripts""",

    'description': """
        Miscellaneous scripts
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store','sale_store_ebay'],
    'data': [
        'data/cron_data.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
