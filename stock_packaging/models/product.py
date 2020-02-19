# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_packaging_product = fields.Boolean('Packaging Product')
    packaging_product_id = fields.Many2one('product.product', 'Packaging', domain=[('is_packaging_product', '=', True)])
    no_packaging = fields.Boolean('No Packaging')
    boxes_ids = fields.One2many('box.line', 'product_id', string='Boxes')


class Boxes(models.Model):
    _name = 'box.line'

    product_id = fields.Many2one('product.template', string='Owner product')
    box_id = fields.Many2one('product.product', string='Box', domain=[('is_packaging_product', '=', True)])
    name = fields.Char(related='box_id.mfg_label')
    qty = fields.Integer('Uses', help='How many times was used')
    comment = fields.Char()
