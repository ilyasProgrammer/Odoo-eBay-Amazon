# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.addons.website.models.website import slug

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_print_product_labels(self):
        return True