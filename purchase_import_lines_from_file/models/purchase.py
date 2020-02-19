# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import csv

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class Purchase(models.Model):
    _inherit = 'purchase.order'

    import_file = fields.Binary('Import File')
    import_logs = fields.Text('Import Logs')
    import_filename = fields.Char('Import File Name', compute='_compute_import_file_name')

    @api.multi
    @api.depends('name')
    def _compute_import_file_name(self):
        for po in self:
            po.import_filename = (po.name or 'blank') + '.csv'

    @api.multi
    def button_import_lines_from_file(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_('There is nothing to import.'))
        if self.state != 'draft':
            raise UserError(_('Importing can only be done if PO is in RFQ status.'))
        data = csv.reader(StringIO(base64.b64decode(self.import_file)), quotechar='"', delimiter=',')
        # Read the column names from the first line of the file
        import_fields = data.next()
        if not('Product' in import_fields or 'Quantity' in import_fields):
            raise UserError(_('File should be a comma-separated file with columns named Products, Quantity, and Unit Price (optional).'))
        rows = []
        for row in data:
            items = dict(zip(import_fields, row))
            rows.append(items)

        if not rows:
            return

        import_logs = ''
        dropshipper_prices = {}
        if self.dropshipper_code in ('pfg', 'lkq'):
            products = '('
            for row in rows:
                products += "'%s', " %row['Product']
            products = products[:-2] + ')'
            mfg_ids = '(17, 21)'
            if self.dropshipper_code == 'pfg':
                mfg_ids = '(16, 35, 36, 37, 38, 39 )'
            query = """
                SELECT INV.PartNo, MIN(PR.Cost) as Cost
                FROM Inventory INV
                LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV2.InventoryID = PR.InventoryID
                WHERE INV2.MfgID IN %s AND INV.PartNo IN %s
                GROUP BY INV.PartNo
            """ %(mfg_ids, products)
            cost_results = self.env['sale.order'].autoplus_execute(query)
            for c in cost_results:
                dropshipper_prices[c['PartNo']] = float(c['Cost']) if c['Cost'] else 0.0

        for row in rows:
            product_id = self.env['product.product'].search([('part_number', '=', row['Product'])])
            if not product_id:
                import_logs += "Product %s not found. Line was not imported.\n" %row['Product']
            else:
                values = {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_qty': float(row['Quantity']),
                    'product_uom': product_id.uom_po_id.id,
                    'date_planned': fields.Datetime.now(),
                    'order_id': self.id,
                }

                if 'Unit Price' in row:
                    values['price_unit'] = float(row['Unit Price'])
                elif dropshipper_prices and row['Product'] in dropshipper_prices and dropshipper_prices[row['Product']]:
                    values['price_unit'] = dropshipper_prices[row['Product']]
                else:
                    values['price_unit'] = 1.0

                self.env['purchase.order.line'].create(values)
        if import_logs:
            if self.import_logs:
                import_logs = self.import_logs + "\n" + import_logs[:-1]
                print import_logs
            self.write({'import_logs': import_logs})
