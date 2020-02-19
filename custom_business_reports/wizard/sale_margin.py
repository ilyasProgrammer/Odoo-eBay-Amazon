# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from pytz import timezone
import pytz

from odoo import models, fields, api


class SaleMargin(models.TransientModel):
    _name = 'sale.margin.wizard'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    report_timezone = fields.Selection([('est', 'EST/EDT (UTC+4)'), ('pdt', 'PDT (UTC+7)'), ('utc', 'UTC')])
    store = fields.Many2one('sale.store')

    @api.model
    def default_get(self, fields):
        result = super(SaleMargin, self).default_get(fields)
        today = datetime.now().replace(tzinfo=timezone('utc')).astimezone(timezone('US/Eastern'))
        yesterday = today + timedelta(days=-1)
        result['from_date'] = yesterday.strftime("%Y-%m-%d")
        result['to_date'] = yesterday.strftime("%Y-%m-%d")
        result['report_timezone'] = 'est'
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/sales_margin?id=%s' % (self.id),
            'target': 'new',
        }


class SaleMarginReturns(models.TransientModel):
    _name = 'sale.margin.returns.wizard'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)

    @api.model
    def default_get(self, fields):
        result = super(SaleMarginReturns, self).default_get(fields)
        today = datetime.now().replace(tzinfo=timezone('utc')).astimezone(timezone('US/Eastern'))
        yesterday = today + timedelta(days=-1)
        result['from_date'] = yesterday.strftime("%Y-%m-%d")
        result['to_date'] = yesterday.strftime("%Y-%m-%d")
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/sales_margin_returns?id=%s' % self.id,
            'target': 'new',
        }
