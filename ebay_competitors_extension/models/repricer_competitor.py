# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RepricerCompetitor(models.Model):
    _inherit = 'repricer.competitor'

    history_ids = fields.One2many('repricer.competitor.history', 'comp_id', 'History')
    history_count = fields.Integer('History Count', compute='_compute_history_count')

    @api.multi
    @api.depends('history_ids')
    def _compute_history_count(self):
        for c in self:
            c.history_count = len(c.history_ids)

    @api.multi
    def action_view_history(self):
        action = self.env.ref('ebay_competitors_extension.action_repricer_competitor_history')
        result = action.read()[0]
        result['context'] = {'search_default_comp_id': [self.id]}
        return result


class RepricerCompetitorHistory(models.Model):
    _name = 'repricer.competitor.history'
    _description = 'Competitor History'
    _rec_name = 'comp_id'
    _order = 'id desc'

    comp_id = fields.Many2one('repricer.competitor', 'Item ID', required=True)
    price = fields.Float('Price')
    qty_sold = fields.Float('Qty Sold')
