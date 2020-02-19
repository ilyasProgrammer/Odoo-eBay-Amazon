# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
import random

class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    endpoint_auth_token = fields.Char(string='Endpoints Auth Token', help='Token for authenticating endpoint requests')

    @api.multi
    def set_endpoint_auth_token(self):
        endpoint_auth_token = self[0].endpoint_auth_token or ''
        self.env['ir.config_parameter'].set_param('endpoint_auth_token', endpoint_auth_token, groups=["base.group_user"])

    @api.model
    def get_default_endpoint_auth_token(self, fields):
        params = self.env['ir.config_parameter'].sudo()
        endpoint_auth_token = params.get_param('endpoint_auth_token', default='')
        return {'endpoint_auth_token': endpoint_auth_token}

    @api.multi
    def generate_new_endpoint_token(self):
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        self.endpoint_auth_token = ''.join(random.SystemRandom().choice(chars) for i in xrange(20))

