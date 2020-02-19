# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    amz_order_type = fields.Selection([('ebay', 'eBay'),  # pour le eBay
                                       ('normal', 'Normal'),  # pour le Amazon
                                       ('fbm', 'FBM (Prime)'),  # pour le Amazon Prime
                                       ('fba', 'FBA')  # pour le Amazon
                                       ], string='Order type')
    amz_order_type_code = fields.Selection([('e1', 'E1'),
                                            ('a1', 'A1'),
                                            ('p1', 'P1'),
                                            ('f1', 'F1')
                                            ], compute='_set_amz_order_type_code', string='Order code')

    @api.one
    @api.depends('amz_order_type')
    def _set_amz_order_type_code(self):
        if self.amz_order_type == 'ebay':
            self.amz_order_type_code = 'e1'
        elif self.amz_order_type == 'normal':
            self.amz_order_type_code = 'a1'
        elif self.amz_order_type == 'fbm':
            self.amz_order_type_code = 'p1'
        elif self.amz_order_type == 'fba':
            self.amz_order_type_code = 'f1'

    @api.multi
    def cron_validate_fba_picks(self):
        self.env['slack.calls'].notify_slack('[STORE] Validate FBA Picks', 'Started at %s' % datetime.utcnow())
        # fba_picks = self.search([('picking_type_id', '=', 11), ('state', 'not in', ['cancel', 'done', 'draft'])], limit=40)
        fba_picks = self.search([('picking_type_id', '=', 11), ('state', 'in', ['assigned'])])
        for fp in fba_picks:
            # fp.force_assign()
            # fp.action_assign()
            for r in fp['pack_operation_ids']:
                r.qty_done = r.ordered_qty
            try:
                res = fp.do_new_transfer()
                self.env.cr.commit()
            except Exception as e:
                pass
        self.env['slack.calls'].notify_slack('[STORE] Validate FBA Picks', 'Ended at %s' % datetime.utcnow())
