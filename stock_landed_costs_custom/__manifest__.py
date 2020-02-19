# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Landed Costs - Custom",
    'summary': "Custom landed cost computation",
    'description': """
Custom landed cost computation
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    # 'depends': ['stock_landed_costs', 'ship_fedex'],
    'depends': ['stock_landed_costs'],
    # always loaded
    'data': [
        'views/stock_landed_cost_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_picking_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
