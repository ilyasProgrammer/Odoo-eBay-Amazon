# -*- coding: utf-8 -*-

{
    'name': "Sale tax",
    'summary': """Taxes handling for eBay and Amazon""",
    'description': """Taxes handling for eBay and Amazon""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale', 'sale_store'],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'data/taxes.xml',
        'views/account_tax.xml',
        'views/sale_order_views.xml',
        'wizard/import_taxjar_taxes.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
}
