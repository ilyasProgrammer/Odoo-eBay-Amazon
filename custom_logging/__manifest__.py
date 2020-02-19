# -*- coding: utf-8 -*-

{
    'name': "custom_logging",
    'summary': "custom_logging",
    'description': """custom_logging""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['base'],
    "external_dependencies": {
            "python": [
                "slackclient",
            ],
        },
    'data': [
        'data.xml'
    ],
    'demo': [],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
}
