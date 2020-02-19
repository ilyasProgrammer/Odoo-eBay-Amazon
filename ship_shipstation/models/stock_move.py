# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_confirm(self):
        procs_to_check = []
        for move in self:
            if move.procurement_id and move.procurement_id.sale_line_id:
                procs_to_check += [move.procurement_id]
        res = super(StockMove, self).action_confirm()
        for proc in procs_to_check:
            pickings = (proc.move_ids.mapped('picking_id')).filtered(lambda record: not record.carrier_id)
            if pickings:
                pickings.write({
                    'sale_id': proc.sale_line_id.order_id.id,
                    'length': proc.sale_line_id.order_id.length,
                    'width': proc.sale_line_id.order_id.width,
                    'height': proc.sale_line_id.order_id.height,
                    'weight': proc.sale_line_id.order_id.weight,
                    'carrier_id': proc.sale_line_id.order_id.carrier_id.id,
                    'service_id': proc.sale_line_id.order_id.service_id.id,
                    'package_id': proc.sale_line_id.order_id.package_id.id,
                    'rate': proc.sale_line_id.order_id.rate,
                    'warehouse_id': proc.sale_line_id.order_id.warehouse_id.id,
                    'store_id': proc.sale_line_id.order_id.store_id.id
                })
        return res

    def _get_new_picking_values(self):
        values = super(StockMove, self)._get_new_picking_values()
        sale_line_id = self.procurement_id.sale_line_id
        if sale_line_id:
            values['store_id'] = sale_line_id.order_id.store_id.id
        return values

    def _prepare_procurement_from_move(self):
        values = super(StockMove, self)._prepare_procurement_from_move()
        values['sale_line_id'] = self.procurement_id.sale_line_id.id
        return values
