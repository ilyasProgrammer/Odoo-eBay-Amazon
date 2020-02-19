# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    store_id = fields.Many2one('sale.store', 'Store', readonly=True)
    web_partner_id = fields.Char(string="Web Partner ID", readonly= True, help="ID as provided by the store")