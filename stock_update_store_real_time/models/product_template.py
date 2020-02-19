# -*- coding: utf-8 -*-

import logging
import ftplib
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

VENDOR_MFG_LABELS = {
    'PPR': {'mfg_labels': "('PPR')", 'less_qty': 5},
    'LKQ': {'mfg_labels': "('BXLD', 'GMK')", 'less_qty': 5},
    'TAW': {'mfg_labels': "('S/B')", 'less_qty': 5},
    'PFG': {'mfg_labels': "('BFHZ', 'REPL', 'STYL', 'NDRE', 'BOLT', 'EVFI')", 'less_qty': 5}
}


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    repricer_scheme_id = fields.Many2one('repricer.scheme', 'Repricer Scheme')
    manual_min_price = fields.Float('Manual Minimum Price', help="Set this to 0 if you do not intend to override computed minimum price.")
    manual_max_price = fields.Float('Manual Maximum Price', help="Set this to 0 if you do not intend to override computed minimum price.")
    auto_min_price = fields.Float('Computed Minimum Price')
    auto_max_price = fields.Float('Compued Maximum Price')
    wh_sale_price = fields.Float('eBay WH Sale Price')
    manual_wh_cost = fields.Float('Manual WH Cost')
    auto_wh_cost = fields.Float('Computed WH Cost')
    auto_wh_shipping_cost = fields.Float('Computed Shipping Cost')
    manual_wh_shipping_cost = fields.Float('Manual Shipping Cost')
    dropship_cost = fields.Float('Dropship Cost')
    competitor_ids = fields.One2many('repricer.competitor', 'product_tmpl_id', 'Competitors')
    use_ebay_repricer = fields.Boolean('Use eBay Repricer')
    always_set_to_zero_qty = fields.Boolean('Always Set Qty to Zero', help="This feature is deprecated. Use 'Do Not Restock' field in listing instead.")

    @api.multi
    def set_qty_to_zero(self):
        self.ebay_update_price_using_vendor_cost(cost=False, qty=0)
        self.amz_update_listing_qty_and_handling_time(qty=0, min_handling_time=False)

    @api.multi
    def get_vendor_cost(self):
        self.ensure_one()
        subquery = ''
        vendor_counter = 1
        for vendor in VENDOR_MFG_LABELS:
            subquery += """
                (SELECT INV2.PartNo as part_number, PR.Cost as cost
                FROM InventoryAlt ALT
                LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryID = INV2.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s AND INV2.PartNo = '%s')

                UNION

                (SELECT INV.PartNo as part_number, PR.Cost as cost
                FROM Inventory INV
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s AND INV.PartNo = '%s')
            """ %(VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'], self.part_number,
                  VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'], self.part_number)

            if vendor_counter < len(VENDOR_MFG_LABELS):
                subquery += 'UNION'
            vendor_counter += 1

        res = self.env['sale.order'].autoplus_execute("""
            SELECT RES.part_number, MIN(RES.cost) as cost FROM
            (
                %s
            ) as RES GROUP BY RES.part_number
        """ %subquery
        )
        return float(res[0]['cost']) if res and res[0]['cost'] else False

    @api.multi
    def get_kit_vendor_cost(self):
        self.ensure_one()
        subquery = ''
        vendor_counter = 1
        for vendor in VENDOR_MFG_LABELS:
            subquery += """
                (SELECT INV2.PartNo as part_number, PR.Cost as cost
                FROM InventoryAlt ALT
                LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryID = INV2.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s)

                UNION

                (SELECT INV.PartNo as part_number, PR.Cost as cost
                FROM Inventory INV
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s)
            """ %(VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'],
                  VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'])
            if vendor_counter < len(VENDOR_MFG_LABELS):
                subquery += 'UNION'
            vendor_counter += 1

        query = """
            SELECT INVKIT.PartNo as part_number,
            (CASE WHEN MIN(CASE WHEN RES2.cost IS NULL THEN 0 ELSE RES2.cost END) = 0 THEN 0 ELSE SUM(RES2.cost) END) as cost
            FROM InventoryPiesKit KIT
            LEFT JOIN Inventory INV on INV.PartNo = KIT.PartNo
            LEFT JOIN Inventory INVKIT on  INVKIT.InventoryID = KIT.InventoryID
            LEFT JOIN (
                SELECT RES.part_number, MIN(RES.cost) as cost FROM
                (
                    %s
                ) as RES GROUP BY RES.part_number
            ) as RES2 ON RES2.part_number = INV.PartNo
            WHERE INVKIT.PartNo = '%s'
            GROUP BY INVKIT.PartNo
        """ %(subquery, self.part_number)

        res = self.env['sale.order'].autoplus_execute(query)
        return float(res[0]['cost']) if res and res[0]['cost'] else False

    @api.multi
    def get_wh_cost(self):
        SHIP_PICK_ID = 4
        create_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

        sql = ("""
            SELECT (CASE WHEN BASE_COST.cost > 0 THEN BASE_COST.cost ELSE 0 END) as wh_cost, BASE_COST.qty, (CASE WHEN SHIPPING.rate > 0 THEN SHIPPING.rate ELSE 0 END) as wh_shipping_cost
            FROM (
                SELECT QUANT.product_id, SUM(QUANT.qty) as qty, SUM(QUANT.qty * QUANT.cost) / SUM(QUANT.qty) as cost
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.cost > 0 AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                GROUP BY QUANT.product_id
            ) as BASE_COST
            LEFT JOIN (
                SELECT MOVE.product_id, (CASE WHEN SUM(MOVE.product_uom_qty) > 0 THEN SUM(PICKING.rate)/SUM(MOVE.product_uom_qty) ELSE 0 END) as rate
                FROM stock_move MOVE
                LEFT JOIN stock_picking PICKING ON PICKING.id = MOVE.picking_id
                WHERE MOVE.create_date >= %s AND PICKING.picking_type_id = %s AND PICKING.state = 'done' AND PICKING.id NOT IN (
                        SELECT PICKING2.id FROM stock_picking PICKING2
                        LEFT JOIN stock_move MOVE2 on MOVE2.picking_id = PICKING2.id
                        GROUP BY PICKING2.id HAVING COUNT(*) > 1
                    )
                GROUP BY MOVE.product_id
            ) as SHIPPING on SHIPPING.product_id = BASE_COST.product_id
            LEFT JOIN product_product PRODUCT on PRODUCT.id = BASE_COST.product_id
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
            WHERE TEMPLATE.part_number = %s
        """)
        params = [create_date, SHIP_PICK_ID, self.part_number]
        cr = self.env.cr
        cr.execute(sql, params)
        wh_cost = cr.dictfetchall()

        total_cost = 0.0
        if wh_cost and wh_cost[0]['qty'] > 1:
            wh_cost = wh_cost[0]
            total_cost += wh_cost['wh_cost']
            if wh_cost['wh_shipping_cost'] > 0:
                total_cost += wh_cost['wh_shipping_cost']
            else:
                pfg_shipping_cost = self.env['sale.order'].autoplus_execute("""
                    SELECT
                    (USAP.ShippingPrice + USAP.HandlingPrice) as ShippingPrice
                    FROM Inventory INV
                    LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                    LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                    LEFT JOIN USAP.dbo.Warehouse USAP ON INV2.PartNo = USAP.PartNo
                    WHERE INV2.MfgID IN (16,35,36,37,38,39) AND USAP.ShippingPrice > 0 AND INV.PartNo = '%s'
                """ %self.part_number)
                if pfg_shipping_cost and pfg_shipping_cost[0]['ShippingPrice'] > 0:
                    total_cost += float(pfg_shipping_cost[0]['ShippingPrice'])
                else:
                    total_cost *= 1.1
        return total_cost

    @api.multi
    def ebay_update_price_using_vendor_cost(self, cost=None, qty=None):
        self.ensure_one()
        updates = []
        rates = {
            'visionary': 1.21,
            'visionary_mg': 1.20,
            'visionary_v2f': 1.19,
            'revive': 1.22,
            'revive_apc': 1.225,
            'rhino': 1.23,
            'ride': 1.24
        }
        ebay_listings = self.listing_ids.filtered(lambda r: r.store_id.site == 'ebay' and r.store_id.enabled and not (r.custom_label and r.custom_label.startswith('X-')))
        for l in ebay_listings:
            if l.max_store_qty:  # If not 0 then use it
                qty = l.max_store_qty
            else:
                qty = min(l.store_id.ebay_max_quantity, qty)
            item_dict = {'ItemID': l.name}
            if not l.do_not_restock:
                item_dict['Quantity'] = qty
            if cost:
                price = rates[l.store_id.code] * cost
                if l.custom_label:
                    if l.custom_label.startswith('APC'):
                        price = rates['revive_apc'] * cost
                    elif l.custom_label.startswith('MG'):
                        price = rates['visionary_mg'] * cost
                    elif l.custom_label.startswith('V2F'):
                        price = rates['visionary_v2f'] * cost
                if l.current_price < price:
                    item_dict['StartPrice'] = price
                    updates.append({
                        'store': l.store_id.code,
                        'item_id': l.name,
                        'qty': qty,
                        'price': price
                    })
            if 'StartPrice' in item_dict or 'Quantity' in item_dict:
                _logger.info('Revising: %s', l.name)
                l.store_id.ebay_execute('ReviseItem', {'Item': item_dict})
        return updates

    @api.multi
    def amz_update_price_using_vendor_cost(self, cost=None, qty=None):
        self.ensure_one()
        updates = []
        amz_listings = self.listing_ids.filtered(lambda r: r.store_id.site == 'amz' and not r.do_not_reprice)
        stores = amz_listings.mapped('store_id')
        for store_id in stores:
            now = datetime.now()
            store_listings = amz_listings.filtered(lambda l: l.store_id.id == store_id.id)
            batches = len(store_listings) / 10
            batch = 0
            res = {}
            repricer_names = {}
            while batch <= batches:
                batch_listings = store_listings[batch * 10: min(len(store_listings), (batch + 1) * 10)]
                if batch_listings:
                    params = {}
                    params['Action'] = 'GetCompetitivePricingForSKU'
                    params['MarketplaceId'] = store_id.amz_marketplace_id
                    counter = 1
                    for b in batch_listings:
                        params['SellerSKUList.SellerSKU.' + str(counter)] = b.name
                        repricer_names[b.name] = b.repricer_scheme_id.name
                        counter += 1
                    response = store_id.process_amz_request('GET', '/Products/2011-10-01', now, params)
                    prices = response['GetCompetitivePricingForSKUResponse']['GetCompetitivePricingForSKUResult']
                    if not isinstance(prices, list):
                        prices = [prices]
                    for price in prices:
                        if 'Product' in price:
                            sku = price['SellerSKU']['value']
                            try:
                                listing_price = price['Product']['CompetitivePricing']['CompetitivePrices']['CompetitivePrice']['Price']['ListingPrice']['Amount']['value']
                                if float(listing_price) <= cost:
                                    res[sku] = listing_price
                            except:
                                res[sku] = 1000
                batch += 1

            if res:
                xml_body = ''
                message_counter = 1
                for sku in res:
                    price = cost * 1.23
                    if sku.startswith('MAPM-PBL'):
                        price = cost * 1.31
                    elif sku.startswith('MAPM'):
                        price = cost * 1.27

                    xml_body += "<Message>"
                    xml_body += "<MessageID>%s</MessageID>" %message_counter
                    xml_body += "<Price>"
                    xml_body += "<SKU>%s</SKU>" %sku
                    xml_body += "<StandardPrice currency='USD'>%s</StandardPrice>" %round(price, 2)
                    xml_body += "</Price>"
                    xml_body += "</Message>"
                    message_counter += 1

                    updates.append({
                        'store': store_id.code,
                        'item_id': sku,
                        'qty': min(qty, 80),
                        'price': price
                    })

                merchant_dentifier = '%s-'% str(self.id) + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                xml = "<?xml version='1.0' encoding='utf-8'?>"
                xml += "<AmazonEnvelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='amzn-envelope.xsd'>"
                xml += "<Header>"
                xml += "<DocumentVersion>1.0</DocumentVersion>"
                xml += "<MerchantIdentifier>%s</MerchantIdentifier>" %merchant_dentifier
                xml += "</Header>"
                xml += "<MessageType>Price</MessageType>"
                xml += xml_body
                xml += "</AmazonEnvelope>"

                _logger.info('Amazon price feed to submit: %s' %xml)

                md5value = store_id.get_md5(xml)

                params = {
                    'ContentMD5Value': md5value,
                    'Action': 'SubmitFeed',
                    'FeedType': '_POST_PRODUCT_PRICING_DATA_',
                    'PurgeAndReplace': 'false'
                }

                response = store_id.process_amz_request('POST', '/Feeds/2009-01-01', now, params, xml)

                file_path = '/var/tmp/repricer.csv'
                with open(file_path, 'wb') as file:
                    file.write("sku,marketplace,merchant_id,price_min,price_max,unit_cost,unit_currency,repricer_name,shipping_cost,shipping_currency,pickpack_cost,pickpack_currency,rrp_price,rrp_currency,vat_rate,fee_listing,fba_fee,fba_currency\n")
                    for sku in res:
                        min_price = 1.147 * cost
                        if sku.startswith('MAPM-PBL'):
                            min_price = cost * 1.31
                        elif sku.startswith('MAPM'):
                            min_price = cost * 1.27
                        min_price = round(min_price, 2)
                        max_price = round(2 * min_price, 2)
                        line = '%s,AUS,A31CNXFNX32WD5,%s,%s,0,USD,%s,0,USD,0,USD,0,USD,0,0,0,USD\n' %(sku, min_price, max_price, repricer_names[sku])
                        file.write('%s' %line)
                ftp = ftplib.FTP("192.169.152.87")
                ftp.login("Repricer", "Th3!TGuy5#$!")
                ftp.storbinary("STOR repricer_%s.csv" %datetime.now().strftime('%Y-%m-%d-%H-%M-%S'), open(file_path, "rb"), 1024)
                ftp.quit()
        return updates

    @api.multi
    def reprice_listings_with_min_cost(self):
        self.ensure_one()
        line = self.env['sale.order.line']
        so_line_id = self.env.context.get('so_line_id', False)
        if so_line_id:
            line = line.browse([so_line_id])
        updates = []
        cost = self.get_min_cost()
        qty, min_handling_time = self.get_qty_for_stores()

        updates += self.ebay_update_price_using_vendor_cost(cost=cost, qty=qty)
        if cost:
            updates += self.amz_update_price_using_vendor_cost(cost=cost, qty=qty)
        if not self.bom_ids:
            self.amz_update_listing_qty_and_handling_time(qty=qty, min_handling_time=min_handling_time)

        bom_line_ids = self.env['mrp.bom.line'].search([('product_id', '=', self.product_variant_id.id )])
        if bom_line_ids:
            bom_ids = bom_line_ids.mapped('bom_id')
            product_tmpl_ids = bom_ids.mapped('product_tmpl_id')
            for p in product_tmpl_ids:
                kit_cost = p.get_min_cost()
                kit_qty, min_handling_time = p.get_qty_for_stores()
                if kit_cost:
                    updates += p.ebay_update_price_using_vendor_cost(cost=kit_cost, qty=kit_qty)
                    updates += p.amz_update_price_using_vendor_cost(cost=kit_cost, qty=kit_qty)
        template = self.env.ref('stock_update_store_real_time.zero_stock_notification')
        template.with_context(
            sku=self.part_number,
            line=line,
            qty=qty,
            cost=cost,
            updates=updates
        ).send_mail(1, force_send=True, raise_exception=True)

    @api.multi
    def get_wh_availability(self):
        self.ensure_one()
        sql = """SELECT RES2.qty
            FROM
                (SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.cost > 0 AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                GROUP BY QUANT.product_id) as RES2
            LEFT JOIN product_product PRODUCT on PRODUCT.id = RES2.product_id
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
            WHERE TEMPLATE.id = %s"""
        params = [self.id]
        cr = self.env.cr
        cr.execute(sql, params)
        res = cr.dictfetchall()
        return res[0]['qty'] if res and res[0]['qty'] else 0

    def get_vendor_availability(self):
        self.ensure_one()
        subquery = ''
        vendor_counter = 1
        for vendor in VENDOR_MFG_LABELS:
            subquery += """
                (SELECT INV2.PartNo as part_number, INV.QtyOnHand as qty
                FROM InventoryAlt ALT
                LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryID = INV2.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s AND INV2.PartNo = '%s')

                UNION

                (SELECT INV.PartNo as part_number, INV.QtyOnHand as qty
                FROM Inventory INV
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s AND INV.PartNo = '%s')
            """ %(VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'], self.part_number,
                  VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'], self.part_number)
            if vendor_counter < len(VENDOR_MFG_LABELS):
                subquery += 'UNION'
            vendor_counter += 1

        res = self.env['sale.order'].autoplus_execute("""
            SELECT RES.part_number, SUM(RES.qty) as qty FROM
            (
                %s
            ) as RES GROUP BY RES.part_number
        """ %subquery
        )
        return float(res[0]['qty']) if res and res[0]['qty'] else 0

    @api.multi
    def get_kit_wh_availability(self):
        self.ensure_one()
        sql = """
            SELECT PT.id, MIN(CASE WHEN RES.qty IS NULL THEN 0 ELSE RES.qty END) as qty
            FROM mrp_bom_line BOMLINE
            LEFT JOIN mrp_bom BOM on BOMLINE.bom_id = BOM.id
            LEFT JOIN product_template PT on PT.id = BOM.product_tmpl_id
            LEFT JOIN
                (SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                FROM stock_quant QUANT
                LEFT JOIN product_product PRODUCT on PRODUCT.id = QUANT.product_id
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.qty > 0
                GROUP BY QUANT.product_id) as RES
            ON RES.product_id = BOMLINE.product_id
            WHERE PT.id = %s
            GROUP BY PT.id
        """
        params = [self.id]
        cr = self.env.cr
        cr.execute(sql, params)
        res = cr.dictfetchall()
        return res[0]['qty'] if res and res[0]['qty'] else 0

    @api.multi
    def get_kit_vendor_availability(self):
        self.ensure_one()
        subquery = ''
        vendor_counter = 1
        for vendor in VENDOR_MFG_LABELS:
            subquery += """
                (SELECT INV2.PartNo as part_number, INV.QtyOnHand as qty
                FROM InventoryAlt ALT
                LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                LEFT JOIN Inventory INV2 on ALT.InventoryID = INV2.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s)

                UNION

                (SELECT INV.PartNo as part_number, INV.QtyOnHand as qty
                FROM Inventory INV
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                LEFT JOIN Mfg MFG on MFG.MfgID = INV.MfgID
                WHERE MFG.MfgCode IN %s AND INV.QtyOnHand > %s)
            """ %(VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'],
                  VENDOR_MFG_LABELS[vendor]['mfg_labels'], VENDOR_MFG_LABELS[vendor]['less_qty'])
            if vendor_counter < len(VENDOR_MFG_LABELS):
                subquery += 'UNION'
            vendor_counter += 1

        res = self.env['sale.order'].autoplus_execute("""
            SELECT INVKIT.PartNo as part_number, MIN(CASE WHEN RES2.qty IS NULL THEN 0 ELSE RES2.qty END) as qty
            FROM InventoryPiesKit KIT
            LEFT JOIN Inventory INV on INV.PartNo = KIT.PartNo
            LEFT JOIN Inventory INVKIT on  INVKIT.InventoryID = KIT.InventoryID
            LEFT JOIN (
                SELECT RES.part_number, SUM(RES.qty) as qty FROM
                (
                    %s
                ) as RES GROUP BY RES.part_number
            ) as RES2 ON RES2.part_number = INV.PartNo
            WHERE INVKIT.PartNo = '%s'
            GROUP BY INVKIT.PartNo
        """ %(subquery, self.part_number))
        return float(res[0]['qty']) if res and res[0]['qty'] else 0

    @api.multi
    def get_qty_for_stores(self):
        self.ensure_one()
        wh_availability = 0
        vendor_availability = 0
        if self.mfg_code == 'ASE' and not self.bom_ids:
            wh_availability = self.get_wh_availability() - 1
            vendor_availability = self.get_vendor_availability()
        elif self.mfg_code == 'ASE' and self.bom_ids:
            wh_availability = self.get_wh_availability()
            if not wh_availability:
                wh_availability = self.get_kit_wh_availability()
                vendor_availability = self.get_kit_vendor_availability()
                if not (wh_availability or vendor_availability):
                    bom_id = self.bom_ids[0]
                    quantities = []
                    for line in bom_id.bom_line_ids:
                        product_tmpl_id = line.product_id.product_tmpl_id
                        wh_availability = product_tmpl_id.get_wh_availability()
                        vendor_availability =  product_tmpl_id.get_vendor_availability()
                        quantities.append(wh_availability + vendor_availability)
                    vendor_availability = min(quantities)
        min_handling_time = bool(wh_availability)
        return int(wh_availability + vendor_availability), min_handling_time

    @api.multi
    def get_wh_availability_for_kits_and_non_kits(self):
        '''
            Note that this returns qty of unreserved quants
            Subtract qty of order line which is yet to be processed by cron to get a better number of unreserved quant
        '''
        self.ensure_one()
        wh_availability = 0
        if self.mfg_code == 'ASE' and not self.bom_ids:
            wh_availability = self.get_wh_availability()
        elif self.mfg_code == 'ASE' and self.bom_ids:
            wh_availability = self.get_wh_availability()
            if not wh_availability:
                wh_availability = self.get_kit_wh_availability()
        return wh_availability

    @api.multi
    def get_min_cost(self):
        if not self.bom_ids:
            wh_cost = self.get_wh_cost()
            vendor_cost =  self.get_vendor_cost()
            if wh_cost or vendor_cost:
                return min(cost for cost in [wh_cost, vendor_cost] if cost > 0)
            else:
                return 0
        elif self.mfg_code == 'ASE' and self.bom_ids:
            bom_id = self.bom_ids[0]
            component_costs = []
            for line_id in bom_id.bom_line_ids:
                product_tmpl_id = line_id.product_id.product_tmpl_id
                component_wh_cost = product_tmpl_id.get_wh_cost()
                component_vendor_cost = product_tmpl_id.get_vendor_cost()
                component_min_cost = 0
                if component_wh_cost or component_vendor_cost:
                    component_min_cost = min(cost for cost in [component_wh_cost, component_vendor_cost] if cost > 0)
                component_costs.append(component_min_cost)
            return sum(component_costs) if all(cost > 0 for cost in component_costs) else 0
        return 0

    @api.multi
    def amz_update_listing_qty_and_handling_time(self, qty=0, min_handling_time=False):
        self.ensure_one()
        amz_listings = self.listing_ids.filtered(lambda r: r.store_id.site == 'amz' and not r.do_not_restock)
        stores = amz_listings.mapped('store_id')
        for store_id in stores:
            now = datetime.now()
            store_listings = amz_listings.filtered(lambda l: l.store_id.id == store_id.id)

            xml_body = ''
            message_counter = 1
            for l in store_listings:
                xml_body += "<Message>"
                xml_body += "<MessageID>%s</MessageID>" %message_counter
                xml_body += "<OperationType>PartialUpdate</OperationType>"
                xml_body += "<Inventory>"
                xml_body += "<SKU>%s</SKU>" %l.name
                xml_body += "<Quantity>%s</Quantity>" %min(qty, 80)
                if not min_handling_time:
                    xml_body += "<FulfillmentLatency>3</FulfillmentLatency>"
                xml_body += "</Inventory>"
                xml_body += "</Message>"
                message_counter += 1

            merchant_dentifier = '%s-'% str(self.id) + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            xml = "<?xml version='1.0' encoding='utf-8'?>"
            xml += "<AmazonEnvelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='amzn-envelope.xsd'>"
            xml += "<Header>"
            xml += "<DocumentVersion>1.0</DocumentVersion>"
            xml += "<MerchantIdentifier>%s</MerchantIdentifier>" %merchant_dentifier
            xml += "</Header>"
            xml += "<MessageType>Inventory</MessageType>"
            xml += "<PurgeAndReplace>false</PurgeAndReplace>"
            xml += xml_body
            xml += "</AmazonEnvelope>"

            _logger.info('Amazon stock feed to submit: %s' %xml)

            md5value = store_id.get_md5(xml)

            params = {
                'ContentMD5Value': md5value,
                'Action': 'SubmitFeed',
                'FeedType': '_POST_INVENTORY_AVAILABILITY_DATA_',
                'PurgeAndReplace': 'false'
            }

            response = store_id.process_amz_request('POST', '/Feeds/2009-01-01', now, params, xml)

    @api.multi
    def restock_listings(self):
        qty, min_handling_time = self.get_qty_for_stores()
        for listing_id in self.listing_ids:
            if listing_id.store_id.site == 'ebay':
                listing_id.update_availability()

    @api.multi
    def button_do_not_restock_all_listings(self):
        for product_tmpl_id in self:
            product_tmpl_id.listing_ids.write({'do_not_restock': True })

    @api.multi
    def button_restock_all_listings(self):
        for product_tmpl_id in self:
            product_tmpl_id.listing_ids.write({'do_not_restock': False })

    @api.multi
    def button_do_not_reprice_all_listings(self):
        for product_tmpl_id in self:
            product_tmpl_id.listing_ids.write({'do_not_reprice': True })

    @api.multi
    def button_reprice_all_listings(self):
        for product_tmpl_id in self:
            product_tmpl_id.listing_ids.write({'do_not_reprice': False })

    @api.model
    def get_cheapest_shipping_rate(self, length, width, height, weight, ship_from_address_id, ship_to_address_id):
        '''
            A more abstract function to get cheapest rate
        '''
        if not (length > 0 and width > 0 and height > 0 and weight > 0):
            raise UserError('A dimension not properly set.')
        ServiceObj = self.env['ship.carrier.service']
        allowed_service_ids = ServiceObj.search([('enabled', '=', True), ('max_weight', '>=', weight), ('max_length', '>=', length), ('max_length_plus_girth', '>=', length + (2 * width) + (2 * height))])
        if not allowed_service_ids:
            raise UserError('Dimensions exceed carrier limits.')
        carrier_ids = allowed_service_ids.mapped('carrier_id').filtered(lambda x: x.enabled)
        first_result = True
        cheapest_rate = 0.0
        cheapest_service_id = ServiceObj
        for c in carrier_ids:
            data = {
                'carrierCode': c.ss_code,
                'packageCode': 'package',
                'fromPostalCode': ship_from_address_id.zip,
                'toPostalCode': ship_to_address_id.zip,
                'toState': ship_to_address_id.state_id.code,
                'toCountry': ship_to_address_id.country_id.code,
                'toCity': ship_to_address_id.city,
                'weight': {
                    'value': weight,
                    'units': 'pounds'
                },
                'dimensions': {
                    'units': 'inches',
                    'length': length,
                    'width': width,
                    'height': height
                },
                'confirmation': 'delivery'
            }
            fedex_carrier = self.env['ship.carrier'].browse(1)
            # residential = fedex_carrier.fedex_validate_address(self, data)
            residential = False
            data['residential'] = residential
            result = self.env['sale.order'].ss_execute_request('POST', '/shipments/getrates', data)
            for rate in result:
                total_rate = rate['shipmentCost'] + rate['otherCost']
                service_id = allowed_service_ids.filtered(lambda x: x.ss_code == rate['serviceCode'])
                if first_result:
                    if service_id:
                        cheapest_rate = total_rate
                        cheapest_service_id = service_id[0]
                        first_result = False
                if not first_result and total_rate < cheapest_rate and service_id:
                    cheapest_rate = total_rate
                    cheapest_service_id = service_id[0]
        if cheapest_service_id:
            return {'rate': cheapest_rate, 'service_id': cheapest_service_id.id, 'package_id': cheapest_service_id.package_id.id, 'exceeds_limits': False}
        else:
            return {'rate': 0.0, 'service_id': False, 'package_id': False, 'exceeds_limits': False}

    @api.multi
    def button_get_shipping_rate(self):
        ParamsObj = self.env['ir.config_parameter']
        param_ship_from_address_id = ParamsObj.get_param('ship_from_address_id')
        param_ship_to_address_id = ParamsObj.get_param('ship_to_address_id')
        if not (param_ship_from_address_id and param_ship_to_address_id):
            raise UserError('Shipping addresses are not properly configured.')

        PartnerObj = self.env['res.partner']
        ship_from_address_id = PartnerObj.browse([int(param_ship_from_address_id)])
        ship_to_address_id = PartnerObj.browse([int(param_ship_to_address_id)])

        for p in self:
            res = self.get_cheapest_shipping_rate(p.length, p.width, p.height, p.weight, ship_from_address_id, ship_to_address_id)
            p.write({'auto_wh_shipping_cost': res['rate']})


class ProductListing(models.Model):
    _inherit = 'product.listing'

    repricer_scheme_id = fields.Many2one('repricer.scheme', 'Repricer Scheme', track_visibility='onchange')
    ebay_reprice_against_competitors = fields.Boolean('Reprice against competitors?', track_visibility='onchange')
    do_not_reprice = fields.Boolean('Do Not Reprice', track_visibility='onchange')
    do_not_restock = fields.Boolean('Do Not Restock', track_visibility='onchange')

    @api.multi
    def ebay_revise_quantity(self, new_qty):
        if self.max_store_qty:
            new_qty = self.max_store_qty
        else:
            new_qty = min(new_qty, self.store_id.ebay_max_quantity)
        try:
            _logger.info('Revising: %s', self.name)
            self.store_id.ebay_execute('ReviseItem', {'Item': {'ItemID': self.name, 'Quantity': new_qty}}).dict()
            _logger.info('Revised qty of %s %s in %s' % (self.product_tmpl_id.part_number, self.name, self.store_id.code))
        except Exception as e:
            _logger.error('Failed to update qty of %s %s in %s %s' % (self.product_tmpl_id.part_number, self.name, self.store_id.code, e))

    @api.multi
    def update_availability(self):
        # Deprecated
        # if self.product_tmpl_id.always_set_to_zero_qty:
        #     return
        for listing in self:
            if listing.store_id.enabled is True and listing.store_id.site == 'ebay' and not listing.do_not_restock and listing.state != 'ended':
                item = listing.store_id.ebay_execute('GetItem', {
                    'ItemID': listing.name
                }).dict()
                if item['Item']['Quantity'] == item['Item']['SellingStatus']['QuantitySold']:
                    new_qty, min_handling_time = listing.product_tmpl_id.get_qty_for_stores()
                    if listing.max_store_qty:
                        listing.ebay_revise_quantity(listing.max_store_qty)
                    else:
                        listing.ebay_revise_quantity(new_qty)
                if listing.min_store_qty:
                    if int(item['Item']['Quantity']) - int(item['Item']['SellingStatus']['QuantitySold']) < listing.min_store_qty:
                        listing.ebay_revise_quantity(listing.max_store_qty)
