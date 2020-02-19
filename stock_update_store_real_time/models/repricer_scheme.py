# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class RepricerScheme(models.Model):
    _name = 'repricer.scheme'
    _description = 'Repricer Scheme'

    name = fields.Char('Description', required=True)
    type = fields.Selection([('percent', 'Percent'), ('amount', 'Amount')], 'Type', default='percent')
    percent = fields.Float('Percent (in %)')
    amount = fields.Float('Amount')
    product_listing_ids = fields.One2many('product.listing', 'repricer_scheme_id', string='Listings')
    store_ids = fields.One2many('sale.store', 'repricer_scheme_id', string='Stores')
    reference = fields.Char('Reference', required=True, default='New', readonly=1, copy=False)

    @api.model
    def create(self, vals):
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('repricer.scheme') or 'New'
        return super(RepricerScheme, self).create(vals)
