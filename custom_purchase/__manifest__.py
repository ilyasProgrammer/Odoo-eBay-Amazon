# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Custom Purchase",
    'summary': """
        Add ASE Fields and CSV in mail attachment""",

    'description': """
        Add ASE Fields and CSV in mail attachment
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['mail', 'purchase'],
    'data': [
        'views/purchase_views.xml',
    ],
}
