# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class ProductListing(models.Model):
    _inherit = 'product.listing'

    upc = fields.Char('UPC')
