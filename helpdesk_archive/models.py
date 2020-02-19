# -*- coding: utf-8 -*-

from odoo import models, api, fields
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model
    def archive_old(self):
        all_teams = self.env['helpdesk.team'].search([])
        for team in all_teams:
            arch = self.env['helpdesk.stage'].search([('team_ids', 'in', [team.id]), ('name', '=', 'Archived')])
            done = self.env['helpdesk.stage'].search([('team_ids', 'in', [team.id]), ('name', '=', 'Done')])
            if arch and done:
                done_recs = self.env['helpdesk.ticket'].sudo().search([('stage_id', '=', done.id)])
                for rec in done_recs:
                    wr_time = datetime.strptime(rec.write_date, '%Y-%m-%d %H:%M:%S')  # simple way. Actually it is necessary to look history table to find out stage changing time.
                    now = datetime.now()
                    if (now - wr_time).days >= 14:
                        rec.stage_id = arch.id
                        _logger.info('Ticket stage updated: %s %s', rec.id, rec.name)
