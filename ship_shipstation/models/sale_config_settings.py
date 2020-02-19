# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ShipStationConfiguration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'sale.config.settings'

    ss_api_key = fields.Char("API Key")
    ss_api_secret = fields.Char("API Secret")

    @api.multi
    def set_ss_api(self):
        ss_api_key = self[0].ss_api_key or ''
        self.env['ir.config_parameter'].set_param('ss_api_key', ss_api_key, groups=["base.group_system"])
        ss_api_secret = self[0].ss_api_secret or ''
        self.env['ir.config_parameter'].set_param('ss_api_secret', ss_api_secret, groups=["base.group_system"])

    @api.model
    def get_default_ss_api(self, fields):
        params = self.env['ir.config_parameter'].sudo()
        ss_api_key = params.get_param('ss_api_key', default='')
        ss_api_secret = params.get_param('ss_api_secret', default='')
        return {'ss_api_key': ss_api_key,
                'ss_api_secret': ss_api_secret
                }