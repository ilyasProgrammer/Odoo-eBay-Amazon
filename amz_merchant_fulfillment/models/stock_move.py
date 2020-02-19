# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        values = super(StockMove, self)._get_new_picking_values()
        sale_line_id = self.procurement_id.sale_line_id
        if sale_line_id:
            values['latest_ship_date'] = sale_line_id.order_id.latest_ship_date
            values['shipping_service_id'] = sale_line_id.order_id.shipping_service_id
            values['shipping_service_offer_id'] = sale_line_id.order_id.shipping_service_offer_id
            if not sale_line_id.order_id.amz_order_type and sale_line_id.order_id.store_id.site == 'ebay':
                values['amz_order_type'] = 'ebay'
            elif not sale_line_id.order_id.amz_order_type and sale_line_id.order_id.store_id.site == 'amz':
                values['amz_order_type'] = 'normal'
            else:
                values['amz_order_type'] = sale_line_id.order_id.amz_order_type
            if self.procurement_id.receipt_return_line_id:
                values['amz_order_type'] = 'normal'
        return values
