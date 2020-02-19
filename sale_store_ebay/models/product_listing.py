# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import models, fields, api, _

class ProductListing(models.Model):
    _inherit = 'product.listing'

    @api.multi
    def button_ebay_revise_item(self):
        revise_form = self.env.ref('sale_store_ebay.view_revise_item', False)
        item = self.store_id.ebay_execute('GetItem', {
            'ItemID': self.name,
            'IncludeItemSpecifics': True,
            'DetailLevel': 'ItemReturnDescription'
        }).dict()['Item']
        ctx = dict(
            default_listing_id=self.id,
            default_sku=item['SKU'],
            default_title=item['Title'],
            default_quantity=int(item['Quantity']),
            default_price=float(item['StartPrice']['value']),
            default_description=item['Description'],
        )
        return {
            'name': _('Revise Item'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.store.ebay.revise.item',
            'views': [(revise_form.id, 'form')],
            'view_id': revise_form.id,
            'target': 'new',
            'context': ctx,
        }
