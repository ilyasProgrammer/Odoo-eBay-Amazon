# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    dropshipper_code = fields.Selection([('lkq', 'LKQ'), ('pfg', 'PFG'), ('ppr', 'PPR'), ('fch', 'FCH')], 'Dropshipper Code')
    is_domestic = fields.Boolean('Is Domestic?')
