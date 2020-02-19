# -*- coding: utf-8 -*-
import logging
from odoo import api, models, fields, tools, _

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    @api.multi
    def _prepare_sale_order_values(self, partner, pricelist):
        values = super(Website, self)._prepare_sale_order_values(partner, pricelist)
        values['web_order_id'] = '-'
        return values
