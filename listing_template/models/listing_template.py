# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ListingTemplate(models.Model):
    _name = 'listing.template'

    name = fields.Char('Name')
    store_id = fields.Many2one('sale.store', 'Store')
    brand_id = fields.Many2one('sale.brand', 'Brand')
    title = fields.Text('Title')
    template = fields.Text('Template')
