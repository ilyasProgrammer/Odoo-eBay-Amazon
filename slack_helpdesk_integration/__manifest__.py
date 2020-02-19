# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Slack Integration with Helpdesk",
    'summary': "Slack Integration with Helpdesk",
    'description': """
Slack Integration with Helpdesk
====================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    "external_dependencies": {
        "python": [
            "slackclient",
        ],
    },
    'depends': ['helpdesk', 'helpdesk_recurring'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
