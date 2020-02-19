# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    residential = fields.Boolean('Residential', default=False, help='Residential or Business address')
