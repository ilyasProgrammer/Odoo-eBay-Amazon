# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class UnlistedWHItems(models.TransientModel):
    _name = 'sale.unlisted.wh.items.wizard'

    store_id = fields.Many2one('sale.store', 'Store', domain=[('enabled', '=', True)])

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/unlisted_wh_items?id=%s' % (self.id),
            'target': 'new',
        }
