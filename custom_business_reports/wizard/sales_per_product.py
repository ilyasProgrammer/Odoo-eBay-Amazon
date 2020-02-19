# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from pytz import timezone
import pytz
from odoo import models, fields, api


class SalesPerProduct(models.TransientModel):
    _name = 'sales.per.product.wizard'
    
    period_start = fields.Date('Period start', help="Date when the current period starts, sales will be counted one day/week/month to the past and to the future of this date",
        default = datetime.now() + timedelta(weeks=-1), required = True)
    grouping_criteria = fields.Selection([('day', 'Day'), ('week', 'Week'), ('month', 'Month')], 'Grouping criteria', required=True, default='week')
    drop_percentage = fields.Integer(required=True, help="This report shows LADs where the sales drop percentage is higher than this percentage", default=0)

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/sales_per_product?id=%s' % (self.id),
            'target': 'new',
        }
