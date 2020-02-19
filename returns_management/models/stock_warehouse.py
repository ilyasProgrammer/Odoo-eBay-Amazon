# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    process_returns = fields.Boolean('Process Returns', default=True, help="Returns are in a specific queue in the warehouse dashboard.")
    return_type_id = fields.Many2one('stock.picking.type', 'Returns', domain=[('code', '=', 'incoming')])

    @api.model
    def _create_return_picking_type(self):
        picking_type_obj = self.env['stock.picking.type']
        seq_obj = self.env['ir.sequence']
        for warehouse in self:
            wh_stock_loc = warehouse.lot_stock_id
            seq = seq_obj.search([('code', '=', 'wh.return.picking.type')], limit=1)
            other_pick_type = picking_type_obj.search([('warehouse_id', '=', warehouse.id)], order = 'sequence desc', limit=1)
            color = other_pick_type and other_pick_type.color or 0
            max_sequence = other_pick_type and other_pick_type.sequence or 0
            return_type = picking_type_obj.create({
                'name': _('Returns'),
                'warehouse_id': warehouse.id,
                'code': 'return',
                'use_create_lots': True,
                'use_existing_lots': False,
                'sequence_id': seq.id,
                'default_location_src_id': self.env.ref('stock.stock_location_customers').id,
                'default_location_dest_id': wh_stock_loc.id,
                'sequence': max_sequence,
                'color': color})
            warehouse.write({'return_type_id': return_type.id})

    @api.multi
    def write(self, vals):
        if 'process_returns' in vals:
            if vals.get("process_returns"):
                for warehouse in self:
                    if not warehouse.return_type_id:
                        warehouse._create_return_picking_type()
                    warehouse.return_type_id.active = True
            else:
                for warehouse in self:
                    if warehouse.return_type_id:
                        warehouse.return_type_id.active = False
        return super(StockWarehouse, self).write(vals)
