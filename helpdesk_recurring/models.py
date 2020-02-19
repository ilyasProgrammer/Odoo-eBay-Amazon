# -*- coding: utf-8 -*-

from odoo import models, api, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime
import logging
import pytz
_logger = logging.getLogger(__name__)

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class Ticket(models.Model):
    _inherit = 'helpdesk.ticket'

    recurring_id = fields.Many2one('helpdesk.ticket.recurring')


class HelpdeskRecurring(models.Model):
    _name = 'helpdesk.ticket.recurring'

    def _default_team_id(self):
        team_id = self._context.get('default_team_id')
        if not team_id:
            team_id = self.env['helpdesk.team'].search([('member_ids', 'in', self.env.uid)], limit=1).id
        if not team_id:
            team_id = self.env['helpdesk.team'].search([], limit=1).id
        return team_id

    ticket_ids = fields.One2many('helpdesk.ticket', 'recurring_id')
    name = fields.Char('Title', required=True)
    description = fields.Text('Description')
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', default=_default_team_id, index=True)
    user_id = fields.Many2one('res.users', string='Assigned to')
    interval_number = fields.Integer(default=1, help="Repeat every x.")
    interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('work_days', 'Work Days'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='months')
    nextcall = fields.Datetime(string='Next Execution Date', required=True, default=fields.Datetime.now, help="Next planned execution date for this job.")
    tickets_number = fields.Integer(compute='_get_tickets_number', string="Number of Tickets")

    @api.multi
    def _get_tickets_number(self):
        for record in self:
            record.tickets_number = len(record.ticket_ids)

    @api.model
    def create_tickets(self):
        recs = self.env['helpdesk.ticket.recurring'].search([])
        for rec in recs:
            vals = {'recurring_id': rec.id,
                    'description': rec.description,
                    'name': rec.name,
                    'team_id': rec.team_id.id,
                    'user_id': rec.user_id.id,
                    }
            now = fields.Datetime.context_timestamp(rec, datetime.now())
            nextcall = fields.Datetime.context_timestamp(rec, fields.Datetime.from_string(rec.nextcall))
            while nextcall < now:
                if rec.interval_type == 'work_days' and nextcall.weekday() in [5, 6]:
                    nextcall += _intervalTypes['days'](1)
                    _logger.info('Skip weekend')
                    continue
                new_ticket = self.env['helpdesk.ticket'].with_context(mail_create_nosubscribe=True).create(vals)
                nextcall += _intervalTypes[rec.interval_type](rec.interval_number)
                _logger.info('New ticket: %s', new_ticket)
                rec.nextcall = nextcall.astimezone(pytz.UTC)

    @api.multi
    def action_get_tickets_tree_view(self):
        action = self.env.ref('helpdesk_recurring.action_tickets_from_recurring_tree')
        result = action.read()[0]
        #override the context to get rid of the default filtering on picking type
        result['context'] = {}
        ticket_ids = sum([r.ticket_ids.ids for r in self], [])
        #choose the view_mode accordingly
        if len(ticket_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, ticket_ids)) + "])]"
        elif len(ticket_ids) == 1:
            res = self.env.ref('helpdesk.helpdesk_ticket_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = ticket_ids and ticket_ids[0] or False
        return result
