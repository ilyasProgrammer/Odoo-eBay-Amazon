# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Amazon - Feedback Request",
    'summary': "Amazon - Feedback Request",
    'description': """
Request feedback from customers
====================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store_amazon', 'stock_update_store_real_time'],
    'data': [
        'data/cron_data.xml',
        'data/mail_data.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
