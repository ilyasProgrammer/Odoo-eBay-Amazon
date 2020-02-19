# -*- coding: utf-8 -*-

import base64
import csv
from cStringIO import StringIO
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class ShippingRecon(models.Model):
    _name = 'purchase.shipping.recon'
    _order = 'id desc'

    name = fields.Char('Reference', required=True, copy=False, default='New', readonly=1)
    vendor_reference = fields.Char('Vendor Reference')
    notes = fields.Text('Notes')
    recon_line_ids = fields.One2many('purchase.shipping.recon.line', 'recon_id', string='Invoice Lines')
    import_file = fields.Binary('Import File')
    import_filename = fields.Char('Import File Name', compute='_compute_import_file_name')
    carrier_id = fields.Many2one('ship.carrier', 'Carrier', required=True)
    recon_lines_count = fields.Integer('# of Invoice Lines', compute='_compute_recon_lines_count')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'Status', default='draft')
    total_variance = fields.Float(compute='_compute_total_variance', string='Total Variance', readonly=True, store=True, digits=dp.get_precision('Product Price'))
    total_amt = fields.Float(compute='_compute_total_amt', string='Total Amt', readonly=True, store=True, digits=dp.get_precision('Product Price'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.shipping.recon') or 'New'
        return super(ShippingRecon, self).create(vals)

    @api.multi
    @api.depends('recon_line_ids.variance')
    def _compute_total_variance(self):
        for r in self:
            r.total_variance = sum(l.variance for l in r.recon_line_ids)

    @api.multi
    @api.depends('recon_line_ids.shipping_price')
    def _compute_total_amt(self):
        for r in self:
            r.total_amt = sum(l.shipping_price for l in r.recon_line_ids)

    @api.multi
    @api.depends('recon_line_ids')
    def _compute_recon_lines_count(self):
        for r in self:
            r.recon_lines_count = len(r.recon_line_ids)

    @api.multi
    @api.depends('name')
    def _compute_import_file_name(self):
        for r in self:
            r.import_filename = (r.name or 'New') + '.csv'

    @api.multi
    def action_view_recon_lines(self):
        action = self.env.ref('invoice_recon.action_shipping_recon_line')
        result = action.read()[0]
        result['context'] = {}
        recon_line_ids = sum([r.recon_line_ids.ids for r in self], [])
        result['domain'] = "[('id','in',[" + ','.join(map(str, recon_line_ids)) + "])]"
        return result

    @api.multi
    def button_import_lines_from_file(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_('There is nothing to import.'))
        data = csv.reader(StringIO(base64.b64decode(self.import_file)), quotechar='"', delimiter=',')
        # Read the column names from the first line of the file
        import_fields = data.next()

        required_cols = ['Tracking Number', 'Shipping Price']
        if any(col not in import_fields for col in required_cols):
            raise UserError(_('File should be a comma-separated file with columns named Tracking Number and Shipping Price.'))
        rows = []
        for row in data:
            items = dict(zip(import_fields, row))
            rows.append(items)

        if not rows:
            return

        counter = 1
        for row in rows:
            try:
                values = {
                    'tracking_number': row['Tracking Number'],
                    'recon_id': self.id,
                    'shipping_price': float(row['Shipping Price']),
                }
                self.env['purchase.shipping.recon.line'].create(values)
                counter += 1
            except:
                raise UserError(_('Row %s has invalid data.') %(counter,))

    @api.multi
    def button_reconcile(self):
        self.ensure_one()
        for line in self.recon_line_ids:
            pick_id = self.env['stock.picking'].search([('tracking_number', '=', line.tracking_number)], limit=1)
            if pick_id:
                if pick_id.recon_line_ids:
                    line.write({'state': 'duplicate', 'pick_id': pick_id.id })
                else:
                    line.write({'state': 'matched', 'pick_id': pick_id.id})
            else:
                tracking_line_id = self.env['stock.picking.tracking.line'].search([('name', '=', line.tracking_number)], limit=1)
                if tracking_line_id:
                    if tracking_line_id.recon_line_ids:
                        line.write({'state': 'duplicate', 'tracking_line_id': tracking_line_id.id })
                    else:
                        line.write({'state': 'matched', 'tracking_line_id': tracking_line_id.id})
                else:
                    line.write({'state': 'notfound'})
        self.write({'state': 'done'})

    @api.multi
    def button_undo_recon(self):
        self.ensure_one()
        for line in self.recon_line_ids:
            line.write({'state': 'draft', 'pick_id': False, 'tracking_line_id': False, 'variance': 0.0})
        self.write({'state': 'draft'})

    @api.multi
    def button_download_summary(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/purchase_shipping_recon?id=%s' % self.id,
            'target': 'new',
        }


class ShippingReconLine(models.Model):
    _name = 'purchase.shipping.recon.line'
    _order = 'id desc'
    _rec_name = 'tracking_number'

    tracking_number = fields.Char('Tracking Number')
    recon_id = fields.Many2one('purchase.shipping.recon', 'Recon Reference', required=True)
    shipping_price = fields.Float('Shipping Price', digits=dp.get_precision('Product Price'))
    pick_id = fields.Many2one('stock.picking', 'Shipment Match')
    tracking_line_id = fields.Many2one('stock.picking.tracking.line', 'Tracking Line Match')
    variance = fields.Float(compute='_compute_variance', string='Variance', readonly=True, store=True)
    state = fields.Selection([('draft', 'Draft'), ('matched', 'Matched'), ('duplicate', 'Duplicate'), ('notfound', 'Not Found')], 'Status', default='draft', copy=False)
    carrier_id = fields.Many2one(related='recon_id.carrier_id', string='Carrier')

    @api.multi
    @api.depends('shipping_price', 'pick_id', 'tracking_line_id', 'state')
    def _compute_variance(self):
        for line in self:
            if line.state in ['notfound', 'duplicate']:
                line.variance = -line.shipping_price
            elif line.state == 'matched':
                if line.pick_id:
                    line.variance = line.pick_id.rate - line.shipping_price
                elif line.tracking_line_id:
                    line.variance = line.tracking_line_id.picking_id.rate - line.shipping_price
            else:
                line.variance = 0.0
