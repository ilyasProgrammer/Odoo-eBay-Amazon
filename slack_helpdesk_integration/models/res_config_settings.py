# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
import random

class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    slack_client_id = fields.Char(string='Client ID')
    slack_client_secret = fields.Char(string='Client Secret')
    slack_oauth_access_token = fields.Char(string='OAuth Access Token')
    slack_verification_token = fields.Char(string='Verification Token')
    slack_team_id = fields.Char(string='Team ID')
    slack_bot_token = fields.Char(string='Bot Token')

    @api.multi
    def set_slack_settings(self):
        slack_client_id = self[0].slack_client_id or ''
        self.env['ir.config_parameter'].set_param('slack_client_id', slack_client_id, groups=["base.group_user"])
        slack_client_secret = self[0].slack_client_secret or ''
        self.env['ir.config_parameter'].set_param('slack_client_secret', slack_client_secret, groups=["base.group_user"])
        slack_oauth_access_token = self[0].slack_oauth_access_token or ''
        self.env['ir.config_parameter'].set_param('slack_oauth_access_token', slack_oauth_access_token, groups=["base.group_user"])
        slack_verification_token = self[0].slack_verification_token or ''
        self.env['ir.config_parameter'].set_param('slack_verification_token', slack_verification_token, groups=["base.group_user"])
        slack_team_id = self[0].slack_team_id or ''
        self.env['ir.config_parameter'].set_param('slack_team_id', slack_team_id, groups=["base.group_user"])
        slack_bot_token = self[0].slack_bot_token or ''
        self.env['ir.config_parameter'].set_param('slack_bot_token', slack_bot_token, groups=["base.group_user"])

    @api.model
    def get_default_slack_settings(self, fields):
        params = self.env['ir.config_parameter'].sudo()
        slack_client_id = params.get_param('slack_client_id', default='')
        slack_client_secret = params.get_param('slack_client_secret', default = '')
        slack_oauth_access_token = params.get_param('slack_oauth_access_token', default='')
        slack_team_id = params.get_param('slack_team_id', default='')
        slack_verification_token = params.get_param('slack_verification_token', default='')
        slack_bot_token = params.get_param('slack_bot_token', default='')
        return {
            'slack_client_id': slack_client_id,
            'slack_client_secret': slack_client_secret,
            'slack_oauth_access_token': slack_oauth_access_token,
            'slack_team_id': slack_team_id,
            'slack_verification_token': slack_verification_token,
            'slack_bot_token': slack_bot_token
        }
