# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_log = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    taxjar_tax = fields.Float('TaxJar Tax', default=0.0)
    taxjar_total = fields.Float('TaxJar Total', default=0.0)
