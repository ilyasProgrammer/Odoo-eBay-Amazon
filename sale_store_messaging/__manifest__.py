# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "CRM - Amazon and eBay Integration",
    'summary': "Manage store customers",
    'description': """
Communicate with Amazon and eBay customers without needing to leave Odoo
""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store_ebay', 'sale_store_amazon'],
    'data': [
        'data/cron_messaging.xml',
        # 'data/mail_data.xml',
        'security/ir.model.access.csv',
        'views/ebay_message_views.xml',
        # 'views/amz_message_views.xml',
        'views/store_views.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
    'installable': True,
    'auto_install': False,
}
