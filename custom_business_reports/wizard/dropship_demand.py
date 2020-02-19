# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from pytz import timezone

from odoo import models, fields, api


class DropshipDemand(models.TransientModel):
    _name = 'dropship.demand.wizard'

    dropshipper_code = fields.Selection([('lkq','LKQ'), ('pfg','PFG'), ('PPR','PPR')], 'Dropshipper', required=True, default='lkq')
    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)

    @api.model
    def default_get(self, fields):
        today = datetime.now().replace(tzinfo=timezone('utc')).astimezone(timezone('US/Eastern'))
        result = super(DropshipDemand, self).default_get(fields)
        result['from_date'] = (today + timedelta(days=-14)).strftime("%Y-%m-%d")
        result['to_date'] = today.strftime("%Y-%m-%d")
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/dropship_demand?id=%s' % (self.id),
            'target': 'new',
        }
