# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class UpdateShippingTemplate(models.TransientModel):
    _name = 'product.update.shipping.template.wizard'

    listing_id = fields.Many2one('product.listing', 'Listing', required=True)
    store_id = fields.Many2one('sale.store', 'Store', related='listing_id.store_id')
    title = fields.Char('Title', required=True)
    shipping_template_id = fields.Many2one('sale.store.amz.shipping.template', 'Shipping Template', required=True)

    @api.model
    def default_get(self, fields):
        res = super(UpdateShippingTemplate, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'product.listing':
            listing_id = self.env['product.listing'].browse([self.env.context.get('active_id')])
            res['listing_id'] = listing_id.id
            res['title'] = listing_id.title
        return res

    @api.multi
    def button_update_shipping_template(self):
        self.listing_id.store_id.update_shipping_template([(self.listing_id.name, self.title, self.shipping_template_id.name)])
        return {'type': 'ir.actions.act_window_close'}
