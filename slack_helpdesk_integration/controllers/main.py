# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import threading

from requests import request as external_request
from time import sleep

from odoo import http, api
from odoo.http import request

class SlackIntegration(http.Controller):

    @http.route('/slack/dev/newticket', type='http', auth="public", csrf=False)
    def slack_dev_new_ticket(self, **post):
        new_thread = threading.Thread(target=request.env['helpdesk.ticket'].create_new_ticket, kwargs=post)
        new_thread.start()
        headers = {'Content-Type': 'application/json'}
        response = request.make_response('', headers)
        response.status = '200'
        return response

    @http.route('/slack/newticket', type='http', auth="public", csrf=False)
    def slack_new_ticket(self, **post):
        new_thread = threading.Thread(target=request.env['helpdesk.ticket'].create_new_ticket, kwargs=post)
        new_thread.start()
        headers = {'Content-Type': 'application/json'}
        response = request.make_response('', headers)
        response.status = '200'
        return response

    @http.route('/slack/showticket', type='http', auth="public", csrf=False)
    def slack_show_ticket(self, **post):
        ParamsObj = request.env['ir.config_parameter'].sudo()
        token = ParamsObj.get_param('slack_verification_token')
        res = {'text': 'Something went wrong there. Please advise your super admin!'}
        if post.get('token') == token:
            user_id = request.env['res.users'].sudo().search([('slack_user_id', '=', post.get('user_id'))])
            text = post.get('text')
            res = request.env['helpdesk.ticket'].sudo().slack_show_ticket(user_id, text)
        headers = {'Content-Type': 'application/json'}
        response = request.make_response(json.dumps(res), headers)
        response.status = '200'
        return response

    @http.route('/slack/mytickets', type='http', auth="public", csrf=False)
    def slack_show_my_tickets(self, **post):
        ParamsObj = request.env['ir.config_parameter'].sudo()
        token = ParamsObj.get_param('slack_verification_token')
        res = {'text': 'Something went wrong there. Please advise your super admin!'}
        if post.get('token') == token:
            user_id = request.env['res.users'].sudo().search([('slack_user_id', '=', post.get('user_id'))])
            res = request.env['helpdesk.ticket'].sudo().slack_show_my_tickets(user_id, 0)
        headers = {'Content-Type': 'application/json'}
        response = request.make_response(json.dumps(res), headers)
        response.status = '200'
        return response

    @http.route('/slack/oauth/login', type='http', auth="user")
    def slack_oauth_login(self, **post):
        code = post.get('code', False)
        state = post.get('state', False)
        if state == request.env.user.slack_oauth_get_state():
            slack_endpoint = 'https://slack.com/api/oauth.access'
            ParamsObj = request.env['ir.config_parameter'].sudo()
            params = {
                'client_id': ParamsObj.get_param('slack_client_id'),
                'client_secret': ParamsObj.get_param('slack_client_secret'),
                'code': code,
                'redirect_uri': request.env.user.slack_oauth_get_redirect_uri()
            }
            response = request.env.user.slack_execute_request('POST', 'oauth.access', data=params)
            if 'access_token' in response:
                request.env.user.write({
                    'slack_access_token': response['access_token'],
                    'slack_scope': response['scope'],
                    'slack_user_id': response['user_id']
                })
            return http.redirect_with_hash('/web?')

    @http.route('/slack/actions', type='http', auth="public", csrf=False)
    def slack_actions(self, **post):
        ParamsObj = request.env['ir.config_parameter'].sudo()
        token = ParamsObj.get_param('slack_verification_token')
        message = {'text': 'Something went wrong there. Please advise your super admin!'}
        data = json.loads(post['payload'])
        actions = data.get('actions', [])
        user = data.get('user', {})
        if data.get('token') == token and actions and user:
            user_id = request.env['res.users'].sudo().search([('slack_user_id', '=', user['id'])])
            action = actions[0]
            if user_id:
                if action['name'] == 'view_more':
                    message = request.env['helpdesk.ticket'].sudo().slack_show_my_tickets(user_id, int(data.get('callback_id')))
                    headers = {'Content-Type': 'application/json'}
                    response = request.make_response(json.dumps(message), headers)
                    response.status = '200'
                    return response
                else:
                    message = data.get('original_message')
                    ticket_id = request.env['helpdesk.ticket'].sudo(user_id).search([('id', '=', int(message['attachments'][0]['callback_id']))])

                    if action['name'] == 'assign_to_self':
                        ticket_id.write({'user_id': user_id.id })
                        attachments = ticket_id.get_ticket_attachments(True)
                        message['attachments'][0] = attachments[0]
                        message['attachments'].append({
                            'text': '<@%s> took the ticket!' %user_id.slack_user_id
                        })
                        headers = {'Content-Type': 'application/json'}
                        response = request.make_response(json.dumps(message), headers)
                        response.status = '200'
                        return response

                    elif action['name'] in ['process', 'close']:
                        stage_id = False
                        if action['name'] == 'process':
                            stage_id = ticket_id.team_id.stage_ids.filtered(lambda r: r.name == 'In Progress')
                            if stage_id:
                                ticket_id.write({'stage_id': stage_id.id })
                            message['attachments'].append({
                                'text': '<@%s> is now working on the ticket.' %user_id.slack_user_id
                            })
                        elif action['name'] == 'close':
                            stage_id = ticket_id.team_id.stage_ids.filtered(lambda r: r.name == 'Done')
                            if stage_id:
                                ticket_id.write({'stage_id': stage_id.id })
                                message['attachments'].append({
                                    'text': '<@%s> closed the ticket.' %user_id.slack_user_id
                                })
                        attachments = ticket_id.get_ticket_attachments(True)
                        message['attachments'][0] = attachments[0]
                        headers = {'Content-Type': 'application/json'}
                        response = request.make_response(json.dumps(message), headers)
                        response.status = '200'
                        return response

                    elif action['name'] == 'set_priority':
                        priority_value = action['selected_options'][0]['value']
                        ticket_id.write({'priority':  priority_value})
                        priority_options_dict = {'0': 'None', '1': 'Low Priority', '2': 'High Priority', '3': 'Urgent'}
                        message['attachments'].append({
                            'text': '<@%s> set this ticket to %s.' %(user_id.slack_user_id, priority_options_dict[priority_value])
                        })
                        attachments = ticket_id.get_ticket_attachments(True)
                        message['attachments'][0] = attachments[0]
                        headers = {'Content-Type': 'application/json'}
                        response = request.make_response(json.dumps(message), headers)
                        response.status = '200'
                        return response

                    elif action['name'] == 'set_team':
                        team_id = int(action['selected_options'][0]['value'])
                        ticket_id.write({'team_id':  team_id})
                        message['attachments'].append({
                            'text': '<@%s> assigned this ticket to %s.' %(user_id.slack_user_id, ticket_id.team_id.name)
                        })
                        attachments = ticket_id.get_ticket_attachments(True)
                        message['attachments'][0] = attachments[0]
                        headers = {'Content-Type': 'application/json'}
                        response = request.make_response(json.dumps(message), headers)
                        response.status = '200'
                        return response
