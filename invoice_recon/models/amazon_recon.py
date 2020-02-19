# -*- coding: utf-8 -*-

import base64
import csv
from cStringIO import StringIO
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class AmazonRecon(models.Model):
    _name = 'amazon.recon'
    _order = 'id desc'

    name = fields.Char('Reference', required=True, copy=False, default='New', readonly=1)
    vendor_reference = fields.Char('Amazon Reference')
    notes = fields.Text('Notes')
    recon_line_ids = fields.One2many('amazon.recon.line', 'recon_id', string='Invoice Lines')
    import_file = fields.Binary('Import File')
    import_filename = fields.Char('Import File Name', compute='_compute_import_file_name')
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)  # Amazon
    recon_lines_count = fields.Integer('# of Invoice Lines', compute='_compute_recon_lines_count')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'Status', default='draft')
    total_variance = fields.Float(compute='_compute_total_variance', string='Total Variance', readonly=True, store=True, digits=dp.get_precision('Product Price'))
    total_amt = fields.Float(compute='_compute_total_amt', string='Total Amt', readonly=True, store=True, digits=dp.get_precision('Product Price'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('amazon.recon') or 'New'
        return super(AmazonRecon, self).create(vals)

    @api.multi
    @api.depends('recon_line_ids.variance')
    def _compute_total_variance(self):
        for r in self:
            r.total_variance = sum(l.variance for l in r.recon_line_ids)

    @api.multi
    @api.depends('recon_line_ids')
    def _compute_total_amt(self):
        for r in self:
            r.total_amt = sum(l.price for l in r.recon_line_ids)

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
        action = self.env.ref('invoice_recon.action_amazon_recon_line')
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
        data = csv.reader(StringIO(base64.b64decode(self.import_file)), quotechar='"', delimiter='\t')
        # Read the column names from the first line of the file
        import_fields = data.next()

        required_cols = ['Store', 'Web ID', 'Sale Price', 'Amazon Fees']
        if any(col not in import_fields for col in required_cols):
            raise UserError(_('File should be a tab-separated file with columns named Store, Web ID, Sale Price, Amazon Fees'))
        rows = []
        for row in data:
            items = dict(zip(import_fields, row))
            rows.append(items)

        if not rows:
            return

        counter = 1
        store_id = self.env['sale.store'].search([('code', '=', 'sinister')])
        for row in rows:
            try:
                values = {
                    'name': row['Web ID'].strip(),
                    'recon_id': self.id,
                    'price': float(row['Sale Price'].replace(',', '.')),
                    'fee': float(row['Amazon Fees'].replace(',', '.')),
                    'store_id': store_id.id,
                    'partner_id': self.partner_id.id
                }
                self.env['amazon.recon.line'].create(values)
                counter += 1
            except Exception as e:
                raise UserError('Row %s has invalid data. %s' % (counter, e))

    @api.multi
    def button_reconcile(self):
        self.ensure_one()
        store_id = self.env['sale.store'].search([('code', '=', 'sinister')])
        for line in self.recon_line_ids:
            state = 'draft'
            variance = 0.0
            fee_variance = 0.0
            so_id = self.env['sale.order'].search([('store_id', '=', store_id.id),
                                                   ('web_order_id', '=', line.name),
                                                   ('state', 'in', ('sale', 'done'))], limit=1)
            if so_id:
                if so_id.amazon_recon_line_ids:
                    state = 'duplicate'
                    # line.write({'state': 'duplicate', 'sale_order_id': po_id.id })
                else:
                    state = 'matched'
                    # line.write({'state': 'matched', 'sale_order_id': po_id.id})
            else:
                state = 'notfound'

            if state in ['notfound', 'duplicate']:
                variance = -line.price
                fee_variance = -line.fee
            elif state == 'matched':
                variance = so_id.amount_total - line.price
                if so_id.amz_order_type == 'fba':
                    if so_id.fba_commission and so_id.fba_fulfillment_fee:
                        amz_calc_fee = so_id.fba_commission + so_id.fba_fulfillment_fee
                else:
                    amz_calc_fee = max(1.00, 0.12 * so_id.amount_total)
                fee_variance = amz_calc_fee - line.fee
            else:
                variance = 0.0
                fee_variance = 0.0
            line.write({'state': state,
                        'sale_order_id': so_id.id,
                        'fee_variance': fee_variance,
                        'variance': variance})
        self.write({'state': 'done'})

    @api.multi
    def button_undo_recon(self):
        self.ensure_one()
        for line in self.recon_line_ids:
            line.write({'state': 'draft', 'sale_order_id': False})
        self.write({'state': 'draft'})

    @api.multi
    def button_unlink_recon_lines(self):
        self.ensure_one()
        self.recon_line_ids.unlink()

    @api.multi
    def button_download_summary(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/amazon_recon?id=%s' % (self.id),
            'target': 'new',
        }


class PurchaseReconLine(models.Model):
    _name = 'amazon.recon.line'
    _order = 'name'

    name = fields.Char('Reference', required=True)
    vendor_ref = fields.Char('Vendor Reference')
    recon_id = fields.Many2one('amazon.recon', 'Recon Reference', required=True)
    price = fields.Float('Item Price', digits=dp.get_precision('Product Price'))
    fee = fields.Float('Amazon Fee', digits=dp.get_precision('Product Price'))
    sale_order_id = fields.Many2one('sale.order', 'SO Match')
    variance = fields.Float(string='Variance')
    fee_variance = fields.Float(string='Fee Variance')
    state = fields.Selection([('draft', 'Draft'), ('matched', 'Matched'), ('duplicate', 'Duplicate'), ('notfound', 'Not Found')], 'Status', default='draft', copy=False)
    partner_id = fields.Many2one(related='recon_id.partner_id', string='Partner')
    store_id = fields.Many2one('sale.store', string='Store')
    note = fields.Char('Note')
