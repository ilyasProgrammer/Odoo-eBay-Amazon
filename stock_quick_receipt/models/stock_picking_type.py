# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    show_all_stocks = fields.Boolean('Allow showing of all stocks')
