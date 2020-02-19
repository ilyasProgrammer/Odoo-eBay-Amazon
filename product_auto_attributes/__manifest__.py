# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Product Auto Attributes",
    'summary': "Product Auto Attributes",
    'description': """
Product Auto Attributes
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_auto_attribute_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
