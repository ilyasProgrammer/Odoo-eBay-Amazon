# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    recon_line_ids = fields.One2many('purchase.recon.line', 'purchase_order_id', 'Recon Lines')
