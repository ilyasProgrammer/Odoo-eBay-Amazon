# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class QuickReturn(models.Model):
    _name = 'stock.quick.return'
    _inherit = ['barcodes.barcode_events_mixin']

    name = fields.Char('Reference', required=True, index=True, copy=False, default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed')
        ], string='Status', readonly=True, index=True, copy=False, default='draft')
    return_line_ids = fields.One2many('stock.quick.return.line', 'quick_return_id', 'Products', copy=False)
    scanned_code = fields.Char('Scanned Code')
    scanned_location_id = fields.Many2one('stock.location', 'Scanned Location')
    total_scanned_qty = fields.Integer('Total Scanned Qty', compute='_get_total_scanned_qty')

    @api.multi
    @api.depends('return_line_ids.quantity')
    def _get_total_scanned_qty(self):
        for r in self:
            r.total_scanned_qty = sum(l.quantity for l in r.return_line_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('stock.quick.return') or 'New'
        result = super(QuickReturn, self).create(vals)
        return result

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        location_id = self.env['stock.location'].search([('barcode', '=', barcode)])
        if location_id:
            self.scanned_location_id = location_id.id
        else:
            self.scanned_code = barcode
            existing_line_id = self.return_line_ids.filtered(lambda l: l.scanned_code == barcode and l.location_id.id == self.scanned_location_id.id)
            if existing_line_id:
                l = existing_line_id[0]
                l.quantity += 1
            else:
                vals = {
                    'scanned_code': barcode,
                    'location_id': self.scanned_location_id.id,
                    'quantity': 1,
                    'state': 'draft'
                }
                self.return_line_ids += self.return_line_ids.new(vals)

    @api.multi
    def button_process(self):
        self.ensure_one()
        for line in self.return_line_ids:
            _logger.info('Processing quick return %s' %line.scanned_code)

            if line.state == 'matched':
                continue

            product_id = self.env['product.product'].search(['|', ('barcode', '=', line.scanned_code), ('partslink', '=', line.scanned_code), ('bom_ids', '=', False)], limit=1)
            if not product_id:
                line.write({'state': 'notfound'})
                continue
            if product_id.mfg_code != 'ASE':
                ase_product_id = product_id.inv_alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')
                if ase_product_id:
                    product_id = ase_product_id[0]

            if not product_id:
                line.write({'state': 'notfound'})
            # Look for return line that is not yet received. Check if parent return has receipt pickings (if not, create the retun pickings. Validate the return pickings. Validate the internal transfer with the location.)
            return_line_id = self.env['sale.return.line'].search([('product_id', '=', product_id.id), ('qty_received', '=', 0)], limit=1)
            if return_line_id and len(return_line_id.return_id.return_line_ids) == 1 and int(return_line_id.product_uom_qty) == line.quantity:
                pick_ids = return_line_id.return_id.receipt_picking_ids
                if not pick_ids:
                    return_line_id.return_id.receive_return()
                    pick_ids = return_line_id.return_id.receipt_picking_ids
                receipt_pick_id = pick_ids.filtered(lambda p: p.picking_type_id.code  == 'incoming' and p.state == 'assigned')
                if receipt_pick_id:
                    receipt_pick_id = receipt_pick_id[0]
                    receipt_pick_id.action_confirm()
                    for pack in receipt_pick_id.pack_operation_ids:
                        if pack.product_qty > 0:
                            pack.write({'qty_done': pack.product_qty})
                        else:
                            pack.unlink()
                    receipt_pick_id.do_transfer()
                transfer_pick_id = pick_ids.filtered(lambda p: p.picking_type_id.code  == 'internal' and p.state == 'assigned')
                if transfer_pick_id:
                    transfer_pick_id = transfer_pick_id[0]
                    transfer_pick_id.action_confirm()
                    for pack in transfer_pick_id.pack_operation_ids:
                        if pack.product_qty > 0:
                            pack.write({
                                'qty_done': pack.product_qty,
                                'location_dest_id': line.location_id.id,
                                'product_qty': line.quantity,
                                'to_loc': line.location_id.id,
                                'location_processed': True,
                            })
                        else:
                            pack.unlink()
                    transfer_pick_id.do_transfer()
                line.write({'state': 'matched'})
            else:
                line.write({'state': 'notfound'})
            self.write({'state': 'processed'})



            # print pack_op_ids
        #     if pack_op_ids:
        #         if line.quantity < pack_op_ids[0].product_qty:
        #             pack_op_ids[0].write({'product_qty': pack_op_ids[0].product_qty - line.quantity})
        #             pick_id.pack_operation_product_ids += pick_id.pack_operation_product_ids.new({
        #                 'product_id': product_id.id,
        #                 'product_uom_id': product_id.uom_id.id,
        #                 'location_id': pick_id.location_id.id,
        #                 'location_dest_id': line.location_id.id,
        #                 'qty_done': line.quantity,
        #                 'product_qty': line.quantity,
        #                 'from_loc': pick_id.location_id.name,
        #                 'to_loc': line.location_id.id,
        #                 'location_processed': True,
        #                 'state':'assigned'
        #             })
        #         else:
        #             pack_op_ids[0].write({
        #                 'location_processed': True,
        #                 'location_dest_id': line.location_id.id,
        #                 'qty_done': line.quantity,
        #                 'to_loc': line.location_id.id,
        #             })
        #         line.write({'state': 'matched'})
        #     else:
        #         pick_id.pack_operation_product_ids += pick_id.pack_operation_product_ids.new({
        #             'product_id': product_id.id,
        #             'product_uom_id': product_id.uom_id.id,
        #             'location_id': pick_id.location_id.id,
        #             'location_dest_id': line.location_id.id,
        #             'qty_done': line.quantity,
        #             'product_qty': 0.0,
        #             'from_loc': pick_id.location_id.name,
        #             'to_loc': line.location_id.name,
        #             'fresh_record': False,
        #             'state':'assigned'
        #         })
        #         line.write({'state': 'new'})
        # self.write({'state': 'processed'})

    @api.multi
    def button_reset(self):
        self.return_line_ids.write({'state': 'draft'})
        self.write({'state': 'draft'})

class QuickReturnLine(models.Model):
    _name = 'stock.quick.return.line'
    _order = 'id desc'

    quick_return_id = fields.Many2one('stock.quick.return', 'Reference', required=True)
    return_id = fields.Many2one('sale.return', 'Return Reference')
    scanned_code = fields.Char('Scanned Code', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    quantity = fields.Integer('Quantity')
    state = fields.Selection([('draft', 'Draft'), ('matched', 'Matched'), ('notfound', 'Not Found')], 'Status', default='draft', copy=False)
