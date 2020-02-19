# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from pytz import timezone
import pytz

from odoo import models, fields, api


class AmazonCustomReportWizard(models.TransientModel):
    _name = 'amz.custom.report.wizard'

    report_name = fields.Char('Report Name', required=True)
    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)

    @api.model
    def default_get(self, fields):
        result = super(AmazonCustomReportWizard, self).default_get(fields)
        today = datetime.now().replace(tzinfo=timezone('utc')).astimezone(timezone('US/Eastern'))
        past = today + timedelta(days=-30)
        result['from_date'] = past.strftime("%Y-%m-%d")
        result['to_date'] = today.strftime("%Y-%m-%d")
        return result

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/amz_custom_report?id=%s' % self.id,
            'target': 'new',
        }
