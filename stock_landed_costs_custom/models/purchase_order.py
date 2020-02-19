# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _prepare_picking(self):
        values = super(PurchaseOrder, self)._prepare_picking()
        if not (self.dest_address_id and self.partner_id.is_domestic):
            values['freight_po_id'] = self.id
        return values

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        if not (self.order_id.dest_address_id and self.order_id.partner_id.is_domestic):
            for r in res:
                r['freight_po_id'] = self.order_id.id
        return res
