# -*- coding: utf-8 -*-

{
    'name': "eBay Competitors Extension",
    'summary': "eBay Competitors Extension",
    'description': """
        Record daily sales of eBay competitors
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['stock_update_store_real_time'],
    'data': [
        'security/ir.model.access.csv',
        'views/competitor_views.xml'
    ],
}
