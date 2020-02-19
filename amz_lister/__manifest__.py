# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "Amazon Lister",
    'summary': "Amazon Lister",
    'description': "Amazon Lister",
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': [
        'amz_merchant_fulfillment',
        'product_auto_attributes'
    ],
    'data': [
        'wizard/update_amz_listing_views.xml',
        'views/product_listing_views.xml',
    ],
    'application': False,
    'license': 'OEEL-1',
}
