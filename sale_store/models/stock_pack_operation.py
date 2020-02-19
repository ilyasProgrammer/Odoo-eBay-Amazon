# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPackOperaion(models.Model):
    _inherit = 'stock.pack.operation'

    partslink = fields.Char(related="product_id.partslink", string="Partslink")
    mfg_label = fields.Char(related="product_id.mfg_label", string="Mfg Label")


class StockMove(models.Model):
    _inherit = 'stock.move'

    partslink = fields.Char(related="product_id.partslink", string="Partslink")
    mfg_label = fields.Char(related="product_id.mfg_label", string="Mfg Label")
