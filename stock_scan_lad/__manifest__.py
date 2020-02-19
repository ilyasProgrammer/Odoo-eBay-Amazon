# -*- coding: utf-8 -*-

{
    'name': "Stock - Scan LAD",
    'summary': "Scan some product data, get product, print it",
    'description': """1. Scan the partslink, manufacturer, LKQ, PFG, etc part number barcode 2. The system pulls up the LAD part numbers that are associated (alternate part number) with the scanned part number, along with the item description 3. In one click it prints a single label""",
    'author': 'Opsyst',
    'developer': 'Ilyas',
    'website': 'http://opsyst.com',
    'category': 'Opsyst',
    'version': '1.0',
    'depends': ['stock', 'sale_dropship','barcodes'],  #  TODO what here ?
    'data': [
        'views/scan_lad_templates.xml',
        'views/scan_lad_views.xml'
    ],
    'qweb': [
        'static/src/xml/scan_lad.xml'
    ],
    'demo': [
    ],
    'application': False,
    'license': 'OEEL-1',
}
