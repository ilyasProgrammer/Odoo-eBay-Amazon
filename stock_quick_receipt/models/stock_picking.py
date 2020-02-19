# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pending_picks_count = fields.Integer('# of Pending Picks', compute='_compute_pending_picks_count')

    @api.multi
    @api.depends('location_id')
    def _compute_pending_picks_count(self):
        for p in self:
            if p.location_id and p.state == 'draft':
                pack_op_ids = self.env['stock.pack.operation'].search([('picking_id.state', 'not in', ['cancel', 'done']), ('location_id', '=', p.location_id.id)])
                p.pending_picks_count = len(pack_op_ids.mapped('picking_id'))
            else:
                p.pending_picks_count = 0

    @api.multi
    def button_view_pending_picks(self):
        if self.location_id and self.state == 'draft':
            pack_op_ids = self.env['stock.pack.operation'].search([('picking_id.state', 'not in', ['cancel', 'done']), ('location_id', '=', self.location_id.id)])
            pending_pick_ids = pack_op_ids.mapped('picking_id')
            return {
                'name': 'Pending Picks',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', pending_pick_ids.ids)],
            }

    @api.multi
    def set_qty_done_to_zero(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            self.pack_operation_product_ids.unlink()
            self.action_assign()

    @api.multi
    def show_current_stocks(self):
        if self.state == 'draft':
            self.move_lines.unlink()
            if not (self.location_id and self.location_dest_id):
                raise UserError('Please specify source location.')
            quant_ids = self.env['stock.quant'].search([('qty', '>', '0'), ('location_id', '=', self.location_id.id)])
            moves = []
            for quant_id in quant_ids:
                moves.append((0, 0, {
                    'product_uom_qty': quant_id.qty,
                    'product_id': quant_id.product_id.id,
                    'name': quant_id.product_id.name,
                    'product_uom': quant_id.product_id.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id
                }))
            self.write({'move_lines': moves})
