# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class QuickTransfer(models.Model):
    _name = 'stock.quick.transfer'
    _inherit = ['barcodes.barcode_events_mixin']
    _order = 'id desc'

    name = fields.Char('Reference', required=True, index=True, copy=False, default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed')
        ], string='Status', readonly=True, index=True, copy=False, default='draft')
    pick_id = fields.Many2one('stock.picking', 'Internal Transfer', domain=[('picking_type_code', '=', 'internal')])
    transfer_line_ids = fields.One2many('stock.quick.transfer.line', 'transfer_id', 'Products', copy=False)
    scanned_code = fields.Char('Scanned Code')
    scanned_location_id = fields.Many2one('stock.location', 'Scanned Location')
    total_scanned_qty = fields.Integer('Total Scanned Qty', compute='_get_total_scanned_qty')

    @api.multi
    @api.depends('transfer_line_ids.quantity')
    def _get_total_scanned_qty(self):
        for r in self:
            r.total_scanned_qty = sum(l.quantity for l in r.transfer_line_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('stock.quick.transfer') or 'New'
        result = super(QuickTransfer, self).create(vals)
        return result

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        location_id = self.env['stock.location'].search([('barcode', '=', barcode)])
        if location_id:
            self.scanned_location_id = location_id.id
        else:
            self.scanned_code = barcode
            existing_line_id = self.transfer_line_ids.filtered(lambda l: l.scanned_code == barcode and l.location_id.id == self.scanned_location_id.id)
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
                self.transfer_line_ids += self.transfer_line_ids.new(vals)

    @api.multi
    def button_process(self):
        self.ensure_one()
        if self.pick_id:
            pick_id = self.pick_id
            for line in self.transfer_line_ids:
                _logger.info('Processing quick transfer %s' %line.scanned_code)
                product_id = self.env['product.product'].search(['|', ('barcode', '=', line.scanned_code), ('partslink', '=', line.scanned_code), ('bom_ids', '=', False)], limit=1)
                if not product_id:
                    line.write({'state': 'notfound'})
                    continue
                if product_id.mfg_code != 'ASE':
                    ase_product_id = product_id.inv_alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')
                    if ase_product_id:
                        product_id = ase_product_id[0]

                pack_op_ids = pick_id.pack_operation_product_ids.filtered(lambda p: p.product_id.id == product_id.id and not p.location_processed)
                if pack_op_ids:
                    if line.quantity < pack_op_ids[0].product_qty:
                        pack_op_ids[0].write({'product_qty': pack_op_ids[0].product_qty - line.quantity})
                        pick_id.pack_operation_product_ids += pick_id.pack_operation_product_ids.new({
                            'product_id': product_id.id,
                            'product_uom_id': product_id.uom_id.id,
                            'location_id': pick_id.location_id.id,
                            'location_dest_id': line.location_id.id,
                            'qty_done': line.quantity,
                            'product_qty': line.quantity,
                            'from_loc': pick_id.location_id.name,
                            'to_loc': line.location_id.id,
                            'location_processed': True,
                            'state':'assigned'
                        })
                    else:
                        pack_op_ids[0].write({
                            'location_processed': True,
                            'location_dest_id': line.location_id.id,
                            'qty_done': line.quantity,
                            'to_loc': line.location_id.id,
                        })
                    line.write({'state': 'matched'})
                else:
                    pick_id.pack_operation_product_ids += pick_id.pack_operation_product_ids.new({
                        'product_id': product_id.id,
                        'product_uom_id': product_id.uom_id.id,
                        'location_id': pick_id.location_id.id,
                        'location_dest_id': line.location_id.id,
                        'qty_done': line.quantity,
                        'product_qty': 0.0,
                        'from_loc': pick_id.location_id.name,
                        'to_loc': line.location_id.name,
                        'fresh_record': False,
                        'state':'assigned'
                    })
                    line.write({'state': 'new'})
            self.write({'state': 'processed'})

    @api.multi
    def button_reset(self):
        self.transfer_line_ids.write({'state': 'draft'})
        self.write({'state': 'draft'})

class QuickTransferLine(models.Model):
    _name = 'stock.quick.transfer.line'
    _order = 'id desc'

    transfer_id = fields.Many2one('stock.quick.transfer', 'Reference', required=True)
    scanned_code = fields.Char('Scanned Code', required=True)
    location_id = fields.Many2one('stock.location', 'Location')
    quantity = fields.Integer('Quantity')
    state = fields.Selection([('draft', 'Draft'), ('matched', 'Matched'), ('new', 'New'), ('notfound', 'Not Found')], 'Status', default='draft', copy=False)
