# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pymssql

from odoo import models, fields, api

class PurchaseUpdateVendorQtyWizard(models.TransientModel):
    _name = 'purchase.update.vendor.qty.wizard'

    product_tmpl_id = fields.Many2one('product.template', 'Product', required=True)
    qty = fields.Integer('Quantity')

    @api.model
    def default_get(self, fields):
        result = super(PurchaseUpdateVendorQtyWizard, self).default_get(fields)
        result['product_tmpl_id'] = self._context.get('active_id')
        return result

    @api.multi
    def button_update_vendor_qty(self):
        self.ensure_one()
        query = """
            UPDATE Inventory SET QtyOnHand = %s WHERE PartNo = '%s'
        """ %(self.qty, self.product_tmpl_id.part_number)
        self.env['sale.order'].with_context(update=True).autoplus_execute(query)
        return {'type': 'ir.actions.act_window_close'}


