# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class CronTool(models.TransientModel):
    _name = 'cron.tool'

    @api.multi
    def qwe_with_loss(self):
        qwes = self.env['sale.order'].search([('amount_total', '=', 0),
                                              ('has_exception', '=', True),
                                              ('state', '=', 'draft')])
        for q in qwes:
            logging.info('QWE %s', q)
            q.button_set_losy_routes()
            self.env.cr.commit()
