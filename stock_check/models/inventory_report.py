# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp

class InventoryReport(models.Model):
    _name = 'stock.check.inventory.report'
    _rec_name = 'item_id'

    item_id = fields.Char('Item ID', required=True)
    sku = fields.Char('SKU', help="Custom label for eBay")
    old_qty = fields.Integer('Old Quantity')
    old_price = fields.Float('Old Price', digits=dp.get_precision('Product Price'))
    wh_shipping_price = fields.Float('WH Shipping Price', digits=dp.get_precision('Shipping Price'))
    vendor_availability = fields.Integer('Vendor Availability')
    vendor_cost = fields.Float('Vendor Cost', digits=dp.get_precision('Product Price'))
    wh_cost = fields.Float('WH Cost', digits=dp.get_precision('Product Price'))
    wh_availability = fields.Integer('WH Availability')
    new_qty = fields.Integer('New Quantity')
    new_price = fields.Float('New Price', digits=dp.get_precision('Product Price'))
    product_tmpl_id = fields.Many2one('product.template', 'Product')
    store_id = fields.Many2one('sale.store', 'Store')
    is_a_kit = fields.Boolean('Is a Kit')
    min_handling_time = fields.Boolean('Set Min. Handling Time?')
