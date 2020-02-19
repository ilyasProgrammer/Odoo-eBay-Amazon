# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from functools import wraps
from werkzeug import wrappers

from odoo import http
from odoo.http import request

def api_call(auth=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            res = {}
            if auth:
                token = ''
                header = request.httprequest.headers['Authorization'] if 'Authorization' in request.httprequest.headers else ''
                if len(header) > 7 and header[0:6] == 'Bearer':
                    token = header[7:]

                if not token or token != request.env['ir.config_parameter'].sudo().get_param('endpoint_auth_token'):
                    return {
                        'error': 'Token is not valid.',
                    }
            return func(*args, **kwargs)
        return wrapper
    return decorator

class StoreConnector(http.Controller):

    def validate_request(self, token):
        if token and token == request.env['ir.config_parameter'].sudo().get_param('endpoint_auth_token'):
            return True
        return False

    @http.route(['/store/order/add'], type='http', auth="none", methods=['POST'], csrf=False)
    def add_order(self, **post):
        code = post.get('code')
        if not code:
            res = {'error': 'Store code is required.'}
            return json.dumps(res)

        store_id = request.env['sale.store'].sudo().search([('code', '=', code)])

        if not store_id:
            res = {'error': 'Store not found.'}
            return json.dumps(res)

        order = post.get('order')
        if not order:
            res = {'error': 'Order data are required.'}
            return json.dumps(res)

        order = json.loads(post.get('order'))
        if store_id.site == 'ebay':
            order_id = order['OrderID']
            sale_order_id = request.env['sale.order'].sudo().search([('web_order_id', '=', order_id)])
            if not sale_order_id:
                sale_order_id = store_id.ebay_saveorder(order)
            res = {'order_id': sale_order_id[0].id}
            return json.dumps(res)

    @http.route(['/store/tracking-to-be-sent-to-store'], type='http', auth="none", methods=['POST'], csrf=False)
    def get_tracking_numbers_to_send_to_store(self, **post):
        code = post.get('code')
        if not code:
            res = {'error': 'Store code is required.'}
            return json.dumps(res)

        store_id = request.env['sale.store'].sudo().search([('code', '=', code)])

        if not store_id:
            res = {'error': 'Store not found.'}
            return json.dumps(res)

        picking_ids = request.env['stock.picking'].sudo().search([('store_notified', '=', False), ('sale_id.store_id.id', '=', store_id.id), ('tracking_number', '!=', False), ('shipping_state', '!=', 'error')])
        vendor_shipment_ids = request.env['sale.shipment.from.vendor'].sudo().search([('store_notified', '=', False), ('sale_id.store_id.id', '=', store_id.id), ('tracking_number', '!=', False), ('shipping_state', '!=', 'error')])
        res = []
        for picking in picking_ids:
            res.append({
                'type': 'direct',
                'order_id': picking.sale_id.web_order_id,
                'order_line_item_id': picking.sale_id.order_line[0].web_orderline_id,
                'carrier': picking.carrier_id.name,
                'tracking_number': picking.tracking_number,
            })
        for shipment in vendor_shipment_ids:
            res.append({
                'type': 'direct',
                'order_id': shipment.sale_id.web_order_id,
                'order_line_item_id': shipment.sale_id.order_line[0].web_orderline_id,
                'carrier': shipment.carrier_id.name,
                'tracking_number': shipment.tracking_number,
            })
        return json.dumps(res)

    @http.route(['/store/tracking-set-store-notified'], type='http', auth="none", methods=['POST'], csrf=False)
    def set_store_notified(self, **post):
        code = post.get('code')
        if not code:
            res = {'error': 'Store code is required.'}
            return json.dumps(res)

        store_id = request.env['sale.store'].sudo().search([('code', '=', code)])

        if not store_id:
            res = {'error': 'Store not found.'}
            return json.dumps(res)
        order_ids = json.loads(post['order_ids'])
        for order_id in order_ids:
            picking_id = request.env['stock.picking'].sudo().search([('sale_id.web_order_id', '=', order_id), ('store_id.code', '=', code)])
            if picking_id:
                picking_id.write({'store_notified': True})
            else:
                vendor_shipment_id = request.env['sale.shipment.from.vendor'].sudo().search([('sale_id.web_order_id', '=', order_id), ('store_id.code', '=', code)])
                vendor_shipment_id.write({'store_notified': True})
        return json.dumps({'success': True})

    @http.route(['/store/missing-order-notification'], type='http', auth='none', methods=['POST'], csrf=False)
    def missing_order_notify(self, **post):
        if 'stores' in post:
            stores = json.loads(post['stores'])
            if stores:
                template = request.env.ref('sale_store_connector.missing_order_notification').sudo()
                template.with_context(stores=stores).send_mail(1, force_send=True, raise_exception=True)

    @http.route(['/store/unmapped-listings-notification'], type='http', auth='none', methods=['POST'], csrf=False)
    def unmapped_listings_notify(self, **post):
        valid = self.validate_request(post.get('token', False))
        if not valid:
            return wrappers.Response(json.dumps({'error': 'Invalid token.'}), 400)
        if 'listings' in post:
            listings = json.loads(post['listings'])
            unmapped_listings_total = post['unmapped_listings_total']
            if listings:
                template = request.env.ref('sale_store_connector.unmapped_listings_notification').sudo()
                template.with_context(unmapped_listings_total=unmapped_listings_total, listings=listings).send_mail(1, force_send=True, raise_exception=True)

    @http.route('/store/stock-check-notification', type='json', auth="none", csrf=False, methods=['POST'])
    @api_call()
    def stock_check_notification(self, **post):
        """
            Post should be:
            {
                "params": {
                    "stores": ["ride", "rhino", "visionary", "sinister"],
                    "error": "some error message here"
                }
            }
        """
        template = request.env.ref('sale_store_connector.stock_check_with_repricer_notification').sudo()
        subject = 'Successful Stock Check Run'
        content = ''
        if 'error' in post and post['error']:
            subject = 'Failed Stock Check Run'
            content = post['error']
        else:
            if 'stores' in post and post['stores'] and isinstance(post['stores'], list):
                content = 'Successful run on ' + ', '.join(post['stores'])
        template.with_context(subject=subject, content=content).send_mail(1, force_send=True, raise_exception=True)
        return {'success': True}
