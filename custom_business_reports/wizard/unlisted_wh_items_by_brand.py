# -*- coding: utf-8 -*-

from odoo import models, fields, api


class UnlistedWHItemsByBrand(models.TransientModel):
    _name = 'sale.unlisted.wh.items.by.brand.wizard'

    brand = fields.Char('Brand', default='Make Auto Parts Manufacturing')

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/unlisted_wh_items_by_brand?id=%s' % (self.id),
            'target': 'new',
        }
