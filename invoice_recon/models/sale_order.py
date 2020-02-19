# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ebay_recon_line_ids = fields.One2many('ebay.recon.line', 'sale_order_id', 'eBay Recon Lines')
    amazon_recon_line_ids = fields.One2many('amazon.recon.line', 'sale_order_id', 'Amazon Recon Lines')
