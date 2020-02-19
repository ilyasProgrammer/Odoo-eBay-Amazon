# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    receipt_return_id = fields.Many2one('sale.return', 'Receipt Return')
    replacement_return_id = fields.Many2one('sale.return', 'Replacement Return')
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")

    @api.multi
    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        if self.receipt_return_id:
            self.receipt_return_id.set_main_state()
        if self.replacement_return_id:
            self.replacement_return_id.set_main_state()
        return res

    @api.one
    @api.depends('group_id')
    def _compute_sale_id(self):
        for picking in self:
            sale_id = False
            if picking.group_id:
                sale_id = self.env['sale.order'].search([('procurement_group_id', '=', picking.group_id.id)], limit=1)
                if not sale_id:
                    return_id = self.env['sale.return'].search([('receipt_procurement_group_id', '=', picking.group_id.id)], limit=1)
                    if return_id:
                        sale_id = return_id.sale_order_id
            picking.sale_id = sale_id

    @api.one
    def _get_attachment_number(self):
        rec = self.replacement_return_id or self.receipt_return_id
        ids = self.replacement_return_id.id or self.receipt_return_id.id
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'sale.return'), ('res_id', 'in', [ids])],
            ['res_id'], ['res_id'])
        attach_data = dict((res['res_id'], res['res_id_count']) for res in read_group_res)
        self.attachment_number = attach_data.get(rec.id, 0)

    @api.multi
    def action_get_attachment_tree_view(self):
        attachment_action = self.env.ref('returns_management.action_attachment')
        action = attachment_action.read()[0]
        ids = self.replacement_return_id.id or self.receipt_return_id.id
        action['context'] = {'default_res_model': 'sale.return', 'default_res_id': ids}
        action['domain'] = str(['&', ('res_model', '=', 'sale.return'), ('res_id', 'in', [ids])])
        return action

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()
        if self.receipt_return_id:
            self.receipt_return_id.set_main_state()
        if self.replacement_return_id:
            self.replacement_return_id.set_main_state()
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    receipt_return_line_id = fields.Many2one('sale.return.line', 'Receipt Return')
    replacement_return_line_id = fields.Many2one('sale.return.line', 'Replacement')

    def _get_new_picking_values(self):
        values = super(StockMove, self)._get_new_picking_values()
        if self.receipt_return_line_id:
            values['store_id'] = self.receipt_return_line_id.return_id.store_id.id
            values['receipt_return_id'] = self.receipt_return_line_id.return_id.id
        else:
            replacement_return_line_id = self.procurement_id.replacement_return_line_id
            if replacement_return_line_id:
                values['store_id'] = replacement_return_line_id.return_id.store_id.id
                values['replacement_return_id'] = replacement_return_line_id.return_id.id
        return values

    def _prepare_procurement_from_move(self):
        values = super(StockMove, self)._prepare_procurement_from_move()
        values['receipt_return_line_id'] = self.receipt_return_line_id.id
        values['replacement_return_line_id'] = self.procurement_id.replacement_return_line_id.id
        return values

    def get_cost_values(self, location):
        '''
            When a move comes from a PO, price unit of move is the purchase cost of the move product
            When a move comes from an inventory adjustment, product cost, landed cost and price unit of move
            should just be taken from
              1. Latest 'internal' quant in the same location of the move
              2. Latest 'internal' quant in any location
              3. All zero
        '''
        price_unit = self.price_unit
        total_price_unit = price_unit
        landed_cost = 0
        if not self.receipt_return_line_id:
            if price_unit > 0:
                landed_cost = self.landed_cost
                total_price_unit += landed_cost
            else:
                quant = self.env['stock.quant'].search([('location_id', '=', location.id), ('qty', '>', 0), ('product_id', '=', self.product_id.id)], limit=1)
                if not quant:
                    quant = self.env['stock.quant'].search([('location_id.usage', '=', 'internal'), ('qty', '>', 0), ('product_id', '=', self.product_id.id)], limit=1)
                if quant:
                    price_unit = quant.product_cost
                    landed_cost = quant.landed_cost
                    total_price_unit = price_unit + landed_cost
        return {
            'product_cost': price_unit,
            'cost': total_price_unit,
            'landed_cost': landed_cost,
        }


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[('return', 'Returns')])


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def _quant_update_from_move(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        res = super(StockQuant, self)._quant_update_from_move(move, location_dest_id, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
        vals = {
            'location_id': location_dest_id.id,
            'history_ids': [(4, move.id)],
            'reservation_id': False}
        if move.receipt_return_line_id:
            vals['product_cost'] = move.price_unit
            vals['landed_cost'] = 0
            vals['cost'] = move.price_unit
        if lot_id and any(quant for quant in self if not quant.lot_id.id):
            vals['lot_id'] = lot_id
        if not entire_pack:
            vals.update({'package_id': dest_package_id})
        self.write(vals)
