# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class AssignPicksLineWizard(models.TransientModel):
    _name = 'stock.assign.picks.line.wizard'

    user_id = fields.Many2one('res.users', 'Users', domain=[('wh_picker', '=', True)])
    picks_count = fields.Integer('Picks to Assign', default=120)
    wizard_id = fields.Many2one('stock.assign.picks.wizard', 'Wizard')

class AssignPicksWizard(models.TransientModel):
    _name = 'stock.assign.picks.wizard'

    line_ids = fields.One2many('stock.assign.picks.line.wizard', 'wizard_id', 'Pickers')

    # @api.multi
    # def assign_picks(self):
    #     wh_id = self.env['stock.warehouse'].search([], limit=1)
    #     if wh_id:
    #         pick_ids = self.env['stock.picking'].search([('picking_type_id', '=', wh_id.pick_type_id.id), ('state', 'not in', ('cancel', 'done'))])
    #         for p in pick_ids:
