# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp

class ReturnWizard(models.TransientModel):
    _name = 'sale.return.wizard'

    order_id = fields.Many2one('sale.order', string="Order", readonly=True)
    return_line_ids = fields.One2many('sale.return.line.wizard', 'wizard_id', 'Products')

    @api.model
    def default_get(self, fields):
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError("You may only return one sales order at a time!")
        res = super(ReturnWizard, self).default_get(fields)

        return_line_ids =[]
        order_id = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if order_id:
            res['order_id'] = order_id.id
            for line in order_id.order_line:
                return_line_ids.append((0, 0, {'qty': line.product_uom_qty, 'order_line_id': line.id}))
            if 'return_line_ids' in fields:
                res.update({'return_line_ids': return_line_ids})
        return res

    @api.multi
    def button_return_order(self):
        self.ensure_one()
        return_id = self.env['sale.return'].create({
            'store_id': self.order_id.store_id.id,
            'sale_order_id': self.order_id.id,
            'web_order_id': self.order_id.web_order_id,
            'request_date': datetime.now().strftime('%Y-%m-%d'),
            'partner_id': self.order_id.partner_id.id,
            'state': 'open',
            'receipt_state': 'draft',
            'replacement_by': 'wh',
            'replacement_state': 'draft',
            'compensation_status': 'draft',

        })
        for line in self.return_line_ids:
            vals = {
                'return_id': return_id.id,
                'name': line.order_line_id.product_id.name,
                'product_id': line.order_line_id.product_id.id,
                'product_uom_qty': line.qty,
                'product_uom':line.order_line_id.product_uom.id,
                'sale_order_id':self.order_id.id,
                'sale_line_id': line.order_line_id.id
            }
            self.env['sale.return.line'].create(vals)

        return {'type': 'ir.actions.act_window_close'}

class ReturnLineWizard(models.TransientModel):
    _name = 'sale.return.line.wizard'

    wizard_id = fields.Many2one('sale.return.wizard', 'Wizard')
    order_line_id = fields.Many2one('sale.order.line', string="Product", required=True, readonly=True)
    qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)