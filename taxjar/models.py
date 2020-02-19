# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    taxjar_tax = fields.Float('TaxJar Tax')

    #  Check v2_taxjar.py for cron that pulls taxjar data
