# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleBrand(models.Model):
    _name = 'sale.brand'

    name = fields.Char('Name')
    image = fields.Binary("Logo", attachment=True, help="This field holds the logo for this store, limited to 1024x1024px",)
    image_ids = fields.One2many('sale.store.image', 'store_id', 'Images used in template')
