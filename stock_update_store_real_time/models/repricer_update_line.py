# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class RepricerUpdatLine(models.Model):
    _name = 'repricer.update.line'
    _description = 'eBay Repricer Updates'
    _rec_name = 'product_listing_id'
    _order = 'id desc'

    product_listing_id = fields.Many2one('product.listing', 'Listing', required=True)
    action = fields.Selection([('increase', 'Increase'), ('decrease', 'Decrease')], 'Action')
    percent = fields.Float('Percent (in %)')
    store_id = fields.Many2one('sale.store', 'Store', related='product_listing_id.store_id')
    product_tmpl_id = fields.Many2one('product.template', 'Product', related='product_listing_id.product_tmpl_id')
    old_price = fields.Float('Old Price')
    new_price = fields.Float('New Price')
