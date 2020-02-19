# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug.utils
from requests import request
from requests.exceptions import HTTPError

from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    slack_access_token = fields.Char('Slack Access Token')
    slack_scope = fields.Char('Slack Scope')
    slack_user_id = fields.Char('Slack User ID')

    @api.model
    def slack_execute_request(self, verb, endpoint, data=None):
        ParamsObj = self.env['ir.config_parameter'].sudo()
        token = ParamsObj.get_param('slack_oauth_access_token')
        headers = {'Authorization': 'Bearer ' + token }
        url = 'https://slack.com/api/' + endpoint
        try:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            response = request(verb, url, data=data, headers=headers)
            response.raise_for_status()
        except HTTPError, e:
            pass

        return json.loads(response.content)

    @api.model
    def slack_execute_request_to_response_url(self, response_url):
        ParamsObj = self.env['ir.config_parameter'].sudo()
        token = ParamsObj.get_param('slack_oauth_access_token')
        headers = {'Authorization': 'Bearer ' + token }
        try:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            response = request('POST', response_url, data=data, headers=headers)
            response.raise_for_status()
        except HTTPError, e:
            pass

        return json.loads(response.content)

    @api.multi
    def slack_oauth_get_state(self):
        return str(self.id) + self.login

    @api.model
    def slack_oauth_get_redirect_uri(self):
        return self.env['ir.config_parameter'].get_param('web.base.url') + '/slack/oauth/login'

    @api.multi
    def preference_connect_with_slack(self):
        slack_endpoint = 'https://slack.com/oauth/authorize'

        ParamsObj = self.env['ir.config_parameter'].sudo()
        params = {
            'client_id': ParamsObj.get_param('slack_client_id'),
            'team': ParamsObj.get_param('slack_team_id'),
            'redirect_uri': self.slack_oauth_get_redirect_uri(),
            'scope': 'incoming-webhook, commands, chat:write:user, chat:write:bot, bot',
            'state': self.slack_oauth_get_state(),
        }

        return {
            'type': 'ir.actions.act_url',
            'url': '%s?%s' % (slack_endpoint, werkzeug.url_encode(params)),
            'target': 'self',
        }
