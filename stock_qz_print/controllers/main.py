# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# -*- coding: utf-8 -*-
import json
import logging
import werkzeug.utils

from odoo import http
from odoo.http import request

class BarcodePrinting(http.Controller):

    @http.route('/barcode-printing/picking/<int:picking_id>', type='http', auth='user')
    def barcode_printing_for_picking(self, picking_id, **k):
        menu_id = request.env.ref('stock_barcode.stock_barcode_menu')
        action = request.env.ref('stock_barcode.stock_picking_action_kanban')
        picking = request.env['stock.picking'].search([('id', '=', int(picking_id))])
        return request.render('stock_qz_print.index', {
            'picking': picking,
            'action': action.id,
            'menu_id': menu_id.id
            })