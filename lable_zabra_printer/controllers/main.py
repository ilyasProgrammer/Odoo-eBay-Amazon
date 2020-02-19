# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
from odoo.http import Controller, route, request


class ReportController(Controller):
    @route([
        '/reportmypdf/<reportname>/<docids>',
    ], type='json', auth='user', website=True)
    def report_routes_cusrome(self, reportname, docids=None, **data):
        context = dict(request.env.context)
        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang'):
                del data['context']['lang']
            context.update(data['context'])
        data = []
        if reportname == 'lable_zabra_printer.report_zebra_shipmentlabel':
            for picking in request.env['stock.picking'].browse(docids):
                data.append({
                    'label': picking.label,
                    'amz_order_type': picking.amz_order_type
                })
        elif reportname == 'stock.report_location_barcode':
            for location in request.env['stock.location'].browse(docids):
                data.append({
                    'name': location.name,
                    'barcode': location.barcode,
                })
        else:
            for product in request.env['product.template'].browse(docids):
                data.append({
                        'name': product.name,
                        'barcode': product.barcode,
                        'binlocation': 'Bin Location',
                        'partslink': product.partslink,
                        'partsbarcode': product.part_number
                })
        return {'data': data}
