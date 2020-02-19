# -*- coding: utf-8 -*-

from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    item_id = fields.Char('Item ID')

    @api.model
    def create(self, values):
        line = super(SaleOrderLine, self).create(values)
        product_id = line.product_id
        if product_id.qty_available > 0:
            quot_qty = 0
            lines = self.search([('product_id', '=', product_id.id), ('order_id.state', '=', 'draft')]) - line
            for l in lines:
                quot_qty += l.product_uom_qty
            remaining_qty_before_order = product_id.qty_available - product_id.outgoing_qty - quot_qty
            if line.order_id.amz_order_type == 'ebay' and '-' in line.order_id.web_order_id:
                ebay_listing = product_id.listing_ids.filtered(lambda r: r.store_id.site == 'ebay'
                                                                             and r.store_id.enabled
                                                                             and not (r.custom_label and r.custom_label.startswith('X-'))
                                                                             and r.name == line.order_id.web_order_id.split('-')[0])
                if ebay_listing and ebay_listing.min_store_qty:
                    if remaining_qty_before_order - line.product_uom_qty < ebay_listing.min_store_qty:
                        product_id.product_tmpl_id.with_context(so_line_id=line.id).reprice_listings_with_min_cost()
            if remaining_qty_before_order > 0 and (remaining_qty_before_order <= line.product_uom_qty or remaining_qty_before_order - line.product_uom_qty < 3):
                product_id.product_tmpl_id.with_context(so_line_id=line.id).reprice_listings_with_min_cost()
        return line
