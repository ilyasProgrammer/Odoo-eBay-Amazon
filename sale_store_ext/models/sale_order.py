# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    related_ids = fields.Many2many('sale.order', 'so_to_so_rel', 'so1', 'so2', compute='_compute_related', store=False)
    web_order_id = fields.Char(string="Web Order ID", required=True, help="Order ID as provided by the web store")
