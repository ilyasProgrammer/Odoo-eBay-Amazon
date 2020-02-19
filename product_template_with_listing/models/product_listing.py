# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class ProductListing(models.Model):
    _inherit = 'product.listing'

    sell_with_loss = fields.Boolean('Allow Selling With Loss?', track_visibility='onchange')
    sell_with_loss_type = fields.Selection([('percent', 'Percent'), ('amount', 'Amount')], 'Loss Limit Calculation', default='percent', track_visibility='onchange')
    sell_with_loss_amount = fields.Float('Amount', track_visibility='onchange')
    sell_with_loss_percent = fields.Float('Percent', track_visibility='onchange')
