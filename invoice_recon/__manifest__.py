# -*- coding: utf-8 -*-

{
    'name': "Invoice Reconciliation",
    'summary': "Invoice reconciliation",
    'description': """
Invoice reconciliation
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_dropship'],
    'data': [
        'data/recon_data.xml',
        'security/ir.model.access.csv',
        'views/purchase_recon_views.xml',
        'views/purchase_shipping_recon_views.xml',
        'views/ebay_recon_views.xml',
        'views/amazon_recon_views.xml',
    ],
    'application': False,
    'license': 'OEEL-1',
}
