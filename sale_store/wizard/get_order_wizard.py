# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError

class StoreGetOrder(models.TransientModel):
    _name = 'sale.store.get.order'

    web_order_id = fields.Char('Order ID', required=True)
    store_id = fields.Many2one('sale.store', 'Store', required=True, domain=[('enabled', '=', True)])

    @api.multi
    def get_order(self):
        self.ensure_one()
        now = datetime.now()
        existing_so = self.env['sale.order'].search([('web_order_id', '=', self.web_order_id)])
        if existing_so.state:
            raise UserError(_('Order is already existing: %s.' %(existing_so.name,)))

        new_so = False
        if hasattr(self.store_id, '%s_get_order_by_order_id' % self.store_id.site):
            new_so = getattr(self.store_id, '%s_get_order_by_order_id' % self.store_id.site)(self.web_order_id, now)
        if not new_so:
            raise UserError(_('Web Order ID not found in store.'))
        return {'type': 'ir.actions.act_window_close'}
