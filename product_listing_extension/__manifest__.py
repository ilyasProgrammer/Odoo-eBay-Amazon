# -*- coding: utf-8 -*-

{
    'name': "Product Listing - Extended",
    'summary': "Product Listing - Extended",
    'description': """
Product Listing - Extended
=================================================================================
    """,
    'author': 'Opsyst',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['sale_store',
                'sale_store_ebay',
                'product_auto_attributes'],
    'data': [
        'security/ir.model.access.csv',
        'templates/assets_templates.xml',
        'wizard/sync_ebay_category_wizard_views.xml',
        'views/ebay_category_views.xml',
        'views/product_listing_views.xml',
        # 'views/product_views.xml',
        'wizard/revise_item_wizard_views.xml',
        'data.xml',
    ],
    'qweb': [
        'static/src/xml/listing_url.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
