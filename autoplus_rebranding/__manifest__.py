# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Autoplus Rebranding",
    'summary': """
        Autoplus Rebranding""",
    'description': """
        This is the base module for autoplus rebranding
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['web_enterprise'],
    'qweb': [
        'static/src/xml/autoplus_rebranding.xml',
    ],
    'data': [
        'views/autoplus_title.xml',
    ],
    'license': 'OEEL-1',
}