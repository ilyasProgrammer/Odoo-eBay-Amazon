# -*- coding: utf-8 -*-


from odoo import models, fields, api


class ProductListing(models.Model):
    _inherit = 'product.listing'

    listing_type = fields.Selection(selection_add=[('fba', 'Fulfillment by Amazon')], track_visibility='onchange')
    fba_qty = fields.Integer('FBA Qty', track_visibility='onchange')
