# -*- coding: utf-8 -*-

{
    'name': "helpdesk_recurring",
    'summary': "helpdesk_recurring",
    'description': """helpdesk_recurring""",
    'author': 'Opsyst',
    'developer': 'Ilyas',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['helpdesk'],
    'data': [
        'views.xml',
        'cron.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'application': True,
    'license': 'OEEL-1',
}
