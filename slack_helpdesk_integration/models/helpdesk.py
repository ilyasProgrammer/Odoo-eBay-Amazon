# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
from datetime import datetime
from requests import request
import os
import calendar
from odoo import models, fields, api
from slackclient import SlackClient
import logging
_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model
    def create(self, vals):
        res = super(HelpdeskTicket, self).create(vals)
        if res.recurring_id:
            try:
                res.push_to_slack()
            except:
                pass
        return res

    @api.model
    def push_to_slack(self):
        slack_token = self.env['ir.config_parameter'].get_param('slack_bot_token')
        sc = SlackClient(slack_token)
        res = sc.api_call("im.list")  # list of direct chats between bot and members
        for ticket in self:
            user_im = filter(lambda im: im['user'] == ticket.user_id.slack_user_id, res['ims'])
            if not len(user_im):
                user_im_id = sc.api_call(
                    "im.open",
                    return_im=True,
                    user=ticket.user_id.slack_user_id
                )
            else:
                user_im_id = user_im[0]['id']
            sc.api_call(
                "chat.postMessage",
                channel=user_im_id,
                as_user=False,
                username='Bender',
                text="New ticket created for you:",
                attachments=ticket.get_ticket_attachments(True)
            )
            _logger.info('Pushed ticket to slack: %s %s', self.user_id.login, self.name)

    @api.multi
    def create_new_ticket(self, **post):
        with api.Environment.manage():
            # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            ParamsObj = self.env['ir.config_parameter'].sudo()
            token = ParamsObj.get_param('slack_verification_token')
            res = {'text': 'Something went wrong there. Please advise your super admin!'}

            if post.get('token') == token:
                creator_id = self.env['res.users'].sudo().search([('slack_user_id', '=', post.get('user_id'))])
                text = post.get('text')
                res = self.env['helpdesk.ticket'].sudo(creator_id).slack_create_new_ticket(text)
                self.env.cr.commit()
                headers= {'Content-Type': 'application/json'}
                request('POST', post.get('response_url'), data=json.dumps(res), headers=headers)
            self._cr.close()
            return {}

    @api.multi
    def dev_create_new_ticket(self, **post):
        ParamsObj = self.env['ir.config_parameter'].sudo()
        token = ParamsObj.get_param('slack_verification_token')
        res = {'text': 'Something went wrong there. Please advise your super admin!'}

        if post.get('token') == token:
            creator_id = self.env['res.users'].sudo().search([('slack_user_id', '=', post.get('user_id'))])
            text = post.get('text')
            res = self.env['helpdesk.ticket'].sudo(creator_id).slack_create_new_ticket(text)
            headers= {'Content-Type': 'application/json'}
            request('POST', post.get('response_url'), data=json.dumps(res), headers=headers)

    @api.multi
    def get_ticket_url(self):
        menu_id = self.env.ref('helpdesk.menu_helpdesk_root')
        action_id = self.env.ref('helpdesk.helpdesk_ticket_action_team')
        ticket_url = self.env['ir.config_parameter'].get_param('web.base.url') + '/web?#id=%s&view_type=form&model=helpdesk.ticket&action=%s&active_id=%s&menu_id=%s' %(self.id, action_id.id, self.team_id.id, menu_id.id)
        return ticket_url

    @api.multi
    def get_ticket_attachments(self, complete_actions):

        def get_epoch_time(sdt):
            d = datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')
            return calendar.timegm(d.utctimetuple())

        short_title = self.name
        if len(self.name) > 200:
            short_title = self.name[0:200] + '...'

        ticket_url = self.get_ticket_url()

        priority_options_dict = {'0': 'None', '1': 'Low Priority', '2': 'High Priority', '3': 'Urgent'}
        priority_options = []
        for p in priority_options_dict:
            if p == '0':
                continue
            priority_options.append({'value': p, 'text': priority_options_dict[p]})

        priority_options = sorted(priority_options, key=lambda k: k['value'])

        team_ids = self.env['helpdesk.team'].search([])
        team_options = [{'value': t.id, 'text': t.name} for t in team_ids]

        ticket_fields = []
        assigned_to = 'None'
        if self.user_id.slack_user_id:
            assigned_to = '<@%s>.' %self.user_id.slack_user_id
        elif self.user_id:
            assigned_to = self.user_id.name
        ticket_fields.append({'title': 'Assigned to', 'value': assigned_to, 'short': True})
        ticket_fields.append({'title': 'Team', 'value': self.team_id.name, 'short': True})
        ticket_fields.append({'title': 'Status', 'value': self.stage_id.name, 'short': True})

        if self.priority in priority_options_dict:
            ticket_fields.append({'title': 'Priority', 'value': priority_options_dict[self.priority], 'short': True})

        if self.create_date:
            create_date = '<!date^%s^{date_num} {time_secs}|%s>' %(get_epoch_time(self.create_date), self.create_date)
            ticket_fields.append({'title': 'Created', 'value': create_date, 'short': True})

        if self.write_date:
            update_date = '<!date^%s^{date_num} {time_secs}|%s>' %(get_epoch_time(self.write_date), self.write_date)
            ticket_fields.append({'title': 'Last updated', 'value': update_date, 'short': True})

        actions = []
        if complete_actions:
            actions = [
                {'name': 'set_priority', "text": 'Set priority', 'type': 'select', 'value': '%s' %self.id, 'options': priority_options},
                {'name': 'set_team', "text": 'Set team', 'type': 'select', 'value': '%s' %self.id, 'options': team_options},
                {'name': 'assign_to_self', "text": 'I take it!', 'type': 'button', 'value': '%s' %self.id},
                {'name': 'process', "text": "Working on it!", 'type': 'button', 'value': '%s' %self.id},
                {'name': 'close', "text": "Close", 'type': 'button', 'value': '%s' %self.id},
            ]
        return [{
            'callback_id': "%s" %self.id,
            'fallback': 'Ticket#%s: %s has been assigned to %s. Follow at %s.' %(self.id, short_title, self.user_id.name, ticket_url),
            'title': 'Ticket#%s: %s' %(self.id, short_title),
            'title_link': ticket_url,
            'text': self.description or '',
            'actions': actions,
            'fields': ticket_fields,
            'color': '#7CD197'
        }]


    @api.model
    def slack_create_new_ticket(self, text):
        team_id = self.env['helpdesk.team'].search([], limit=1)
        pattern = r'<@(.+?)>+?'
        users = re.findall(pattern, text)

        text_split = text.split('\n', 1)
        title = text_split[0]
        description = ''
        if len(text_split) > 1:
            description = text_split[1]

        user_id = self.env['res.users']
        if len(users) > 1:
            user_id = self.env['res.users'].sudo().search([('slack_user_id', '=', users[0].split('|')[0])])

        title = title.replace('<@%s>' %users[0], '')

        for u in users:
            user_id = self.env['res.users'].sudo().search([('slack_user_id', '=', u.split('|')[0])])
            title = title.replace('<@%s>' %u, user_id.name)
            description = description.replace('<@%s>' %u, user_id.name)

        title = ' '.join(title.split())
        description = ' '.join(description.split())

        if title[-1] == ' ':
            title = title[:-1]
        if title[0] == ' ':
            title = title[1:]
        if description and description[-1] == ' ':
            description = description[:-1]
        if description and description[0] == ' ':
            description = description[1:]
        ticket_id = self.create({
            'name': title,
            'team_id': team_id.id,
            'user_id': user_id.id if user_id else False,
            'description': description
        })

        if ticket_id.user_id and ticket_id.user_id.slack_user_id:
            main_text = 'A ticket has been assigned to <@%s>.' %ticket_id.user_id.slack_user_id
        else:
            main_text = 'A ticket has been created.'

        attachments = ticket_id.get_ticket_attachments(True)

        message = {
            'response_type': 'in_channel',
            'text': main_text,
            'attachments': attachments
        }
        return message

    @api.model
    def slack_show_ticket(self, user_id, text):
        pos = text.find('#')

        ticket_id = self
        try:
            ticket_id = self.search([('id', '=', int(text[pos + 1:]))])
        except:
            return {'text': 'That does not seem to be a valid ticket number.'}

        if not ticket_id:
            return {'text': "That ticket can't be found."}

        attachments = ticket_id.get_ticket_attachments(True)

        message = {
            'response_type': 'in_channel',
            'text': 'Here are the details of that ticket.',
            'attachments': attachments
        }
        return message

    @api.model
    def slack_show_my_tickets(self, user_id, last_id):
        domain = [('user_id', '=', user_id.id), ('stage_id.name', 'in', ('New', 'In Progress')), ('id', '>', last_id)]
        ticket_ids_count = self.search(domain, count=True)
        ticket_ids = self.search(domain, order='id asc', limit=6)

        attachments = []
        if ticket_ids:
            ticket_counter = 1
            last_ticket_id = ticket_ids[0]
            for ticket_id in ticket_ids:
                if ticket_counter > 5:
                    attachments[-1]['actions'].append({'name': 'view_more', "text": 'View More', 'type': 'button', 'value': '%s' %last_ticket_id.id})
                    break
                ticket_attachments = ticket_id.get_ticket_attachments(False)
                attachments.append(ticket_attachments[0])
                last_ticket_id = ticket_id
                ticket_counter += 1

        message = {
            'text': 'You have %s open tickets.' %ticket_ids_count,
            'attachments': attachments
        }
        return message
