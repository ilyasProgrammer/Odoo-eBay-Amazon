# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class UnsoldWHItems(models.TransientModel):
    _name = 'sale.unsold.wh.items.wizard'

    store_ids = fields.Many2many('sale.store', 'unsold_wh_item_wizard_store_rel', 'wizard_id', 'store_id', 'Stores', domain=[('enabled', '=', True)], required=True)
    days = fields.Integer('Days', required=True)

    @api.model
    def default_get(self, fields):
        result = super(UnsoldWHItems, self).default_get(fields)
        store_ids = self.env['sale.store'].search([('enabled', '=', True)])
        result['store_ids'] = [(6, 0, store_ids.ids)]
        result['days'] = 30
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/unsold_wh_items?id=%s' % (self.id),
            'target': 'new',
        }
