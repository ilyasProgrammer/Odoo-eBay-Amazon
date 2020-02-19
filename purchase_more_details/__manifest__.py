# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Purchase - More Details",
    'summary': "Advanced purchase features",
    'description': """
Advanced Purchase Features
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['purchase_import_lines_from_file'],
    'data': [
        'data/mail_data.xml',
        'views/purchase_views.xml',
        'views/res_partner_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
