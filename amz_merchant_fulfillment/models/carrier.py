# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api

class CarrierService(models.Model):
    _inherit = 'ship.carrier.service'

    amz_fbm_code = fields.Char('Amazon FBM Code')
