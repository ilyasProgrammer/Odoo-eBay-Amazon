# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPackagingWarning(models.TransientModel):
    _name = 'stock.packaging.warning.wizard'
    _description = 'Packaging Warning'

    pick_id = fields.Many2one('stock.picking')

    @api.model
    def default_get(self, fields):
        res = super(StockPackagingWarning, self).default_get(fields)
        if not res.get('pick_id') and self._context.get('active_id'):
            res['pick_id'] = self._context['active_id']
        return res

    @api.multi
    def process(self):
        self.ensure_one()
        self.pick_id.write({'packaging_not_required': True})
        return self.pick_id.do_new_transfer()
