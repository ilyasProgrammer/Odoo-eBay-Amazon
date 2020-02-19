# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    require_packaging = fields.Boolean('Require Packaging')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    packaging_not_required = fields.Boolean('No Packaging Required', help="Technical field that is checked when user wants to bypass packaging requirement.")
    packaging_line_ids = fields.One2many('stock.picking.packaging.line', 'picking_id', 'Packaging')
    packaging_move_ids = fields.One2many('stock.move', 'packaging_picking_id', 'Packaging Moves')
    pick_src = fields.Many2one('stock.location', string='Source operation location')
    pick_dst = fields.Many2one('stock.location', string='Destination operation location')
    src_complete_name = fields.Char(related='pick_src.complete_name', string='Full Source operation location')
    dst_complete_name = fields.Char(related='pick_dst.complete_name', string='Full Destination operation location')

    @api.multi
    def button_assign_packaging(self):
        if len(self.packaging_line_ids) == 1 and len(self.move_lines) == 1 and float_compare(self.move_lines.product_qty, 1, precision_rounding=0.01) == 0:
            self.move_lines.product_id.product_tmpl_id.write({'packaging_product_id': self.packaging_line_ids.packaging_product_id.id })
        elif len(self.packaging_line_ids) == 0:
            self.move_lines.product_id.product_tmpl_id.write({'no_packaging': True })
        elif len(self.move_ids) > 1:
            raise UserError(_("There is more than one products in this shipment. Please configure product packages in product screen."))
        else:
            raise UserError(_("Please configure product packages in product screen."))

    @api.multi
    def action_assign(self):
        for pick_id in self:
            if pick_id.picking_type_id.require_packaging and len(pick_id.move_lines) == 1 and float_compare(pick_id.move_lines.product_qty, 1, precision_rounding=0.01) == 0:
                if pick_id.move_lines.product_id.product_tmpl_id.no_packaging:
                    pick_id.write({'packaging_not_required': True})
                else:
                    packaging_product_id = pick_id.move_lines.product_id.product_tmpl_id.packaging_product_id
                    if packaging_product_id:
                        self.env['stock.picking.packaging.line'].create({
                            'picking_id': pick_id.id,
                            'quantity': 1,
                            'packaging_product_id': packaging_product_id.id
                        })
        return super(StockPicking, self).action_assign()

    @api.multi
    def do_new_transfer(self):
        self.ensure_one()
        if self.picking_type_id.require_packaging and not self.packaging_not_required and not self.packaging_line_ids:
            view = self.env.ref('stock_packaging.view_packaging_warning_wizard')
            wiz = self.env['stock.packaging.warning.wizard'].create({'pick_id': self.id})
            # TDE FIXME: a return in a loop, what a good idea. Really.
            return {
                'name': _('No Packaging Specified'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.packaging.warning.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        return super(StockPicking, self).do_new_transfer()

    @api.multi
    def do_transfer(self):
        if self.picking_type_id.require_packaging and not self.packaging_not_required and self.packaging_line_ids:
            for line in self.packaging_line_ids:
                move_values = {
                    'name': _('PACK:') + (self.name or ''),
                    'product_id': line.packaging_product_id.id,
                    'product_uom': line.packaging_product_id.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'date': self.date,
                    'company_id': self.company_id.id,
                    'packaging_picking_id': self.id,
                    'state': 'confirmed',
                    'location_id': self.env.ref('stock.stock_location_stock').id,
                    'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                }
                move_id = self.env['stock.move'].create(move_values)
                move_id.action_assign()
                if move_id.state != 'assigned':
                    raise UserError(_("Could not reserve package."))
            self.packaging_move_ids.action_done()
        return super(StockPicking, self).do_transfer()


class PackagingLine(models.Model):
    _name = 'stock.picking.packaging.line'
    _order = 'id desc'

    packaging_product_id = fields.Many2one('product.product', 'Packaging Type', domain=[('is_packaging_product', '=', True)])
    quantity = fields.Integer('Quantity', default=1)
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    packaging_picking_id = fields.Many2one('stock.picking', 'Packaging Picking')
