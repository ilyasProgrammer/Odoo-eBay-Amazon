# -*- coding: utf-8 -*-

from odoo import models, api


class MapmBuyBoxWizard(models.TransientModel):
    _name = 'mapm.buy.box.wizard'

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/mapm_buy_box?id=%s' % self.id,
            'target': 'new',
        }
