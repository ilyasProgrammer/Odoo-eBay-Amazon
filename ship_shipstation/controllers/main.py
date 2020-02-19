# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
from odoo.http import Controller, route, request


class GetReportController(Controller):
    @route([
        '/reportmypdf/<docids>/get/nextid',
    ], type='json', auth='user', website=True)
    def get_report_routes_cusrome(self, docids=None, **data):
        context = dict(request.env.context)
        data = []
        if docids:
            docids = [int(i) for i in docids.split(',')]
            all_ids = request.env['stock.picking'].search([('picking_type_code', '=', 'outgoing')])
            filtered = all_ids.filtered(lambda b: b.id > docids[0])
            if filtered:
                data.append({
                    'next_id': filtered[0].id,
                })
        return {'data': data}