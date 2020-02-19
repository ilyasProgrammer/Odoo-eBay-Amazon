# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def cron_amz_submit_tracking_numbers(self):
        prev_6_hrs = (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')
        pick_ids = self.search([('create_date', '>=', '2017-09-08 00:00:00'), ('shipping_state', '=', 'waiting_shipment'), ('write_date', '<=', prev_6_hrs), ('tracking_number', '!=', False)])
        for pick_id in pick_ids:
            try:
                pick_id.button_get_tracking_details()
                _logger.info('%s status: %s' %(pick_id.name, pick_id.shipping_state))
            except:
                pass
