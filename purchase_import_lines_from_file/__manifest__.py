# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Purchase - Import Lines From CSV",
    'summary': "Enable importing of purchase order lines from file",
    'description': """
Enable importing of purchase order lines from file
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_dropship'],
    # always loaded
    'data': [
        'views/purchase_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
