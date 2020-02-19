# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    product_cost = fields.Float('Product Cost', default=0.0)

    @api.multi
    def _prepare_inventory_line(self):
        product = self.product_id.with_context(location=self.location_id.id, lot_id=self.lot_id.id)
        th_qty = product.qty_available

        res = {
               'product_qty': self.new_quantity,
               'location_id': self.location_id.id,
               'product_id': self.product_id.id,
               'product_uom_id': self.product_id.uom_id.id,
               'theoretical_qty': th_qty,
               'prod_lot_id': self.lot_id.id,
               'product_cost': self.product_cost,
        }

        return res


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    product_cost = fields.Float('Product Cost', default=0.0)
