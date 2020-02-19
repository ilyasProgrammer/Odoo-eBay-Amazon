# -*- coding: utf-8 -*-

import pprint
import time
import csv
from pytz import timezone
import zipfile
from datetime import datetime, timedelta
from cStringIO import StringIO
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
import logging

_logger = logging.getLogger(__name__)
ebay_fees = {'visionary': 0.1051, 'revive': 0.1103, 'rhino': 0.1303, 'ride': 0.0847}
paypal_fee = 0.0215


def dt_to_utc(sdt):
    return timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')


class BusinessCSVReports(http.Controller):

    @http.route('/reports/mapm_buy_box', type='http', auth="user")
    def mapm_buy_box(self, **post):
        store_id = request.env['sale.store'].browse(7)  # Sinister
        wizard_id = request.env['mapm.buy.box.wizard'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['SKU', 'Buy Box']
        writer.writerow([name.encode('utf-8') for name in columns])
        sql = ("""
                    SELECT LISTING.name
                    FROM product_listing LISTING
                    LEFT JOIN product_template TEMPLATE on TEMPLATE.id = LISTING.product_tmpl_id
                    LEFT JOIN sale_store STORE on STORE.id = LISTING.store_id
                    WHERE STORE.site = 'amz' AND LISTING.state = 'active' and LISTING.name like '%MAPM%'
                """)
        cr = request.env.cr
        cr.execute(sql)
        results = cr.dictfetchall()
        chunks = split_on_chunks(results, 20)
        params = {'Action': 'GetCompetitivePricingForSKU', 'MarketplaceId': 'ATVPDKIKX0DER'}
        iteration = 0
        total = len(results)/20
        for ch in chunks:
            _logger.info('Step %s/%s', iteration, total)
            iteration += 1
            counter = 1
            try:
                for b in ch:
                    params['SellerSKUList.SellerSKU.' + str(counter)] = b['name']
                    counter += 1
                now = datetime.now()
                response = store_id.process_amz_request('GET', '/Products/2011-10-01', now, params)
                prices = response['GetCompetitivePricingForSKUResponse']['GetCompetitivePricingForSKUResult']
                if not isinstance(prices, list):
                    prices = [prices]
                for price in prices:
                    got_bb = False
                    if 'Error' in price:
                        continue
                    cps = price['Product']['CompetitivePricing']['CompetitivePrices']
                    if len(cps):
                        if not isinstance(cps, list):
                            cps = [cps]
                        for cp in cps:
                            if cp['CompetitivePrice']['belongsToRequester']['value'] == 'true' and cp['CompetitivePrice']['CompetitivePriceId']['value'] == '1':
                                got_bb = True  # CompetitivePriceId. The pricing model for each price that is returned. Valid values: 1, 2. Value definitions: 1 = New Buy Box Price, 2 = Used Buy Box Price.
                                break
                        row = [
                            price['SellerSKU']['value'],
                            got_bb,
                        ]
                        writer.writerow(row)
                time.sleep(3)
            except Exception as e:
                _logger.error(e)
                _logger.error(response)
                time.sleep(10)
        fp.seek(0)
        data = fp.read()
        valid_fname = 'mapm_buy_box_%s.csv' % datetime.today().strftime('%Y%m%d%H%M')
        file = open('/tmp/'+valid_fname, 'w')
        file.write(data)
        file.close()
        fp.close()
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_demand', type='http', auth="user")
    def sales_demand_report(self, **post):
        wizard_id = request.env['sale.demand.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 00:00:00')
        to_date = dt_to_utc(wizard_id.to_date + ' 23:59:59')

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'Girth', 'Alt Mfg Codes', 'Alt Part Numbers', 'Quantity Sold']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT PT.part_number, PT.partslink, PT.mfg_label, ALT_DETAILS.mfg_codes, ALT_DETAILS.part_numbers,
            (PP.length + (2*PP.width) + (2*PP.height)) as girth,
            CASE WHEN ALT_RES.qty > 0 THEN (ASE_RES.qty + ALT_RES.qty) ELSE ASE_RES.qty END AS qty
            FROM
            (
                SELECT SOL.product_id, SUM(SOL.product_uom_qty) as qty
                FROM sale_order_line SOL
                LEFT JOIN product_product PP on SOL.product_id = PP.id
                WHERE PP.mfg_code = 'ASE' AND SOL.create_date >= %s AND SOL.create_date <= %s
                GROUP BY SOL.product_id
            ) as ASE_RES
            LEFT JOIN
            (
                SELECT ALT.alt_product_id, SUM(SOL.product_uom_qty) as qty
                FROM sale_order_line SOL
                LEFT JOIN product_product_alt_rel ALT on SOL.product_id = ALT.product_id
                LEFT JOIN product_product PP on ALT.product_id = PP.id
                WHERE PP.mfg_code <> 'ASE' AND SOL.create_date >= %s AND SOL.create_date <= %s
                GROUP BY ALT.alt_product_id
            ) as ALT_RES on ALT_RES.alt_product_id = ASE_RES.product_id
            LEFT JOIN
            (
                SELECT ALT.alt_product_id, string_agg(PP.mfg_code, ',') as mfg_codes, string_agg(PP.part_number, ',') as part_numbers
                FROM product_product PP
                LEFT JOIN product_product_alt_rel ALT on ALT.product_id = PP.id
                GROUP BY ALT.alt_product_id
            ) as ALT_DETAILS on ALT_DETAILS.alt_product_id = ASE_RES.product_id
            LEFT JOIN product_product PP on ASE_RES.product_id = PP.id
            LEFT JOIN product_template PT on PP.product_tmpl_id = PT.id
        """)
        params = [from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['part_number'],
                res['partslink'],
                res['mfg_label'],
                res['girth'],
                res['mfg_codes'],
                res['part_numbers'],
                res['qty']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'sales_demand_%s_%s.csv' %(wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/dropship_demand', type='http', auth="user")
    def dropship_demand_report(self, **post):
        wizard_id = request.env['dropship.demand.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 00:00:00')
        to_date = dt_to_utc(wizard_id.to_date + ' 23:59:59')
        dropshipper_code = wizard_id.dropshipper_code

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'Girth', 'Quantity Sold']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT PP2.part_number, PT.partslink, PT.mfg_label, (PP2.length + (2*PP2.width) + (2*PP2.height)) as girth, RES.qty FROM
            (SELECT PP.id, SUM(POL.product_qty) as qty
            FROM purchase_order_line POL
            LEFT JOIN purchase_order PO ON POL.order_id = PO.id
            LEFT JOIN product_product PP on POL.product_id = PP.id
            LEFT JOIN res_partner RP on RP.id = PO.partner_id
            WHERE RP.dropshipper_code = %s AND POL.create_date >= %s AND POL.create_date <= %s AND PO.dest_address_id IS NOT NULL AND PO.state IN ('purchase','done')
            GROUP BY PP.id) as RES
            LEFT JOIN product_product PP2 on RES.id = PP2.id
            LEFT JOIN product_template PT on PP2.product_tmpl_id = PT.id
        """)
        params = [dropshipper_code, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['part_number'],
                res['partslink'],
                res['mfg_label'],
                res['girth'],
                res['qty']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s_dropship_demand_%s_%s.csv' %(dropshipper_code, wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/inventory_ave_costs', type='http', auth="user")
    def inventory_ave_costs(self, **post):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'Quantity', 'Cost']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT TEMPLATE.name, TEMPLATE.partslink, TEMPLATE.mfg_label, RES2.qty, RES1.cost
            FROM (
                SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.qty > 0
                GROUP BY QUANT.product_id
            ) as RES2
            LEFT JOIN
                (SELECT QUANT.product_id, SUM(QUANT.qty) as qty, SUM(QUANT.qty * QUANT.cost) / SUM(QUANT.qty) as cost
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.cost > 0 AND QUANT.qty > 0
                GROUP BY QUANT.product_id
            ) as RES1 on RES1.product_id = RES2.product_id
            LEFT JOIN product_product PRODUCT on PRODUCT.id = RES2.product_id
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
            WHERE TEMPLATE.type = 'product'
        """)
        cr = request.env.cr
        cr.execute(sql)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['name'],
                res['partslink'] if res['partslink'] else '',
                res['mfg_label'] if res['mfg_label'] else '',
                res['qty'],
                "{0:.2f}".format(float(res['cost'])) if res['cost'] else '0.00'
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = 'inventory_ave_costs_%s.csv' %(today)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/unlisted_wh_items', type='http', auth="user")
    def unlisted_wh_items_report(self, **post):
        wizard_id = request.env['sale.unlisted.wh.items.wizard'].browse([int(post.get('id'))])

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'Location', 'Quantity', 'Cost', 'Total']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
           WITH main as (SELECT TEMPLATE.name, TEMPLATE.partslink, TEMPLATE.mfg_label, res2.location, RES2.qty,
                RES1.cost as cost,
               RES2.qty*RES1.cost as Total
            FROM (
                SELECT QUANT.product_id, LOC.id as loc_id,LOC.name as location, SUM(QUANT.qty) as qty
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.qty > 0
                GROUP BY QUANT.product_id, LOC.id
            ) as RES2
            LEFT JOIN
                (SELECT QUANT.product_id, LOC.id as loc_id,LOC.name as location, SUM(QUANT.qty) as qty, SUM(QUANT.qty * QUANT.cost) / SUM(QUANT.qty) as cost
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.cost > 0 AND QUANT.qty > 0
                GROUP BY QUANT.product_id, loc.id
            ) as RES1 on RES1.product_id = RES2.product_id and RES1.loc_id = RES2.loc_id
            LEFT JOIN product_product PRODUCT on PRODUCT.id = RES2.product_id
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
            WHERE TEMPLATE.type = 'product' AND TEMPLATE.part_number IS NOT NULL
            AND NOT EXISTS (
                SELECT product_tmpl_id FROM product_listing PL
                WHERE PL.product_tmpl_id = TEMPLATE.id AND PL.store_id in %s
            )and cost is not NULL
            ORDER BY RES2.qty DESC)
            SELECT main.name, main.partslink, main.mfg_label, string_agg(main.location, ', ') as locations, sum(main.qty) as qty, main.cost, sum(main.Total) as total
            from main
            GROUP BY main.name, main.partslink, main.mfg_label, main.cost
            union all
            select 'TOTAL:', NULL, NULL ,NULL , SUM(main.qty), null,SUM(main.total) from main""")
        cr = request.env.cr
        params = [wizard_id.store_id.id] if wizard_id.store_id else [(1, 3, 4, 5, 7)]
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['name'],
                res['partslink'] if res['partslink'] else '',
                res['mfg_label'] if res['mfg_label'] else '',
                res['locations'],
                res['qty'],
                "{0:.2f}".format(float(res['cost'])) if res['cost'] else '0.00',
                "{0:.2f}".format(float(res['total'])) if res['total'] else '0.00',
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        store_name = wizard_id.store_id.code if wizard_id.store_id else "all"
        valid_fname = '%s_unlisted_wh_items_%s.csv' % (store_name, today)
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/unlisted_wh_items_by_brand', type='http', auth="user")
    def unlisted_wh_items_by_brand_report(self, **post):
        wizard_id = request.env['sale.unlisted.wh.items.by.brand.wizard'].browse([int(post.get('id'))])

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'Quantity', 'Cost']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT TEMPLATE.name, TEMPLATE.partslink, TEMPLATE.mfg_label, RES2.qty, RES1.cost
            FROM (
                SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.qty > 0
                GROUP BY QUANT.product_id
            ) as RES2
            LEFT JOIN
                (SELECT QUANT.product_id, SUM(QUANT.qty) as qty, SUM(QUANT.qty * QUANT.cost) / SUM(QUANT.qty) as cost
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.cost > 0 AND QUANT.qty > 0
                GROUP BY QUANT.product_id
            ) as RES1 on RES1.product_id = RES2.product_id
            LEFT JOIN product_product PRODUCT on PRODUCT.id = RES2.product_id
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
            WHERE TEMPLATE.type = 'product' AND TEMPLATE.part_number IS NOT NULL
            AND NOT EXISTS (
                SELECT product_tmpl_id 
                FROM product_listing PL
                WHERE PL.product_tmpl_id = TEMPLATE.id AND PL.brand = %s
            )
            ORDER BY RES2.qty DESC
        """)
        cr = request.env.cr
        params = [wizard_id.brand]
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['name'],
                res['partslink'] if res['partslink'] else '',
                res['mfg_label'] if res['mfg_label'] else '',
                res['qty'],
                "{0:.2f}".format(float(res['cost'])) if res['cost'] else '0.00'
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = '%s_unlisted_wh_items_%s.csv' % (wizard_id.brand.replace(' ', ''), today)
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/unlisted_wh_kits', type='http', auth="user")
    def unlisted_wh_items_kits_report(self, **post):
        wizard_id = request.env['sale.unlisted.wh.kits.wizard'].browse([int(post.get('id'))])

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Mfg Label', 'Quantity']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT TEMPLATE.name, TEMPLATE.mfg_label, RES2.qty
            FROM (
                SELECT PT.id, MIN(CASE WHEN RES.qty IS NULL THEN 0 ELSE RES.qty END) as qty
                FROM mrp_bom_line BOMLINE
                LEFT JOIN mrp_bom BOM on BOMLINE.bom_id = BOM.id
                LEFT JOIN product_template PT on PT.id = BOM.product_tmpl_id
                LEFT JOIN
                    (SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                    FROM stock_quant QUANT
                    LEFT JOIN product_product PRODUCT on PRODUCT.id = QUANT.product_id
                    LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                    LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
                    WHERE LOC.usage = 'internal' AND QUANT.qty > 0
                    -- AND (TEMPLATE.oversized IS NULL OR TEMPLATE.oversized = False
                    )
                    GROUP BY QUANT.product_id) as RES
                ON RES.product_id = BOMLINE.product_id
                GROUP BY PT.id
                HAVING MIN(CASE WHEN RES.qty IS NULL THEN 0 ELSE RES.qty END) > 0
            ) as RES2
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = RES2.id
            WHERE  TEMPLATE.part_number IS NOT NULL
            AND NOT EXISTS (
                SELECT product_tmpl_id FROM product_listing PL
                WHERE PL.product_tmpl_id = TEMPLATE.id AND PL.store_id = %s
            )
            ORDER BY RES2.qty DESC
        """)

        cr = request.env.cr
        params = [wizard_id.store_id.id]
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['name'],
                res['mfg_label'] if res['mfg_label'] else '',
                res['qty']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = '%s_unlisted_wh_kits_%s.csv' %(wizard_id.store_id.code, today)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/amazon_mapping', type='http', auth="user")
    def amazon_mapping(self, **post):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Amazon SKU', 'LAD SKU']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT LISTING.name, TEMPLATE.part_number, LISTING.title, LISTING.asin, LISTING.upc, LISTING.brand
            FROM product_listing LISTING
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = LISTING.product_tmpl_id
            LEFT JOIN sale_store STORE on STORE.id = LISTING.store_id
            WHERE STORE.site = 'amz' AND LISTING.state = 'active'
        """)
        cr = request.env.cr
        cr.execute(sql)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['name'],
                res['part_number'],
                res['title'].encode('utf-8') if res['title'] else '',
                res['asin'],
                res['upc'],
                res['brand']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        zipped_file = StringIO()
        with zipfile.ZipFile(zipped_file, 'w') as myzip:
            myzip.writestr("amazon_mapping.csv", data)
        zipped_file.seek(0)
        zipped_data = zipped_file.read()
        zipped_file.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = 'amazon_mapping_%s.zip' %(today)
        return request.make_response(zipped_data,
                [('Content-Type', 'application/zip'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/missing_features', type='http', auth="user")
    def missing_features_report(self, **post):
        wizard_id = request.env['sale.missing.features.wizard'].browse([int(post.get('id'))])

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'PFG Alternate', 'LKQ Alternate', 'PPR Alternate']
        writer.writerow([name.encode('utf-8') for name in columns])

        brands_mapping = {
            'lad': "(1)",
            'pfg': "(16, 35, 36, 37, 38,39)",
            'lkq': "(17, 21)",
            'ppr': "(30)",
            'apc': "(42)",
            'mg': "(40)"
        }

        if wizard_id.missing_feature != 'attributes':
            brands_list = brands_mapping['lad']
            if wizard_id.brand:
                brands_list = brands_mapping[wizard_id.brand]
            subquery = ''
            if wizard_id.missing_feature == 'category':
                subquery = """
                    SELECT INV.PartNo FROM Inventory INV
                    LEFT JOIN InventoryPC IPC on IPC.InventoryID = INV.InventoryID
                    LEFT JOIN pc PC on IPC.pcID = PC.pcID
                    LEFT JOIN pcPART PCP on PC.pcPartID = PCP.pcPartID
                    LEFT JOIN pcPosition POS on PC.pcPositionID = POS.pcPositionID
                    GROUP BY INV.PartNo
                    HAVING MAX(PCP.eBayCatID) = 0 OR MAX(PCP.eBayCatID) IS NULL
                """ %brands_list
            elif wizard_id.missing_feature == 'image':
                subquery = """
                    SELECT INV.InventoryID FROM Inventory INV WHERE INV.InventoryID NOT IN (
                        SELECT ASST.InventoryID FROM InventoryPiesASST ASST WHERE ASST.URI IS NOT NULL
                    )
                    AND INV.MfgID IN %s
                """ %brands_list
            elif wizard_id.missing_feature == 'fitment':
                subquery = """
                    SELECT INV.InventoryID FROM Inventory INV WHERE INV.InventoryID NOT IN (
                        SELECT IVEH.InventoryID FROM InventoryVcVehicle IVEH WHERE IVEH.VehicleID IS NOT NULL
                    )
                    AND INV.MfgID IN %s
                """ %brands_list
            query = """
                SELECT MAX(INV.PartNo) as PartNo, MAX(INV.MfgLabel) as MfgLabel,
                (
                    SELECT INTE.PartNo + ',' FROM InventoryPiesINTE INTE
                    WHERE RES.InventoryID = INTE.InventoryID AND INTE.BrandID = 'FLQV'
                    FOR XML PATH('')
                ) as Partslink,
                (
                    SELECT INV2.PartNo + ',' FROM Inventory INV2
                    LEFT JOIN InventoryAlt ALT ON ALT.InventoryIDAlt = INV2.InventoryID
                    WHERE RES.InventoryID = ALT.InventoryID AND INV2.MfgID IN (16, 35, 36, 37, 38, 39)
                    FOR XML PATH('')
                ) as PFGAlternates,
                (
                    SELECT INV2.PartNo + ',' FROM Inventory INV2
                    LEFT JOIN InventoryAlt ALT ON ALT.InventoryIDAlt = INV2.InventoryID
                    WHERE RES.InventoryID = ALT.InventoryID AND INV2.MfgID IN (17, 21)
                    FOR XML PATH('')
                ) as LKQAlternates,
                (
                    SELECT INV2.PartNo + ',' FROM Inventory INV2
                    LEFT JOIN InventoryAlt ALT ON ALT.InventoryIDAlt = INV2.InventoryID
                    WHERE RES.InventoryID = ALT.InventoryID AND INV2.MfgID IN (30)
                    FOR XML PATH('')
                ) as PPRAlternates
                FROM (
                    %s
                ) as RES
                LEFT JOIN Inventory INV on INV.InventoryID = RES.InventoryID
                GROUP BY RES.InventoryID
            """ %subquery

            results = request.env['sale.order'].autoplus_execute(query)
            for res in results:
                columns = ['Part Number', 'Partslink', 'Mfg Label', 'PFG Alternate', 'LKQ Alternate', 'PPR Alternate']
                row = [
                    res['PartNo'],
                    res['Partslink'] if res['Partslink'] else '',
                    res['MfgLabel'] if res['MfgLabel'] else '',
                    res['PFGAlternates'] if res['PFGAlternates'] else '',
                    res['LKQAlternates'] if res['LKQAlternates'] else '',
                    res['PPRAlternates'] if res['PPRAlternates'] else '',
                ]
                writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = 'missing_%s_%s.csv' %(wizard_id.missing_feature, today)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/unsold_wh_items', type='http', auth="user")
    def unsold_wh_items_report(self, **post):
        wizard_id = request.env['sale.unsold.wh.items.wizard'].browse([int(post.get('id'))])
        from_date = (datetime.now() - timedelta(days=wizard_id.days)).strftime('%Y-%m-%d %H:%M:%S')
        store_ids = tuple(wizard_id.store_ids.ids)

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Mfg Label', 'Quantity']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT TEMPLATE.name, TEMPLATE.mfg_label, RES1.qty
            FROM (
                SELECT QUANT.product_id, SUM(QUANT.qty) as qty
                FROM stock_quant QUANT
                LEFT JOIN stock_location LOC on QUANT.location_id = LOC.id
                WHERE LOC.usage = 'internal' AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                GROUP BY QUANT.product_id
            ) as RES1
            LEFT JOIN product_product PRODUCT on PRODUCT.id = RES1.product_id
            LEFT JOIN product_template TEMPLATE on TEMPLATE.id = PRODUCT.product_tmpl_id
            WHERE (
            --TEMPLATE.oversized IS NULL OR TEMPLATE.oversized = False) 
            TEMPLATE.part_number IS NOT NULL
            AND PRODUCT.id not in (
                 SELECT SOL.product_id
                 FROM sale_order_line SOL
                 LEFT JOIN sale_order SO on SO.id = SOL.order_id
                 WHERE SO.store_id IN %s
                 AND SO.create_date >= %s)
            ORDER BY RES1.qty DESC
        """)

        cr = request.env.cr
        params = [store_ids, from_date]
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            row = [
                res['name'],
                res['mfg_label'] if res['mfg_label'] else '',
                res['qty']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = 'unsold_wh_items_%s_%s.csv' %(today, wizard_id.id)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/c2c_competition', type='http', auth="user")
    def c2c_competition_report(self):
        from_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        sql = ("""
            SELECT PT.name, V2M.name as v2m_item_id, V2M.title as v2m_title, 
            V2M.current_price as v2m_price, V2M.qty_sold as v2m_qty_sold, 
            C2C.item_id as c2c_item_id, C2C.title as c2c_title, 
            C2C.price as c2c_price,
            (CASE WHEN DEMAND.qty_sold > 0 THEN DEMAND.qty_sold ELSE 0 END) as c2c_qty_sold
            FROM product_listing V2M
            LEFT JOIN product_template PT ON PT.id = V2M.product_tmpl_id
            LEFT JOIN repricer_competitor C2C ON PT.id = C2C.product_tmpl_id
            LEFT JOIN (
              SELECT HIST.comp_id, SUM(HIST.qty_sold) as qty_sold
              FROM repricer_competitor_history HIST
              WHERE HIST.create_date >= %s
              GROUP BY HIST.comp_id
            ) as DEMAND ON DEMAND.comp_id = C2C.id
            WHERE V2M.custom_label LIKE 'V2F-%%' AND C2C.seller = 'classic2currentfabrication'
            AND C2C.state = 'active' AND V2M.state = 'active'
            ORDER BY (CASE WHEN DEMAND.qty_sold > 0 THEN DEMAND.qty_sold ELSE 0 END) DESC
        """)
        params = [from_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        comp_count = len(results)

        sql_wins = ("""
            SELECT COUNT(*) as count
            FROM product_listing V2M
            LEFT JOIN product_template PT ON PT.id = V2M.product_tmpl_id
            LEFT JOIN repricer_competitor C2C ON PT.id = C2C.product_tmpl_id
            WHERE V2M.custom_label LIKE 'V2F-%' AND C2C.seller = 'classic2currentfabrication'
            AND C2C.state = 'active' AND V2M.state = 'active' AND V2M.current_price < C2C.price
        """)
        cr.execute(sql_wins)
        wins_count_res = cr.dictfetchall()
        wins_count = wins_count_res[0]['count']
        win_percentage = round(wins_count / (comp_count * 1.0), 2)

        writer.writerow(['Wins: %s/%s' % (wins_count, comp_count), '%s' % win_percentage])
        columns = ['Part Number', 'V2M Item ID', 'C2C Item ID', 'V2M Title', 'C2C Title', 'V2M Price', 'C2C Price',
                   'V2M Qty Sold', 'C2C Qty Sold']
        writer.writerow([name.encode('utf-8') for name in columns])
        for res in results:
            row = [
                res['name'],
                res['v2m_item_id'],
                res['c2c_item_id'],
                res['v2m_title'].encode('utf-8') if res['v2m_title'] else '',
                res['c2c_title'].encode('utf-8') if res['c2c_title'] else '',
                res['v2m_price'],
                res['c2c_price'],
                res['v2m_qty_sold'],
                res['c2c_qty_sold']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = 'c2c_competition_%s.csv' % today
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/non_c2c_competition', type='http', auth="user")
    def non_c2c_competition_report(self, **post):
        from_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        sql = ("""
            SELECT PT.name, STORE.code, OUR.name as our_item_id, OUR.title as our_title, 
                   OUR.current_price as our_price, OUR.qty_sold as our_qty_sold,
                   COMP.seller, COMP.item_id as comp_item_id, COMP.title as comp_title, COMP.price as comp_price, 
                   (CASE WHEN DEMAND.qty_sold > 0 THEN DEMAND.qty_sold ELSE 0 END) as comp_qty_sold
            FROM product_listing OUR
            LEFT JOIN sale_store STORE ON STORE.id = OUR.store_id
            LEFT JOIN product_template PT ON PT.id = OUR.product_tmpl_id
            LEFT JOIN (
	            SELECT COMP_SUB_RES.id, COMP_SUB_RES.product_tmpl_id, COMP_SUB_RES.item_id, COMP_SUB_RES.seller, COMP_SUB_RES.title, COMP_SUB_RES.price
                FROM (
		            SELECT COMP.id, COMP.product_tmpl_id, COMP.item_id, COMP.seller, COMP.title, COMP.price,
		            RANK() OVER(PARTITION BY COMP.product_tmpl_id ORDER BY COMP.price) AS rank
	                FROM repricer_competitor COMP
	                WHERE COMP.state = 'active' AND COMP.seller <> 'classic2currentfabrication' AND COMP.price > 0
	            ) AS COMP_SUB_RES WHERE COMP_SUB_RES.rank = 1
            ) AS COMP on COMP.product_tmpl_id = PT.id
            LEFT JOIN (
              SELECT HIST.comp_id, SUM(HIST.qty_sold) as qty_sold
              FROM repricer_competitor_history HIST
              WHERE HIST.create_date >= %s
              GROUP BY HIST.comp_id
            ) as DEMAND ON DEMAND.comp_id = COMP.id
            WHERE OUR.custom_label NOT LIKE 'V2F-%%' AND STORE.site = 'ebay' AND OUR.state = 'active' AND OUR.ebay_reprice_against_competitors = True
            AND COMP.item_id IS NOT NULL
            ORDER BY (CASE WHEN DEMAND.qty_sold > 0 THEN DEMAND.qty_sold ELSE 0 END) DESC
        """)
        params = [from_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        comp_count = len(results)

        sql_wins = ("""
            SELECT COUNT(*)
            FROM product_listing OUR
            LEFT JOIN sale_store STORE ON STORE.id = OUR.store_id
            LEFT JOIN product_template PT ON PT.id = OUR.product_tmpl_id
            LEFT JOIN (
	            SELECT COMP_SUB_RES.product_tmpl_id, COMP_SUB_RES.price
                FROM (
		            SELECT COMP.product_tmpl_id, COMP.price,
		            RANK() OVER(PARTITION BY COMP.product_tmpl_id ORDER BY COMP.price) AS rank
	                FROM repricer_competitor COMP
	                WHERE COMP.state = 'active' AND COMP.seller <> 'classic2currentfabrication' AND COMP.price > 0
	            ) AS COMP_SUB_RES WHERE COMP_SUB_RES.rank = 1
            ) AS COMP on COMP.product_tmpl_id = PT.id
            WHERE OUR.custom_label NOT LIKE 'V2F-%' AND STORE.site = 'ebay' AND OUR.state = 'active' AND OUR.ebay_reprice_against_competitors = True
            AND COMP.price IS NOT NULL AND OUR.current_price < COMP.price
        """)
        cr.execute(sql_wins)
        wins_count_res = cr.dictfetchall()
        wins_count = wins_count_res[0]['count']
        win_percentage = round(wins_count / (comp_count * 1.0), 2)

        writer.writerow(['Wins: %s/%s' % (wins_count, comp_count), '%s' % win_percentage])
        columns = ['Part Number', 'Our Item ID', 'Their Item ID', 'Our Store', 'Their Store',
                   'Our Title', 'Their Title', 'Our Price', 'Their Price',
                   'Our Qty Sold', 'Their Qty Sold']
        writer.writerow([name.encode('utf-8') for name in columns])
        for res in results:
            row = [
                res['name'],
                res['our_item_id'],
                res['comp_item_id'],
                res['code'].title(),
                res['seller'],
                res['our_title'].encode('utf-8') if res['our_title'] else '',
                res['comp_title'].encode('utf-8') if res['comp_title'] else '',
                res['our_price'],
                res['comp_price'],
                res['our_qty_sold'],
                res['comp_qty_sold']
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        today = datetime.today().strftime('%Y-%m-%d')
        valid_fname = 'non_c2c_competition_%s.csv' % today
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/competition_demand', type='http', auth="user")
    def competition_demand_report(self, **post):
        wizard_id = request.env['sale.competition.demand.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 00:00:00')
        to_date = dt_to_utc(wizard_id.to_date + ' 23:59:59')
        group_by = wizard_id.group_by

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        params = [from_date, to_date]
        cr = request.env.cr
        if group_by == 'listing':
            columns = ['Item ID', 'Part Number', 'Seller', 'Demand']
            writer.writerow([name.encode('utf-8') for name in columns])

            sql = ("""
                SELECT MAX(PT.name) as part_number, MAX(COMP.item_id) as item_id, 
                MAX(COMP.seller) as seller, 
                SUM(HIST.qty_sold) as qty_sold
                FROM repricer_competitor COMP
                LEFT JOIN product_template PT ON PT.id = COMP.product_tmpl_id
                LEFT JOIN repricer_competitor_history HIST ON HIST.comp_id = COMP.id
                WHERE HIST.create_date >= %s AND HIST.create_date < %s
                GROUP BY COMP.id
                ORDER BY SUM(HIST.qty_sold) DESC
            """)

            cr.execute(sql, params)
            results = cr.dictfetchall()
            for res in results:
                row = [
                    res['item_id'],
                    res['part_number'],
                    res['seller'],
                    res['qty_sold']
                ]
                writer.writerow(row)
        else:
            columns = ['Part Number', 'Demand']
            writer.writerow([name.encode('utf-8') for name in columns])

            sql = ("""
                SELECT MAX(PT.name) as part_number, SUM(HIST.qty_sold) as qty_sold
                FROM repricer_competitor COMP
                LEFT JOIN product_template PT ON PT.id = COMP.product_tmpl_id
                LEFT JOIN repricer_competitor_history HIST ON HIST.comp_id = COMP.id
                WHERE HIST.create_date >= %s AND HIST.create_date < %s
                GROUP BY PT.id
                ORDER BY SUM(HIST.qty_sold) DESC
            """)

            cr.execute(sql, params)
            results = cr.dictfetchall()
            for res in results:
                row = [
                    res['part_number'],
                    res['qty_sold']
                ]
                writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'competition_demand_%s_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data,
                                     [('Content-Type', 'text/csv'),
                                      ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/ebay_stock', type='http', auth="user")
    def ebay_stock(self, **post):
        wizard_id = request.env['ebay.stock.wizard'].browse([int(post.get('id'))])
        store_id = wizard_id.store_id
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        valid_fname = 'ebay_stock_%s.csv' % store_id.code
        columns = ['LAD', 'WH QTY', 'Listings']
        writer.writerow([name.encode('utf-8') for name in columns])
        qry = """SELECT PT.name lad, sum(coalesce(q.qty, 0))   wh_qty, string_agg(PL.name, ', ') listings
                         FROM product_listing PL
                         LEFT JOIN product_template PT
                         ON PL.product_tmpl_id = PT.id
                         LEFT JOIN (SELECT TEMPLATE.id AS product_tmpl_id, SUM(QUANT.qty) qty
                                           FROM stock_quant QUANT
                                           LEFT JOIN product_product PRODUCT ON PRODUCT.id = QUANT.product_id
                                           LEFT JOIN stock_location LOC ON QUANT.location_id = LOC.id
                                           LEFT JOIN product_template TEMPLATE ON TEMPLATE.id = PRODUCT.product_tmpl_id
                                           WHERE LOC.usage = 'internal' AND LOC.name NOT IN ('Output', 'Amazon FBA')
                                           AND QUANT.reservation_id IS NULL
                                           GROUP BY TEMPLATE.id
                                   ) AS q
                         ON PL.product_tmpl_id = q.product_tmpl_id
                         WHERE PL.store_id = %s AND coalesce(q.qty, 0) > 0
                         GROUP BY PT.name
                         ORDER BY LAD""" % store_id.id
        cr = request.env.cr
        cr.execute(qry)
        results = cr.dictfetchall()
        for r in results:
            writer.writerow([r['lad'], r['wh_qty'], r['listings']])
        fp.seek(0)
        data = fp.read()
        fp.close()
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_fall', type='http', auth="user")
    def sales_fall(self, **post):
        wizard_id = request.env['sales.fall'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Week-1', '']

        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""SELECT SOL.product_id, SUM(SOL.product_uom_qty), date_trunc('day', SO.create_date)::date as day
                FROM sale_order SO
                LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                WHERE SO.create_date >= '2018-07-01' and SO.create_date < '2018-08-01' and product_id=174
                AND SO.state in ('sale','done')
                GROUP BY day, SOL.product_id
                ORDER BY day, product_id""")
        params = [from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        splitted = split_on_chunks(results, 7)
        for group in splitted:
            pass
            row = []
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'sales_fall_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/lossy_dnrl', type='http', auth="user")
    def lossy_dnrl(self, **post):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Listing ID', 'LAD', 'ASIN', 'SKU', 'Min Price', 'Price', 'Diff']

        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""select pl.id,
                           pt.name LAD,
                           pl.asin,
                           pl.name SKU,
                           ROUND((ptl.total_min_cost/0.88)::numeric, 2) as min_price,
                           ROUND(pl.current_price::numeric, 2) as price,
                           ROUND((ptl.total_min_cost/0.88 - pl.current_price)::numeric, 2) as diff
                    from product_listing pl
                    left join product_template_listed ptl on ptl.product_tmpl_id = pl.product_tmpl_id
                    left join product_template as pt on pl.product_tmpl_id = pt.id
                    where pl.state = 'active'
                    and ptl.total_min_cost/0.89 > pl.current_price
                    and pl.name like '%MAPM%'
                    AND (ptl.vendor_qty > 0 OR ptl.wh_qty > 0)
                    order by diff desc""")
        cr = request.env.cr
        cr.execute(sql)
        results = cr.dictfetchall()
        for group in results:
            writer.writerow([group['id'],
                             group['lad'],
                             group['asin'],
                             group['sku'],
                             group['min_price'],
                             group['price'],
                             group['diff']])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'lossy_do_not_repr_mapm.csv'
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])


def list_to_sql_str(data_list):
    qry = ''
    for el in data_list:
        qry += "'" + el + "' ,"
    qry = '(' + qry[:-1] + ")"
    return qry


def split_on_chunks(lst, num):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(lst), num):
        yield lst[i:i + num]