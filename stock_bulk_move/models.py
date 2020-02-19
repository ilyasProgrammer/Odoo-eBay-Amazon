# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_log = logging.getLogger(__name__)


class StockBulkMove(models.TransientModel):
    _name = 'stock.bulk.move'

    source_location = fields.Many2one('stock.location')
    dest_location = fields.Many2one('stock.location')
    include_descendants = fields.Boolean('Include descendant locations', default=False, help="In case if WH/Stock/A is selected then locations like WH/Stock/A/A-1-A-1 will be included according to hierarchy.")
    lines = fields.Many2many('stock.bulk.move.line')
    pickings = fields.Many2many('stock.picking')

    # @api.multi
    # @api.onchange('lines')
    # def onchanhe_qty(self):
    #     for l in self.lines:
    #         l.qty = l.qty

    @api.multi
    def load_stock(self):
        if self.include_descendants:
            stock = self.env['stock.quant'].search([('location_id', 'child_of', self.source_location.id),
                                                    ('reservation_id', '=', False),
                                                    ('qty', '>', 0)])
        else:
            stock = self.env['stock.quant'].search([('location_id', '=', self.source_location.id),
                                                    ('reservation_id', '=', False),
                                                    ('qty', '>', 0)])
        if stock:
            nl = self.env['stock.bulk.move.line']
            for el in stock:
                nl += self.env['stock.bulk.move.line'].create({'marked': True, 'quant': el.id, 'qty': el.qty})
            self.lines = [(6, 0, nl.ids)]
        else:  # no stock
            self.lines = [(5, 0, 0)]
        view_id = self.env['ir.ui.view'].search([('model', '=', 'stock.bulk.move')])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.bulk.move',
            'name': 'Bulk Move',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id.id,
            'target': 'new',
            'nodestroy': True,
            'context': self.env.context
        }

    @api.multi
    def move_all_quants(self):
        if self.include_descendants:
            locs = set([r.quant.location_id for r in self.lines])
            for loc in locs:
                self.proceed_move(loc)
        else:
            self.proceed_move()
        view_id = self.env['ir.ui.view'].search([('model', '=', 'stock.bulk.move')])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.bulk.move',
            'name': 'Bulk Move',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id.id,
            'target': 'new',
            'nodestroy': True,
            'context': self.env.context
        }

    @api.multi
    def uncheck_all(self):
        for line in self.lines:
            line.marked = False
        view_id = self.env['ir.ui.view'].search([('model', '=', 'stock.bulk.move')])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.bulk.move',
            'name': 'Bulk Move',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id.id,
            'target': 'new',
            'nodestroy': True,
            'context': self.env.context
        }

    @api.multi
    def proceed_move(self, loc=None):
        StockPicking = self.env['stock.picking']
        vals = {
            'picking_type_id': 5,  # internal transfer
            'origin': 'Bulk Move',
            'location_dest_id': self.dest_location.id,
            'location_id': loc.id if loc else self.source_location.id,
            'company_id': self.env.context.get('company_id') or self.env.user.company_id.id,
        }
        picking = StockPicking.create(vals)
        _log.info('Picking created: %s', picking)
        moves = self._create_stock_moves(picking, loc if loc else self.source_location, self.dest_location)
        _log.info('Moves created: %s', moves.ids)
        moves = moves.filtered(lambda x: x.state not in ('cancel')).action_confirm()
        moves.force_assign()
        _log.info('Moves assigned: %s', moves.ids)
        for pack in picking.pack_operation_ids:
            if pack.product_qty > 0:
                pack.write({'qty_done': pack.product_qty})
        picking.action_confirm()
        _log.info('Picking confirmed: %s', picking)
        picking.do_transfer()
        _log.info('Picking transfer done: %s', picking)
        self.pickings = [(4, picking.id, 0)]  # add to existing

    @api.multi
    def _create_stock_moves(self, picking, src, dst):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self.lines:
            if not line.marked or line.quant.location_id.id != src.id:
                continue
            template = {
                'name': line.quant.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.quant.product_uom_id.id,
                'date': picking.date,
                'location_id': src.id,
                'location_dest_id': dst.id,
                'picking_id': picking.id,
                'company_id': picking.company_id.id,
                'picking_type_id': 5,  # internal transfer
                'procurement_id': False,
                'origin': 'Bulk Move',
                'route_ids': [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id or 1,
                'landed_cost': line.quant.landed_cost,
                'product_uom_qty': line.qty,  # TODO add onchange
                'state': 'done',
                'quant_ids': [line.quant.id]
            }
            done += moves.create(template)
        return done


class StockBulkMoveLine(models.TransientModel):
    _name = 'stock.bulk.move.line'

    marked = fields.Boolean()
    quant = fields.Many2one('stock.quant')
    product_id = fields.Many2one(related='quant.product_id')
    qty = fields.Float('Qty to move', default=0)
    location_id = fields.Many2one(related='quant.location_id')
