# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from pytz import timezone
import pytz

from odoo import models, fields, api

class DropshipMargin(models.TransientModel):
    _name = 'sale.dropship.margin.wizard'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)

    @api.model
    def default_get(self, fields):
        result = super(DropshipMargin, self).default_get(fields)
        today = datetime.now().replace(tzinfo=timezone('utc')).astimezone(timezone('US/Eastern'))
        yesterday = today + timedelta(days=-1)
        result['from_date'] = yesterday.strftime("%Y-%m-%d")
        result['to_date'] = yesterday.strftime("%Y-%m-%d")
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/dropship_margin?id=%s' % (self.id),
            'target': 'new',
        }
