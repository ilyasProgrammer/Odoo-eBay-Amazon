# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseReports(models.TransientModel):
    _name = 'po.international.diff.wizard'

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/po_international_diff?id=%s' % self.id,
            'target': 'new',
        }
