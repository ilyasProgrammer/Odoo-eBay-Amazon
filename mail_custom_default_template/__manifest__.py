# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Mail - Custom Default Template",
    'summary': "Custom default template for mails",
    'description': """
Remove Sent by Company Name Using Odoo in mails
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['mail'],
    'data': [
        'data/mail_data.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
