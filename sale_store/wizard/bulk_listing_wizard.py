# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime

class StoreBulkListing(models.TransientModel):
    _name = 'sale.store.bulk.listing'

    mfg_code = fields.Char('Mfg Code')
    number_of_parts_to_list = fields.Integer('Number of Parts to List', required=True)
    offset = fields.Integer('Offset')
    store_id = fields.Many2one('sale.store', 'Store', required=True, domain=[('enabled', '=', True)])

    @api.multi
    def button_bulk_listing(self):
        self.ensure_one()
        now = datetime.now()
        params = {
            'mfg_code': self.mfg_code,
            'number_of_parts_to_list': self.number_of_parts_to_list,
            'offset': self.offset
        }
        if hasattr(self.store_id, '%s_bulk_list_products' % self.store_id.site):
            getattr(self.store_id, '%s_bulk_list_products' % self.store_id.site)(now, params)
        return {'type': 'ir.actions.act_window_close'}