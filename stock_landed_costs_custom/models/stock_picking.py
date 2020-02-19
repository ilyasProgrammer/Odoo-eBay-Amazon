# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    freight_po_id = fields.Many2one('purchase.order', 'Purchase Order')
    freight_cost = fields.Float('Freight Cost')
    without_freight_cost = fields.Boolean('Without Freight Cost')

    @api.multi
    def do_new_transfer(self):
        for pick in self:
            if pick.location_id and pick.location_id.usage == 'supplier' and pick.partner_id and not pick.partner_id.is_domestic and not pick.freight_po_id:
                raise UserError("Please specify PO for this international transfer and enter freight cost.")
            warehouse_id = self.env['stock.warehouse'].browse(1)  # Township Fullfillment Center
            if pick.location_id.usage == 'supplier' and pick.picking_type_id == warehouse_id.in_type_id and pick.freight_po_id and not pick.freight_po_id.is_domestic and pick.freight_cost <= 0:
                raise UserError("Please enter freight cost as this is international receipt.")
                pass
            if pick.location_id.usage == 'supplier' and pick.picking_type_id == warehouse_id.in_type_id \
                    and pick.freight_po_id and pick.freight_po_id.is_domestic and pick.freight_cost <= 0 and not pick.without_freight_cost:
                raise UserError("""You did not entered freight cost for this Domestic receipt. 
                                   To proceed without freight cost tick Without Freight Cost checkbox. 
                                   Otherwise enter freight cost.""")
                pass
        return super(StockPicking, self).do_new_transfer()

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()
        if self.freight_po_id and self.picking_type_id.code in ['internal', 'incoming'] and self.freight_cost > 0 and self.partner_id.is_domestic:  # DOMESTIC freight distr
            total_length = sum(move_id.product_qty * move_id.product_id.length for move_id in self.move_lines)
            for move_id in self.move_lines:
                if move_id.product_qty > 0:
                    landed_cost = self.freight_cost * move_id.purchase_line_id.price_unit / self.purchase_id.amount_total  # Freight cost for 1 quant
                    move_id.write({'landed_cost': landed_cost})
                for quant_id in move_id.quant_ids:
                    quant_id.write({
                        'product_cost': move_id.price_unit,
                        'landed_cost': move_id.landed_cost,
                        'cost': move_id.price_unit + move_id.landed_cost
                    })
        elif self.freight_po_id and self.picking_type_id.code in ['internal', 'incoming'] and self.freight_cost > 0:
            for move_id in self.move_lines:
                pl = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', move_id.product_id.product_tmpl_id.id),('name', '=', self.freight_po_id.partner_id.id), ('cu_ft', '>', 0)], limit=1)
                if not pl:
                    raise UserError(_('No cu ft assigned to %s.') % (move_id.product_id.name, ))
                move_id.write({'cu_ft': pl.cu_ft})

            total_cu_ft = sum(move_id.product_qty * move_id.cu_ft for move_id in self.move_lines)

            for move_id in self.move_lines:
                if move_id.product_qty > 0:
                    landed_cost =self.freight_cost * move_id.cu_ft / total_cu_ft
                    move_id.write({'landed_cost': landed_cost})
                for quant_id in move_id.quant_ids:
                    quant_id.write({
                        'product_cost': move_id.price_unit,
                        'landed_cost': move_id.landed_cost,
                        'cost': move_id.price_unit + move_id.landed_cost
                    })
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    freight_po_id = fields.Many2one('purchase.order', 'Purchase Order')
    landed_cost = fields.Float('Landed Cost')
    cu_ft = fields.Float('Cu. Ft.')

    def _get_new_picking_values(self):
        values = super(StockMove, self)._get_new_picking_values()
        if self.freight_po_id:
            values['freight_po_id'] = self.freight_po_id.id
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
