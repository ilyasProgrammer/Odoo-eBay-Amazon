# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "DO Server Management",
    'summary': "Manage Digital Ocean servers in Odoo",
    'description': """
Automate daily creattion of snapshot of one or more servers
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['base'],
    # always loaded
    'data': [
    ],
    'demo': [
    ],
    'external_dependencies': {'python': ['digitalocean']},
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
