# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import csv

from cStringIO import StringIO
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class Purchase(models.Model):
    _inherit = 'purchase.order'

    has_duplicate = fields.Boolean('Has duplicate', compute='_get_duplicate_lines')
    duplicate_products = fields.Char('Duplicate Products', compute='_get_duplicate_lines')
    vendor_po_bid_file = fields.Binary('Vendor PO Bid File')
    vendor_po_bid_logs = fields.Text('Vendor PO Bid Import Logs')
    vendor_po_bid_filename = fields.Char('Vendor PO Bid File Name', compute='_compute_vendor_po_bid_file_name')
    vendor_po_bid_approved = fields.Boolean('Bid Approved?')
    cu_ft_total = fields.Float(string='Cu. Ft. Total', digits=dp.get_precision('Product Unit of Measure'), store=True, readonly=1, compute='_get_cu_ft_total')

    @api.multi
    def button_save_to_pricelist(self):
        for po in self:
            for line in po.order_line:
                if line.price_unit > 0:
                    line.button_save_to_pricelist()

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        for order in self:
            min_date = False
            for line in order.order_line:
                if not min_date or line.date_planned < min_date:
                    min_date = line.date_planned
            if min_date:
                order.date_planned = min_date
            else:
                order.date_planned = fields.Datetime.now()

    @api.multi
    @api.depends('order_line', 'order_line.product_id')
    def _get_duplicate_lines(self):
        for po in self:
            products = []
            dupes = set()
            for line in po.order_line:
                if line.product_id.name in products:
                    dupes.add(line.product_id.name)
                else:
                    products.append(line.product_id.name)
            if len(dupes) >= 1:
                po.has_duplicate = True
                po.duplicate_products = ', '.join(str(s) for s in dupes)
            else:
                po.has_duplicate = False
                po.duplicate_products = ''

    @api.depends('order_line.cu_ft_subtotal')
    def _get_cu_ft_total(self):
        for order in self:
            order.cu_ft_total = sum(l.cu_ft_subtotal for l in order.order_line)

    @api.multi
    @api.depends('name')
    def _compute_vendor_po_bid_file_name(self):
        for po in self:
            po.vendor_po_bid_filename = (po.name or 'blank') + '-BID.csv'

    @api.multi
    def button_reset_bid(self):
        self.ensure_one()
        for line in self.order_line:
            if self.vendor_po_bid_approved:
                line.write({'price_unit': line.pre_bid_price_unit, 'product_qty': line.pre_bid_product_qty})
                line.write({'pre_bid_price_unit': 0.0, 'pre_bid_product_qty': 0.0})
            line.write({'bid_price_unit': 0.0, 'bid_product_qty': 0.0})
        self.write({'vendor_po_bid_approved': False})

    @api.multi
    def button_approve_bid(self):
        self.ensure_one()
        for line in self.order_line:
            line.write({'pre_bid_price_unit': line.price_unit, 'pre_bid_product_qty': line.product_qty})
            line.write({'price_unit': line.bid_price_unit, 'product_qty': line.bid_product_qty})
        self.write({'vendor_po_bid_approved': True })

    @api.multi
    def button_import_vendor_po_bid(self):
        self.ensure_one()
        if not self.vendor_po_bid_file:
            raise UserError(_('There is nothing to import.'))
        if self.state != 'draft':
            raise UserError(_('Importing can only be done if PO is in RFQ status.'))
        data = csv.reader(StringIO(base64.b64decode(self.vendor_po_bid_file)), quotechar='"', delimiter=',')
        # Read the column names from the first line of the file
        import_fields = data.next()
        required_cols = ['LAD SKU', 'Quantity', 'Unit Price']
        if any(col not in import_fields for col in required_cols):
            raise UserError(_('File should be a comma-separated file with columns named LAD SKU, Quantity, and Unit Price.'))
        rows = []
        for row in data:
            items = dict(zip(import_fields, row))
            rows.append(items)

        if not rows:
            return

        import_logs = ''

        for row in rows:
            product_id = self.env['product.product'].search([('part_number', '=', row['LAD SKU'])])
            if not product_id:
                import_logs += "Product %s not found. Line was not imported.\n" %row['LAD SKU']
            else:
                line = self.order_line.filtered(lambda l: l.bid_product_qty < 1 and l.product_id.id == product_id.id)
                if line:
                    try:
                        line.write({'bid_product_qty': float(row['Quantity']), 'bid_price_unit': float(row['Unit Price'])})
                    except:
                        import_logs += "Product %s has invalid data. Line was not imported.\n" %row['LAD SKU']

                else:
                    import_logs += "Product %s is not found in PO.\n" %row['LAD SKU']

        if import_logs:
            if self.vendor_po_bid_logs:
                import_logs = self.vendor_po_bid_logs + "\n" + import_logs[:-1]
            self.write({'vendor_po_bid_logs': import_logs})

    @api.multi
    def print_quotation(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/rfq?id=%s' % (self.id),
            'target': 'new',
        }

    @api.multi
    def get_rfq_lines(self):
        self.ensure_one()
        data = []
        partner_id = self.partner_id
        if partner_id.parent_id:
            partner_id = partner_id.parent_id

        if partner_id.mfg_codes:
            sql = ("""
                SELECT PP.part_number, PT.mfg_code, PT.partslink, PT.mfg_label, POL.product_qty, POL.price_unit, POL.price_subtotal
                FROM purchase_order_line POL
                LEFT JOIN purchase_order PO ON POL.order_id = PO.id
                LEFT JOIN product_product PP ON PP.id = POL.product_id
                LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                WHERE PO.id = %s
            """)
            params = [self.id]
        else:
            sql = ("""
                SELECT PP.part_number, VC.vendor_code, PT.partslink, PT.mfg_label, POL.product_qty, POL.price_unit, POL.price_subtotal
                FROM purchase_order_line POL
                LEFT JOIN purchase_order PO ON POL.order_id = PO.id
                LEFT JOIN product_product PP ON PP.id = POL.product_id
                LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                LEFT JOIN (
                    SELECT PS.product_tmpl_id, PS.name, MAX(PS.product_code) as vendor_code
                    FROM product_supplierinfo PS
                    GROUP BY PS.product_tmpl_id, PS.name
                ) as VC on VC.product_tmpl_id = PT.id and VC.name = PO.partner_id
                WHERE PO.id = %s
            """)
            params = [self.id]
        cr = self.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['part_number'],
                res['vendor_code'] if 'vendor_code' in res and res['vendor_code'] else '',
                res['partslink'],
                res['mfg_label'],
                res['product_qty'],
                res['price_unit'],
                res['price_subtotal']
            ]
            if 'vendor_code' not in res and res['mfg_code'] and partner_id.mfg_codes:
                if res['mfg_code'] == 'ASE':
                    result = self.env['sale.order'].autoplus_execute("""
                        SELECT TOP 1 INV2.PartNo
                        FROM Inventory INV
                        LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                        LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                        LEFT JOIN InventoryMiscPrCur PR ON INV2.InventoryID = PR.InventoryID
                        LEFT JOIN Mfg MFG on MFG.MfgId = INV2.MfgId
                        WHERE MFG.MfgCode IN (%s) AND INV.PartNo = '%s'
                        ORDER BY PR.Cost ASC
                    """ %(partner_id.mfg_codes, res['part_number']))
                    if result:
                        row[1] = result[0]['PartNo']
                else:
                    row[1] = res['part_number']
            data.append(row)
        return data

    @api.multi
    def create_purchase_attachment(self):
        self.ensure_one()
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['LAD Part Number', 'Vendor Code', 'Partslink', 'Description', 'Qty', 'Unit Price', 'Subtotal']
        writer.writerow([name.encode('utf-8') for name in columns])

        rows = self.get_rfq_lines()

        for row in rows:
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        attachment_id = self.env['ir.attachment'].create({
            'name': self.name,
            'datas_fname': self.name + '.csv',
            'datas': base64.encodestring(data)
        })
        return attachment_id

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
            raise UserError(_('File should be a comma-separated file with columns named Products, Quantity, Unit Price (optional), and Vendor Code (optional).'))
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
                date_planned = datetime.now()
                if self.partner_id.purchase_lead_time:
                    date_planned = datetime.now() + timedelta(days=self.partner_id.purchase_lead_time)
                date_planned = date_planned.strftime('%Y-%m-%d %H:%M:%S')
                values = {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_qty': float(row['Quantity']),
                    'product_uom': product_id.uom_po_id.id,
                    'date_planned': date_planned,
                    'order_id': self.id,
                }

                if 'Unit Price' in row:
                    values['price_unit'] = float(row['Unit Price'])
                elif dropshipper_prices and row['Product'] in dropshipper_prices and dropshipper_prices[row['Product']]:
                    values['price_unit'] = dropshipper_prices[row['Product']]
                else:
                    values['price_unit'] = 1.0

                seller = product_id._select_seller(partner_id=self.partner_id)
                if 'Vendor Code' in row:
                    values['vendor_product_code'] = row['Vendor Code']
                else:
                    if seller:
                        values['vendor_product_code'] = seller[0].product_code

                if 'Cu Ft Per Piece' in row:
                    values['cu_ft_subtotal'] = float(row['Cu Ft Per Piece']) * values['product_qty']
                else:
                    if seller:
                        values['cu_ft_subtotal'] = seller[0].cu_ft * values['product_qty']
                self.env['purchase.order.line'].create(values)
        if import_logs:
            if self.import_logs:
                import_logs = self.import_logs + "\n" + import_logs[:-1]
                print import_logs
            self.write({'import_logs': import_logs})

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bid_price_unit = fields.Float(string='Bid Unit Price', digits=dp.get_precision('Product Price'))
    bid_product_qty = fields.Float(string='Bid Quantity', digits=dp.get_precision('Product Unit of Measure'))
    pre_bid_price_unit = fields.Float(string='Pre-bid Unit Price', digits=dp.get_precision('Product Price'))
    pre_bid_product_qty = fields.Float(string='Pre-bid Quantity', digits=dp.get_precision('Product Unit of Measure'))
    cu_ft_subtotal = fields.Float(string='Cu Ft Subtotal', digits=dp.get_precision('Product Unit of Measure'))
    vendor_product_code = fields.Char('Vendor Product Code')

    earliest_incoming_date = fields.Datetime('Earliest Incoming Date')
    last_incoming_date = fields.Datetime('Latest Incoming Date')
    incoming_total = fields.Float('Incoming Qty Total')
    qty_on_hand = fields.Float('Unreserved Qty on Hand')
    sales_demand_14 = fields.Float('14-Day Demand')
    sales_demand_30 = fields.Float('30-Day Demand')
    cheapest_vendor_id = fields.Many2one('res.partner', 'Cheapest Vendor')
    cheapest_vendor_price = fields.Float('Cheapest Vendor Price')
    cheapest_vendor_lead_time = fields.Integer('Cheapest Vendor Lead Time')
    lowest_price = fields.Float('Lowest Price')
    highest_price = fields.Float('Highest Price')
    average_price = fields.Float('Average Price')
    margin_rate = fields.Float('Margin Rate')
    average_daily_sales = fields.Float('Ave. Daily Sales')
    suggested_purchase_qty = fields.Float('Suggested Purchase Qty')

    @api.multi
    def compute_purchase_info(self):
        for line in self:
            now = datetime.now()
            sdt_now = now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            sdt_14_days_ago = (now - timedelta(days=14)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            sdt_30_days_ago = (now - timedelta(days=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            sql = ("""
                SELECT ASE_RES_30.qty as sales_demand_30, ASE_RES_14.qty as sales_demand_14, ASE_RES_30.sale_date_30, ASE_RES_30.low_price, ASE_RES_30.high_price, (CASE WHEN ASE_RES_30.qty > 0 THEN ASE_RES_30.sum_price_subtotal / ASE_RES_30.qty ELSE 0 END) as ave_price,
                    INCOMING.incoming_total, INCOMING.earliest_incoming_date, INCOMING.last_incoming_date, QUANTS.qty as qty_on_hand, PL_RES.vendor_name, PL_RES.price, PL_RES.vendor_id, PL_RES.purchase_lead_time
                FROM
                (
                    SELECT SOL.product_id, SUM(SOL.product_uom_qty) as qty, MIN(price_unit) as low_price, MAX(price_unit) as high_price, SUM(price_subtotal) as sum_price_subtotal, MIN(SOL.create_date) as sale_date_30
                    FROM sale_order_line SOL
                    LEFT JOIN product_product PP on SOL.product_id = PP.id
                    WHERE SOL.create_date >= %s AND SOL.create_date < %s
                    GROUP BY SOL.product_id
                ) as ASE_RES_30
                LEFT JOIN
                (
                    SELECT SOL.product_id, SUM(SOL.product_uom_qty) as qty
                    FROM sale_order_line SOL
                    LEFT JOIN product_product PP on SOL.product_id = PP.id
                    WHERE SOL.create_date >= %s AND SOL.create_date < %s
                    GROUP BY SOL.product_id
                ) as ASE_RES_14 on ASE_RES_30.product_id = ASE_RES_14.product_id
                LEFT JOIN (
                    SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                    FROM stock_quant QUANT
                    LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                    WHERE LOC.usage = 'internal' AND QUANT.cost > 0 AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                    GROUP BY QUANT.product_id
                ) as QUANTS on QUANTS.product_id = ASE_RES_30.product_id
                LEFT JOIN (
                    SELECT POL.product_id, SUM(POL.product_qty - POL.qty_received) as incoming_total, MIN(POL.date_planned) as earliest_incoming_date, MAX(POL.date_planned) as last_incoming_date
                    FROM purchase_order_line POL
                    LEFT JOIN purchase_order PO on POL.order_id = PO.id
                    WHERE POL.product_qty > POL.qty_received AND POL.state NOT IN ('cancel', 'done')
                    AND PO.dest_address_id IS NULL
                    GROUP BY POL.product_id
                ) AS INCOMING on INCOMING.product_id = ASE_RES_30.product_id
                LEFT JOIN (
                    SELECT PL_SUB_RES.product_id, PL_SUB_RES.vendor_name as vendor_name, PL_SUB_RES.price, PL_SUB_RES.purchase_lead_time, PL_SUB_RES.vendor_id
                    FROM
                        (SELECT PP.id as product_id, PARTNER.id as vendor_id, PARTNER.name as vendor_name, PARTNER.purchase_lead_time, PL.price, RANK() OVER(PARTITION BY PL.product_tmpl_id ORDER BY PL.price) AS rank
                        FROM product_supplierinfo PL
                        LEFT JOIN product_template PT on PL.product_tmpl_id = PT.id
                        LEFT JOIN product_product PP on PP.id = PT.product_variant_id
                        LEFT JOIN res_partner PARTNER on PARTNER.id = PL.name
                        WHERE PL.price > 0
                        ) as PL_SUB_RES WHERE PL_SUB_RES.rank = 1
                ) AS PL_RES on PL_RES.product_id = ASE_RES_30.product_id
                WHERE ASE_RES_30.product_id = %s
            """)
            params = [sdt_30_days_ago, sdt_now, sdt_14_days_ago, sdt_now, line.product_id.id]
            cr = self.env.cr
            cr.execute(sql, params)
            res = cr.dictfetchall()
            if res:
                res = res[0]
                line.earliest_incoming_date = res['earliest_incoming_date'] if res['earliest_incoming_date'] else None
                line.last_incoming_date = res['last_incoming_date'] if res['last_incoming_date'] else None
                line.incoming_total = float(res['incoming_total']) - line.product_qty if res['incoming_total'] else 0.0
                line.sales_demand_14 = float(res['sales_demand_14']) if res['sales_demand_14'] else 0.0
                line.sales_demand_30 = float(res['sales_demand_30']) if res['sales_demand_30'] else 0.0
                line.qty_on_hand = float(res['qty_on_hand']) if res['qty_on_hand'] else 0.0
                line.cheapest_vendor_id = int(res['vendor_id']) if res['vendor_id'] else None
                line.cheapest_vendor_lead_time = int(res['purchase_lead_time']) if res['purchase_lead_time'] else 0.0
                line.cheapest_vendor_price = float(res['price']) if res['price'] else 0.0
                line.lowest_price = float(res['low_price']) if res['low_price'] else 0.0
                line.highest_price = float(res['high_price']) if res['high_price'] else 0.0
                line.average_price = float(res['ave_price']) if res['ave_price'] else 0.0
                line.margin_rate = (100 * (line.average_price - line.price_unit) / line.average_price) if line.average_price > 0 else 0.0

                if line.sales_demand_30 > 0:
                    first_sale_date = res['sale_date_30'][:19] if res['sale_date_30'] else 'NO_SALE'
                    if first_sale_date != 'NO_SALE':
                        first_sale_date = datetime.strptime(first_sale_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        sale_duration = (now - first_sale_date).days + 1
                        line.average_daily_sales = line.sales_demand_30 / sale_duration

                        # Assuming we want to have sufficient stock for 2 times the lead time

                        line.suggested_purchase_qty = max([(line.average_daily_sales * 2 * line.cheapest_vendor_lead_time) - line.incoming_total - line.qty_on_hand, 0])

    @api.model
    def _get_date_planned(self, seller, po=False):
        """
        Overwrite existing method in purchase module
        Use vendor purchase_lead_time instead
        """
        date_planned =datetime.today()
        date_order = po.date_order if po else self.order_id.date_order
        if po and po.partner_id:
            partner_id = po.partner_id
            if partner_id.parent_id:
                partner_id = partner_id.parent_id
            if date_order:
                date_planned = datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=partner_id.purchase_lead_time if partner_id.purchase_lead_time > 0 else 0)
        return date_planned

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return

        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order[:10],
            uom_id=self.product_uom)

        if not seller:
            seller = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id), ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)], limit=1)

        self.date_planned = self._get_date_planned(seller, po=self).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if self.partner_id.mfg_codes:
            print
            if self.product_id.mfg_code == 'ASE':
                mfg_codes = [x.replace("'", "").replace(" ", "") for x in self.partner_id.mfg_codes.split(",")]
                alt_product_ids = self.product_id.alternate_ids.filtered(lambda p: p.mfg_code in mfg_codes)
                if alt_product_ids:
                    self.vendor_product_code = alt_product_ids[0].part_number
            else:
                self.vendor_product_code = self.product_id.part_number

        if not seller:
            return

        price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, self.product_id.supplier_taxes_id, self.taxes_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id.compute(price_unit, self.order_id.currency_id)

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        if seller and not self.partner_id.mfg_codes:
            self.vendor_product_code = seller.product_code

        self.price_unit = price_unit
        self.cu_ft_subtotal = self.product_qty * seller.cu_ft

    @api.multi
    def button_save_to_pricelist(self):
        seller = self.product_id._select_seller(
            partner_id=self.partner_id)
        if not seller:
            seller = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id), ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)], limit=1)
        if seller:
            values = {'price': self.price_unit, 'product_id': self.product_id.id}
            if self.vendor_product_code:
                values['product_code'] = self.vendor_product_code
            if self.cu_ft_subtotal > 0 and self.product_qty > 0:
                values['cu_ft'] = self.cu_ft_subtotal / self.product_qty
            seller.write(values)
        else:
            values = {
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'product_id': self.product_id.id,
                'name': self.partner_id.id,
                'price': self.price_unit,
                'cu_ft': self.cu_ft_subtotal / self.product_qty if self.product_qty > 0 else 0,
                'product_code': self.vendor_product_code
            }
            seller.create(values)
