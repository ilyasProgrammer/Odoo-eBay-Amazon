# -*- coding: utf-8 -*-

{
    'name': "helpdesk_archive",
    'summary': "helpdesk_archive",
    'description': """Archive done tasks automatically if it is older than 14 days""",
    'author': 'Opsyst',
    'developer': 'Ilyas',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['helpdesk'],
    'data': [
        'cron.xml',
    ],
    'demo': [
    ],
    'application': True,
    'license': 'OEEL-1',
}
