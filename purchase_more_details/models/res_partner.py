# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class Partner(models.Model):
    _inherit = 'res.partner'

    mfg_codes = fields.Char(string='Mfg Codes', help='Technical field for comma-separated associated mfg codes with the vendor')
    purchase_lead_time = fields.Integer('Purchase Lead Time')
