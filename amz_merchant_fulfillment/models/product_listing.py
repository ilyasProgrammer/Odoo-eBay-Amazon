# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class ProductListting(models.Model):
    _inherit = 'product.listing'

    is_fbm_prime = fields.Boolean('Sell as Prime', track_visibility='onchange')
    listing_type = fields.Selection([('normal', 'Normal'), ('fbm', 'Prime Fulfillment by Merchant')], 'Prime Eligible Or Not', default='normal', track_visibility='onchange')
