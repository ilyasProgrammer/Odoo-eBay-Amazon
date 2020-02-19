# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class QuickReceipt(models.Model):
    _name = 'stock.quick.receipt'
    _inherit = ['barcodes.barcode_events_mixin']
    _order = 'id desc'

    name = fields.Char('Reference', required=True, index=True, copy=False, default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed')
        ], string='Status', readonly=True, index=True, copy=False, default='draft')
    pick_id = fields.Many2one('stock.picking', 'Receipt Pick', domain=[('picking_type_code', '=', 'incoming')])
    receipt_line_ids = fields.One2many('stock.quick.receipt.line', 'receipt_id', 'Products', copy=False)
    scanned_code = fields.Char('Scanned Code')
    total_scanned_qty = fields.Integer('Total Scanned Qty', compute='_get_total_scanned_qty')

    @api.multi
    @api.depends('receipt_line_ids.quantity')
    def _get_total_scanned_qty(self):
        for r in self:
            r.total_scanned_qty = sum(l.quantity for l in r.receipt_line_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('stock.quick.receipt') or 'New'
        result = super(QuickReceipt, self).create(vals)
        return result

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        self.scanned_code = barcode
        existing_line_id = self.receipt_line_ids.filtered(lambda l: l.scanned_code == barcode)
        if existing_line_id:
            l = existing_line_id[0]
            l.quantity += 1
        else:
            vals = {
                'scanned_code': barcode,
                'quantity': 1,
                'state': 'draft'
            }
            self.receipt_line_ids += self.receipt_line_ids.new(vals)

    @api.multi
    def button_process(self):
        self.ensure_one()
        if self.pick_id:
            pick_id = self.pick_id
            for line in self.receipt_line_ids:
                _logger.info('Processing quick receipt %s' %line.scanned_code)
                product_id = self.env['product.product'].search(['|', ('barcode', '=', line.scanned_code), ('partslink', '=', line.scanned_code), ('bom_ids', '=', False)], limit=1)
                if not product_id:
                    line.write({'state': 'notfound'})
                    continue
                if product_id.mfg_code != 'ASE':
                    ase_product_id = product_id.inv_alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')
                    if ase_product_id:
                        product_id = ase_product_id[0]
                pack_op_ids = pick_id.pack_operation_product_ids.filtered(lambda p: p.product_id.id == product_id.id)
                if pack_op_ids:
                    pack_op_ids[0].write({'qty_done': pack_op_ids[0].qty_done + line.quantity})
                    line.write({'state': 'matched'})
                else:
                    pick_id.pack_operation_product_ids += pick_id.pack_operation_product_ids.new({
                        'product_id': product_id.id,
                        'product_uom_id': product_id.uom_id.id,
                        'location_id': pick_id.location_id.id,
                        'location_dest_id': pick_id.location_dest_id.id,
                        'qty_done': line.quantity,
                        'product_qty': 0.0,
                        'from_loc': pick_id.location_id.name,
                        'to_loc': pick_id.location_dest_id.name,
                        'fresh_record': False,
                        'state':'assigned'
                    })
                    line.write({'state': 'new'})
            self.write({'state': 'processed'})

    @api.multi
    def button_reset(self):
        self.receipt_line_ids.write({'state': 'draft'})
        self.write({'state': 'draft'})

class QuickReceiptLine(models.Model):
    _name = 'stock.quick.receipt.line'
    _order = 'id desc'

    receipt_id = fields.Many2one('stock.quick.receipt', 'Reference')
    scanned_code = fields.Char('Scanned Code', required=True)
    quantity = fields.Integer('Quantity')
    state = fields.Selection([('draft', 'Draft'), ('matched', 'Matched'), ('new', 'New'), ('notfound', 'Not Found')], 'Status', default='draft', copy=False)
