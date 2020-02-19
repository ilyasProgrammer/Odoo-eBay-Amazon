# -*- coding: utf-8 -*-

{
    'name': "Fedex Integration",
    'summary': """Integration with FedEx tracking API""",
    'description': """Get status of a tracking number. Direct FedEx requests""",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'depends': ['ship_shipstation', 'stock', 'sale_store'],
    'data': [
        'views/carrier_views.xml',
        'views/picking.xml',
        'views/service.xml',
        'fedex_oversized.xml',
        'oversized_pack.xml',
        'oversized_services.xml'
    ],
    'application': False,
    'license': 'OEEL-1',
}
