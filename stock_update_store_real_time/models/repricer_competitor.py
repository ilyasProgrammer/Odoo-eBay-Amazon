# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class RepricerCompetitor(models.Model):
    _name = 'repricer.competitor'
    _description = 'Repricer Competitors'
    _rec_name = 'item_id'
    _order = 'sequence, id'

    item_id = fields.Char('eBay Item ID', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product', required=True)
    price = fields.Float('Current Price')
    previous_price = fields.Float('Previous Price')
    quantity = fields.Integer('Quantity')
    quantity_sold = fields.Integer('Quantity Sold')
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
        ], string='Status', readonly=True, index=True, copy=False, default='active')
    seller = fields.Char('Seller Name')
    title = fields.Char('Title')
    listing_url = fields.Char('Listing URL', compute='_get_listing_url')
    sequence = fields.Integer('Priority', help='Price scraper checks price with lower sequence value more often', default=1000)
    price_write_date = fields.Datetime('Price Updated At')
    mfr_part_number = fields.Char('Manufacturer Part Number')

    @api.multi
    @api.depends('item_id')
    def _get_listing_url(self):
        for l in self:
            if l.item_id:
                l.listing_url = 'https://www.ebay.com/itm/' + l.item_id

    @api.multi
    def button_activate(self):
        for c in self:
            c.state = 'active'

    @api.multi
    def button_deactivate(self):
        for c in self:
            c.state = 'inactive'
