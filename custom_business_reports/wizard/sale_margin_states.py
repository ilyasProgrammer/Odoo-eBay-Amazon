# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from pytz import timezone
from odoo import models, fields, api


class SaleMarginStates(models.TransientModel):
    _name = 'sale.margin.states.wizard'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    store_id = fields.Many2one('sale.store', string='Store')

    @api.model
    def default_get(self, fields):
        result = super(SaleMarginStates, self).default_get(fields)
        today = datetime.now().replace(tzinfo=timezone('utc')).astimezone(timezone('US/Eastern'))
        yesterday = today + timedelta(days=-1)
        result['from_date'] = yesterday.strftime("%Y-%m-%d")
        result['to_date'] = yesterday.strftime("%Y-%m-%d")
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/sales_margin_states?id=%s' % self.id,
            'target': 'new',
        }
