# -*- coding: utf-8 -*-

{
    'name': 'Digital Ocean Backup',
    'summary': 'Digital Ocean Backup',
    'description': 'Digital Ocean Backup',
    'category': 'Database',
    'version': '1.0',
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/digital_ocean_views.xml',
    ],
    'installable': True,
}