# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ebay_category_id = fields.Many2one('product.ebay.category', 'eBay Category')
