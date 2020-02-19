# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from pytz import timezone
from odoo import models, fields, api


class EbayStock(models.TransientModel):
    _name = 'ebay.stock.wizard'

    store_id = fields.Many2one('sale.store', string='Store')

    @api.model
    def default_get(self, fields):
        result = super(EbayStock, self).default_get(fields)
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/ebay_stock?id=%s' % self.id,
            'target': 'new',
        }
