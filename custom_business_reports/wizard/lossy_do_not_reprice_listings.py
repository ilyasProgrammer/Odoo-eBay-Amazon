# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LossDoNotRepriceListings(models.TransientModel):
    _name = 'lossy.dnrl.wizard'

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/lossy_dnrl?id=%s' % (self.id),
            'target': 'new',
        }
