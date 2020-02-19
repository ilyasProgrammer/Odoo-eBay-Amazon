# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Secondary Store Connector",
    'summary': "Accept orders from secondary stores",
    'description': """
Accept orders from secondary stores
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store_ebay'],
    # always loaded
    'data': [
        'data/connector_data.xml',
        'views/res_config_settings_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
