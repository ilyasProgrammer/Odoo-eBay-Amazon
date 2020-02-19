# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    amz_fba_shipping_cost = fields.Float('Amazon FBA shipping cost')
