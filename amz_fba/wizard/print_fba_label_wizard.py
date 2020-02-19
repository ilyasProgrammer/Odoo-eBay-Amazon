# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.exceptions import UserError

class PrintFBALabelWizard(models.TransientModel):
    _name = 'stock.print.fba.label.wizard'

    copies = fields.Integer('Copies', required=True, default=1)
    sku = fields.Char('SKU', required=True)
    description = fields.Char('Description')

    @api.model
    def default_get(self, fields):
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError("You can only print FBA label for one listing at a time!")
        res = super(PrintFBALabelWizard, self).default_get(fields)

        listing_id = self.env['product.listing'].browse(self.env.context.get('active_id'))

        if listing_id:
            res.update({
                'sku': listing_id.asin or listing_id.name,
                'description': listing_id.product_tmpl_id.mfg_label or listing_id.product_tmpl_id.product_type
            })
        return res

    @api.multi
    def print_fba_label(self):
        return {'type': 'ir.actions.act_window_close'}
