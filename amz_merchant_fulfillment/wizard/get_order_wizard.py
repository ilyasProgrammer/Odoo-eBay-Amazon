# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError

class StoreGetOrder(models.TransientModel):
    _inherit = 'sale.store.get.order'

    web_order_id = fields.Char('Order ID', required=False)
    buyer_email_address = fields.Char('Buyer Email Address')
    site = fields.Selection([], 'Site', related='store_id.site')
    send_feedback_request = fields.Boolean('Send Feedback Request', default=True)
    created_before = fields.Integer('Created Before (in days)', default=7)

    @api.multi
    def get_order(self):
        self.ensure_one()
        now = datetime.now()
        if self.store_id.site == 'ebay':
            if not self.web_order_id:
                raise UserError('Web Order ID is required.')
            existing_so = self.env['sale.order'].search([('web_order_id', '=', self.web_order_id)])
            if existing_so and existing_so.state != 'cancel':
                raise UserError(_('Order is already existing: %s.' %(existing_so.name,)))
            new_so = self.store_id.ebay_get_order_by_order_id(self.web_order_id, now)
            if not new_so:
                raise UserError(_('Web Order ID is not found in store.'))
        else:
            if self.buyer_email_address:
                res = self.store_id.amz_get_order_by_buyer_email_address(self.buyer_email_address, now,
                                                                         send_feedback_request=self.send_feedback_request,
                                                                         created_before=self.created_before)
            if self.web_order_id:
                getorder_params = {'Action': 'GetOrder', 'AmazonOrderId.Id.1': self.web_order_id}
                res = self.store_id.process_amz_request('GET', '/Orders/2013-09-01', now, getorder_params)
                if res:
                    self.store_id.save_orders(now, [res['GetOrderResponse']['GetOrderResult']['Orders']['Order']])
            if not res:
                raise UserError(_('No orders found.'))
        return {'type': 'ir.actions.act_window_close'}
