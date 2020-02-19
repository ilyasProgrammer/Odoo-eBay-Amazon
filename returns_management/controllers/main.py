# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import time


class QZReturnLabel(http.Controller):

    @http.route('/qz/return_label', type='json', auth="user")
    def qz_return_label(self, **post):
        return_id = request.env['sale.return']
        if post.get('return_id', False):
            return_id = return_id.browse([post.get('return_id')])
        data = []
        for line in return_id.return_line_ids:
            product_tmpl_id = line.product_id.product_tmpl_id
            row = {
                'name': product_tmpl_id.name,
                'barcode': product_tmpl_id.barcode,
                'partslink': product_tmpl_id.partslink or '',
                'part_number': product_tmpl_id.part_number,
                'copies': int(line.product_uom_qty),
                'return_reference': return_id.name[3:]
            }
            data.append(row)
        return data

    @http.route('/return_barcode_scanned', type='json', auth='user')
    def return_barcode_scanned(self, barcode, **kw):
        # location or tracking number
        barcode = barcode.strip()
        if '-' not in barcode:
            ret_id = request.env['sale.return'].search([('tracking_number', '=', barcode)])
            if not ret_id:
                # FedEx ?
                fedex_barcode = barcode[-15:].lstrip("0")
                ret_id = request.env['sale.return'].search([('tracking_number', '=', fedex_barcode)])
            if not ret_id:
                if barcode[0:7] == '42048035':  # USPS. Not sure what it is.
                    usps_barcode = barcode[8:]
                    ret_id = request.env['sale.return'].search([('tracking_number', '=', usps_barcode)])
            if not ret_id:
                # USPS. Not sure what it is.
                usps_barcode = barcode[8:]
                ret_id = request.env['sale.return'].search([('tracking_number', '=', usps_barcode)])
            if len(ret_id) > 1:
                return {'error': 'Several (%(ret)s) returns with same tracking number : %(barcode)s' % {'ret': len(ret_id), 'barcode': barcode}}
            elif len(ret_id) < 1:
                return {'error': 'Cant find return for barcode: %(barcode)s' % {'barcode': barcode}}
            # if ret_id.state not in ['draft', 'open', 'waiting_receipt', 'waiting_buyer_send']:
            #     return {'error': '<p>Wrong return state: %s</p> <p>Picking id: %s</p>' % (ret_id.state, ret_id.id)}
            ret_vals = {'type': 'return',
                        'id': ret_id.id,
                        'web_order_id': ret_id.web_order_id,
                        'return_reason': ret_id.return_reason,
                        'customer_comments': ret_id.customer_comments,
                        'tracking_number': ret_id.tracking_number,
                        'carrier_name': ret_id.carrier_id.name,
                        'product_name': ret_id.return_line_ids[0].product_id.mfg_label,
                        'lad': ret_id.return_line_ids[0].product_id.name}
            return ret_vals
        else:  # Location always has letters and hyphen
            loc_id = request.env['stock.location'].search([('barcode', '=', barcode)])
            if len(loc_id) > 1:
                return {'warning': 'Several (%(ret)s) locations with same barcode number : %(barcode)s' % {'ret': len(loc_id), 'barcode': barcode}}
            elif len(loc_id) < 1:
                return {'warning': 'Cant find location for barcode: %(barcode)s' % {'barcode': barcode}}
            ret_vals = {'type': 'location',
                        'name': loc_id.name,
                        'barcode': loc_id.barcode}
            return ret_vals

    @http.route('/return_receive_item', type='json', auth='user')
    def return_receive_item(self, ret_data, **kw):
        res = self._receive_item(ret_data, request)
        if 'message' in res:
            return {'message': res['message']}
        return res

    def _receive_item(self, ret_data, request):
        ret_id = request.env['sale.return'].browse(int(ret_data['id']))
        if not ret_id:
            return {'error': 'Cant find return by id: %s' % ret_data['id']}
        loc_id = request.env['stock.location'].search([('barcode', '=', ret_data['location_barcode'])])
        if not loc_id:
            return {'error': 'Cant find location by barcode: %s' % ret_data['location_barcode']}
        picks_to_process = ret_id.receipt_picking_ids.filtered(lambda r: r.state not in ['cancel', 'done'])
        if len(picks_to_process):
            res = ret_id.receive_return_in_wh_button(triggered=True, location=loc_id)
        else:
            ret_id.create_picking_for_receipt()
            ret_id.receipt_state = 'to_receive'
            ret_id.with_return = True
            res = ret_id.receive_return_in_wh_button(triggered=True, location=loc_id)
            picks_to_process = res
        return {'message': 'received', 'processed_pickings': picks_to_process}

    @http.route('/return_scrap_items', type='json', auth='user')
    def return_scrap_items(self, ret_data, **kw):
        ret_id = request.env['sale.return'].browse(int(ret_data['id']))
        returns_transit_location = request.env.ref('returns_management.returns_transit_location')
        ret_data['location_barcode'] = returns_transit_location.barcode
        res = self._receive_item(ret_data, request)
        if 'processed_pickings' in res:
            for picking in res['processed_pickings']:
                for move in picking.move_lines:
                    request.env['stock.scrap'].create({
                        'location_id': returns_transit_location.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_id.uom_id.id,
                        'scrap_qty': move.product_uom_qty,
                        'picking_id': picking.id,
                        'origin': picking.name
                    })
                    for quant in move.quant_ids:
                        quant.landed_cost = move.landed_cost
                        quant.cost = quant.product_cost + move.landed_cost if quant.product_cost else move.price_unit + move.landed_cost
            return {'message': 'scrapped'}
        else:
            return res
