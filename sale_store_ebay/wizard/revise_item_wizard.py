# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class eBayReviseItem(models.TransientModel):
    _name = 'sale.store.ebay.revise.item'

    listing_id = fields.Many2one('product.listing', 'Listing', required=True)
    sku = fields.Char('SKU')
    title = fields.Char('Title')
    price = fields.Float('Price')
    quantity = fields.Integer('Quantity')
    description = fields.Text('Description')

    @api.model
    def default_get(self, fields):
        result = super(eBayReviseItem, self).default_get(fields)
        result['listing_id'] = result.get('listing_id', self._context.get('listing_id'))
        result['sku'] = result.get('sku', self._context.get('sku'))
        result['title'] = result.get('title', self._context.get('title'))
        result['price'] = result.get('price', self._context.get('price'))
        result['quantity'] = result.get('quantity', self._context.get('quantity'))
        return result

    @api.multi
    def button_revise_item(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
