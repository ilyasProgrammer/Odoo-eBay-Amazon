# -*- coding: utf-8 -*-

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    services_prices_log = fields.Text('Services prices log')
    residential = fields.Boolean('Residential', default=False, help='Residential or Business address')
