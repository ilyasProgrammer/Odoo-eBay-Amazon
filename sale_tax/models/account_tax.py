# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    state_id = fields.Many2one('res.country.state', 'State')
    # web_store = fields.Selection([('ebay', 'eBay'), ('amz', 'Amazon')], 'Store type')
    tax_reg_num = fields.Char('Registration', help='State Tax Registration Number')
