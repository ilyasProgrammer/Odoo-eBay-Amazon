# -*- coding: utf-8 -*-

import csv
from cStringIO import StringIO
from datetime import datetime, timedelta

from odoo import http, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
import logging
_logger = logging.getLogger(__name__)

ebay_fees = {'visionary': 0.1051, 'revive': 0.1103, 'rhino': 0.1303, 'ride': 0.0847}
paypal_fee = 0.0215


class PurchaseReports(http.Controller):

    @http.route('/reports/rfq', type='http', auth="user")
    def rfq_report(self, **post):
        po_id = request.env['purchase.order'].browse([int(post.get('id'))])

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['LAD Part Number', 'Vendor Code', 'Partslink', 'Description', 'Qty', 'Unit Price', 'Subtotal']
        writer.writerow([name.encode('utf-8') for name in columns])

        rows = po_id.get_rfq_lines()

        for row in rows:
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s.csv' %(po_id.name)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/purchase_qty_suggestions', type='http', auth="user")
    def purchase_qty_suggestions(self, **post):
        now = datetime.now()
        sdt_now = now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        sdt_14_days_ago = (now - timedelta(days=14)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        sdt_30_days_ago = (now - timedelta(days=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # single_orders = self.get_singles_orders(sdt_now)
        sos_for_last_pos = self.get_sos_for_last_pos(sdt_now)
        all_lads_margin = self.get_all_lads_margin(sdt_now)
        last_po_sale_order_ids = [r['so'] for r in sos_for_last_pos]
        # single_orders_ids = [r['id'] for r in single_orders]

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Part Number', 'Partslink', 'Mfg Label', 'Girth', '14-Day Sales', '30-Day Sales', 'Average Daily Sales', 'Suggested Purchase Qty',
                   'Qty On Hand', 'Incoming Total', 'Earliest Incoming Date', 'Last Incoming Date', 'Cheapest Vendor', 'Cost', 'Lead Time',
                   'AVG Margin', 'AVG Profit', 'Win SO/S/P', 'Loss SO/S/P',
                   'DS AVG Margin', 'DS AVG Profit', 'DS Win SO/S/P', 'DS Loss SO/S/P']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT PT.part_number, PT.partslink, PT.mfg_label, 
            (CASE WHEN (ALT_RES.length > 0 AND ALT_RES.width > 0 AND ALT_RES.height > 0) THEN
              (ALT_RES.length + (2*ALT_RES.width) + (2*ALT_RES.height)) ELSE
              (PT.length + (2*PT.width) + (2*PT.height))
            END ) as girth,
            ASE_RES_30.qty as sales_demand_30, ASE_RES_14.qty as sales_demand_14, 
            ASE_RES_30.sale_date_30,
            INCOMING.incoming_total, 
            INCOMING.earliest_incoming_date, 
            INCOMING.last_incoming_date, 
            QUANTS.qty as qty_on_hand, 
            PL_RES.vendor_name,
            PL_RES.price,
            PL_RES.purchase_lead_time
            FROM
            (
                SELECT SOL.product_id, SUM(SOL.product_uom_qty) as qty, MIN(SOL.create_date) as sale_date_30
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
                WHERE LOC.usage = 'internal' AND LOC.name NOT IN ('Output', 'Amazon FBA') AND QUANT.cost > 0 AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                GROUP BY QUANT.product_id
            ) as QUANTS on QUANTS.product_id = ASE_RES_30.product_id
            LEFT JOIN (
                SELECT POL.product_id, SUM(POL.product_qty - POL.qty_received) as incoming_total, MIN(POL.date_planned) as earliest_incoming_date, MAX(POL.date_planned) as last_incoming_date
                FROM purchase_order_line POL
                LEFT JOIN purchase_order PO on POL.order_id = PO.id
                LEFT JOIN stock_picking PICK ON PO.name = PICK.origin
                LEFT JOIN stock_picking_type PICKTYPE on PICKTYPE.id = PICK.picking_type_id
                WHERE POL.product_qty > POL.qty_received AND POL.state NOT IN ('cancel', 'done') AND PICK.state NOT IN ('cancel', 'done')
                AND PICKTYPE.code = 'incoming' AND PO.dest_address_id IS NULL
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
            LEFT JOIN
            (
                SELECT ALT.product_id, PP.length, PP.width, PP.height
                FROM product_product_alt_rel ALT
                LEFT JOIN product_product PP on ALT.alt_product_id = PP.id
                WHERE PP.mfg_code IN ('BFHZ', 'REPL', 'STYL', 'NDRE', 'BOLT', 'EVFI')
            ) as ALT_RES on ALT_RES.product_id = ASE_RES_30.product_id
            LEFT JOIN product_product PP on PP.id = ASE_RES_30.product_id
            LEFT JOIN product_template PT on PT.id = PP.product_tmpl_id
            WHERE PT.part_number IS NOT NULL
        """)
        params = [sdt_30_days_ago, sdt_now, sdt_14_days_ago, sdt_now]
        cr = request.env.cr
        cr.execute(sql, params)
        qry_res = cr.dictfetchall()
        total_rows = len(qry_res)
        cnt = 1
        for res in qry_res:
            _logger.info('%s/%s', cnt, total_rows)
            cnt += 1
            sales_demand_14 = float(res['sales_demand_14']) if res['sales_demand_14'] else 0.0
            sales_demand_30 = float(res['sales_demand_30']) if res['sales_demand_30'] else 0.0
            qty_on_hand = float(res['qty_on_hand']) if res['qty_on_hand'] else 0.0
            incoming_total = float(res['incoming_total']) if res['incoming_total'] else 0.0
            lead_time = int(res['purchase_lead_time']) if res['purchase_lead_time'] else 0.0

            average_daily_sales = 0.0
            suggested_purchase_qty = 0.0

            if sales_demand_30 > 0:
                first_sale_date = res['sale_date_30'][:19] if res['sale_date_30'] else 'NO_SALE'
                if first_sale_date != 'NO_SALE':
                    first_sale_date = datetime.strptime(first_sale_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    sale_duration = (now - first_sale_date).days + 1
                    average_daily_sales = sales_demand_30 / 30

                    # Assuming we want to have sufficient stock for 2 times the lead time

                    suggested_purchase_qty = max([(average_daily_sales * 2 * lead_time) - incoming_total - qty_on_hand, 0])
            margin_data = self.get_margin(res['part_number'], all_lads_margin, last_po_sale_order_ids)
            row = [
                res['part_number'] if res['part_number'] else '',
                res['partslink'] if res['partslink'] else '',
                res['mfg_label'] if res['mfg_label'] else '',
                res['girth'] if res['girth'] else '',
                "{0:.2f}".format(sales_demand_14),
                "{0:.2f}".format(sales_demand_30),
                "{0:.2f}".format(average_daily_sales),
                "{0:.2f}".format(suggested_purchase_qty),
                "{0:.2f}".format(qty_on_hand),
                "{0:.2f}".format(incoming_total),
                res['earliest_incoming_date'] if res['earliest_incoming_date'] else '',
                res['last_incoming_date'] if res['last_incoming_date'] else '',
                res['vendor_name'] if res['vendor_name'] else '',
                "{0:.2f}".format(float(res['price'])) if res['price'] else '',
                lead_time,
                margin_data['wh']['avg_margin'],
                margin_data['wh']['avg_profit_percent'],
                margin_data['wh']['win'],
                margin_data['wh']['loss'],
                margin_data['ds']['avg_margin'],
                margin_data['ds']['avg_profit_percent'],
                margin_data['ds']['win'],
                margin_data['ds']['loss'],
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        valid_fname = 'purchase_qty_suggestions_%s.csv' % (sdt_now[:10])
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @api.model
    def get_margin(self, lad, all_lads_margin, last_po_sale_order_ids):
        total_margin = 0
        total_sale_price = 0
        lad_sales_data = []
        found = False
        res = {'wh': {'avg_margin': 0, 'avg_profit_percent': 0, 'avg_sale_price': 0, 'win': '  ', 'loss': '  ',
                      'qty_of_sales': 0, 'total_sale_price': 0, 'total_margin': 0},
               'ds': {'avg_margin': 0, 'avg_profit_percent': 0, 'avg_sale_price': 0, 'win': '  ', 'loss': '  ',
                      'qty_of_sales': 0, 'total_sale_price': 0, 'total_margin': 0}}
        _logger.info('get_margin LAD: %s', lad)
        filtered_lad_margins = filter(lambda x: lad in x['products'], all_lads_margin)
        for lad_margin in filtered_lad_margins:
            found = True
            win = ''
            loss = ''
            box_cost = lad_margin['box_cost'] if lad_margin['box_cost'] else 0
            so_total = lad_margin['so_total'] if lad_margin['so_total'] else 0
            tax = lad_margin['amount_tax'] if lad_margin['amount_tax'] else 0
            delivery_price = lad_margin['delivery_price'] if lad_margin['delivery_price'] else 0
            computed_dropship_cost = lad_margin['computed_dropship_cost'] if lad_margin['computed_dropship_cost'] else 0
            actual_dropship_cost = lad_margin['actual_dropship_cost'] if lad_margin['actual_dropship_cost'] else 0
            wh_product_cost = lad_margin['wh_product_cost'] if lad_margin['wh_product_cost'] else 0
            computed_wh_shipping_cost = lad_margin['computed_wh_shipping_cost'] if lad_margin['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = lad_margin['actual_pick_shipping_price'] if lad_margin['actual_pick_shipping_price'] else 0
            actual_fee = lad_margin['actual_amz_fee']  # + lad_margin['actual_ebay_fee']
            fee = 0
            if lad_margin['site'] == 'ebay':
                if lad_margin['store'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[lad_margin['store']] + paypal_fee) * so_total
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * so_total
            else:
                if lad_margin['amz_order_type'] == 'fba':
                    if lad_margin.get('fba_commission') and lad_margin.get('fba_fulfillment_fee'):
                        fee = lad_margin['fba_commission'] + lad_margin['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            final_fee = actual_fee if actual_fee else fee
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + final_fee + box_cost + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            margin = so_total - total_cost - tax + delivery_price
            total_margin += margin
            total_sale_price += so_total
            is_ds = True if actual_dropship_cost or computed_dropship_cost else False
            lad_sales_data.append(lad_margin)
            if margin > 0:
                win = '%s/%s/%s, ' % (lad_margin['id'], round(so_total, 2), round(margin, 2))
            else:
                loss = '%s/%s/%s, ' % (lad_margin['id'], round(so_total, 2), round(margin, 2))
            if not is_ds and lad_margin['id'] in last_po_sale_order_ids:
                res['wh']['win'] += win
                res['wh']['loss'] += loss
                res['wh']['total_margin'] += margin
                res['wh']['total_sale_price'] += total_sale_price
                res['wh']['qty_of_sales'] += 1
            elif is_ds:
                res['ds']['win'] += win
                res['ds']['loss'] += loss
                res['ds']['total_margin'] += margin
                res['ds']['total_sale_price'] += total_sale_price
                res['ds']['qty_of_sales'] += 1
        if found:
            try:
                if res['ds']['qty_of_sales']:
                    res['ds']['avg_margin'] = round(res['ds']['total_margin']/res['ds']['qty_of_sales'], 2)
                    res['ds']['avg_sale_price'] = round(res['ds']['total_sale_price']/res['ds']['qty_of_sales'], 2)
                    res['ds']['avg_profit_percent'] = str(round(100*res['ds']['avg_margin']/res['ds']['avg_sale_price'], 2)) + '%'
                    res['ds']['win'] = res['ds']['win'][:-2]
                    res['ds']['loss'] = res['ds']['loss'][:-2]
                if res['wh']['qty_of_sales']:
                    res['wh']['avg_margin'] = round(res['wh']['total_margin']/res['wh']['qty_of_sales'], 2)
                    res['wh']['avg_sale_price'] = round(res['wh']['total_sale_price']/res['wh']['qty_of_sales'], 2)
                    res['wh']['avg_profit_percent'] = str(round(100*res['wh']['avg_margin']/res['wh']['avg_sale_price'], 2)) + '%'
                    res['wh']['win'] = res['wh']['win'][:-2]
                    res['wh']['loss'] = res['wh']['loss'][:-2]
            except Exception as e:
                _logger.error(e)
            return res
        else:
            return res

    @api.model
    def get_singles_orders(self, sdt_now):
        cr = request.env.cr
        single_orders_qry = """SELECT * FROM (SELECT so.id, SUM(sol.product_uom_qty) q
                 FROM sale_order so
                 LEFT JOIN sale_order_line sol on sol.order_id = so.id
                 WHERE so.state in ('sale', 'done') AND so.create_date >= '2018-05-01' AND so.date_order < '%s'
                 GROUP BY so.id) a where q = 1""" % sdt_now
        cr.execute(single_orders_qry)
        single_orders = cr.dictfetchall()
        return single_orders

    @api.model
    def get_sos_for_last_pos(self, sdt_now):
        cr = request.env.cr
        sos_for_last_pos_qry = """
                            select * from (
                            select q.name, q.last_in_move_id in_move, q.po_id, sq.id quant,
                              max(smo.id) out_move,  -- lines with multiple SO will be cut. max will be applied to singles what is fine
                              max(sp.id)  picking,
                              max(so.id) so,
                              string_agg(smo.id :: TEXT, ','),
                              string_agg(sp.id :: TEXT, ','),
                              string_agg(so.id :: TEXT, ','), count(*) cnt
                            FROM (SELECT
                                   pt.name,
                                   max(sm.id)                     last_in_move_id,
                                   string_agg(sm.id :: TEXT, ',') moves_ids,
                                   max(po.id)                     po_id
                                 FROM purchase_order_line pol
                                   LEFT JOIN purchase_order po ON pol.order_id = po.id
                                   LEFT JOIN product_product pp ON pol.product_id = pp.id
                                   LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                                   LEFT JOIN stock_move sm ON pol.id = sm.purchase_line_id
                                 WHERE po.state IN ('purchase', 'done') AND sm.state = 'done' AND sm.location_id = 8
                                 GROUP BY pt.name
                                 ORDER BY pt.name -- 5960
                            ) as q
                            LEFT JOIN stock_quant_move_rel sqm
                                  ON sqm.move_id = q.last_in_move_id
                            LEFT JOIN stock_quant sq on sqm.quant_id = sq.id
                            LEFT JOIN stock_quant_move_rel sqmq -- to connect last out move
                            ON sq.id = sqmq.quant_id
                            LEFT JOIN stock_move smo  -- out moves
                            ON sqmq.move_id = smo.id
                            LEFT JOIN stock_picking sp ON smo.picking_id = sp.id
                            LEFT JOIN sale_order so ON sp.sale_id = so.id
                            WHERE sq.location_id = 9 AND sp.picking_type_id = 4 AND sp.state = 'done' AND smo.location_dest_id = 9 
                            AND so.create_date >= '2018-05-01' AND so.date_order < '%s'
                            GROUP BY q.name, q.last_in_move_id, q.po_id, sq.id) z where cnt = 1  -- exclude quants wih returns in history""" % sdt_now
        cr.execute(sos_for_last_pos_qry)
        sos_for_last_pos = cr.dictfetchall()  # keep some extra data for analysis
        return sos_for_last_pos

    @api.model
    def get_all_lads_margin(self, sdt_now):
        cr = request.env.cr
        qry = """SELECT SO.id,so.date_order, SO.name, SO.ebay_sales_record_number, SO.web_order_id,
                         SO.so_total, SO.amount_tax, SO.delivery_price,
                         SO.fba_commission, SO.fba_fulfillment_fee, SO.store, SO.amz_order_type,
                         SO.products, SO.total_items, SO.site, PO.vendor, SO.computed_dropship_cost,
                         PO.actual_dropship_cost, PICK.computed_wh_shipping_cost, PICK.wh_product_cost,
                         PICK.actual_pick_shipping_price, coalesce(box.box_cost, 0) as box_cost, coalesce(arl.fee, 0) as actual_amz_fee
                   FROM (
                        SELECT SO.id,SO.date_order,SO.ebay_sales_record_number,SO.web_order_id,MAX(SO.amz_order_type) as amz_order_type,
                               MAX(SO.fba_commission) as fba_commission,MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                               MAX(SO.name) as name, MAX(SO.amount_total) as so_total,MAX(SO.amount_tax) as amount_tax,
                               MAX(SO.delivery_price) as delivery_price,string_agg(PP.part_number, ', ') as products,
                               SUM(SOL.product_uom_qty) as total_items,SUM(SOL.dropship_cost) as computed_dropship_cost,
                               MAX(STORE.code) as store, MAX(store.site) as site
                        FROM sale_order SO
                        LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                        LEFT JOIN product_product PP on PP.id = SOL.product_id
                        LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                        WHERE  SO.state in ('sale','done') AND so.create_date >= '2018-05-01' AND so.date_order < '%(sdt_now)s'
                        GROUP BY SO.id, SO.ebay_sales_record_number, SO.web_order_id
                   ) as SO
                   LEFT JOIN (
                        SELECT PO.sale_id, string_agg(PARTNER.name, ', ') as vendor,
                               SUM(RECL.product_price + coalesce(RECL.shipping_price, 0) + coalesce(RECL.handling_price, 0)) as actual_dropship_cost
                        FROM purchase_order PO
                        LEFT JOIN purchase_recon_line RECL on RECL.purchase_order_id = PO.id
                        LEFT JOIN res_partner PARTNER on PO.partner_id = PARTNER.id
                        WHERE PO.state != 'cancel'
                        GROUP BY PO.sale_id
                   ) as PO on PO.sale_id = SO.id
                   LEFT JOIN amazon_recon_line as arl on arl.sale_order_id = SO.id
                   LEFT JOIN (SELECT SO.id,
                              SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                              SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                              SUM(MOVES.product_cost) as wh_product_cost
                              FROM sale_order SO
                              LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                              LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id
                              LEFT JOIN (SELECT PICK.id as pick_id, SUM(MOVE.product_uom_qty * MOVE.price_unit) as product_cost
                                         FROM stock_move as MOVE
                                         LEFT JOIN stock_picking PICK ON PICK.id = MOVE.picking_id
                                         WHERE MOVE.state = 'done'
                                         GROUP BY PICK.id
                                         ) as MOVES on PICK.id = MOVES.pick_id
                              LEFT JOIN (SELECT PICK.id as pick_id, SUM(RECSHIP.shipping_price) as actual_pick_shipping_price
                                         FROM purchase_shipping_recon_line RECSHIP
                                         LEFT JOIN stock_picking PICK ON PICK.id = RECSHIP.pick_id
                                         GROUP BY PICK.id
                                         ) as RECPICK on PICK.id = RECPICK.pick_id
                              LEFT JOIN (SELECT PICK.id as pick_id,
                                                COUNT(*) as count,
                                                SUM(RECSHIPLINES.shipping_price) as actual_tline_shipping_price
                                         FROM stock_picking_tracking_line TLINE
                                         LEFT JOIN (SELECT TLINE.id,
                                                           SUM(RECSHIP.shipping_price) as shipping_price
                                                    FROM purchase_shipping_recon_line RECSHIP
                                                    LEFT JOIN stock_picking_tracking_line TLINE ON TLINE.id = RECSHIP.tracking_line_id
                                                    GROUP BY TLINE.id
                                                  ) as RECSHIPLINES on RECSHIPLINES.id = TLINE.id
                                         LEFT JOIN stock_picking PICK ON PICK.id = TLINE.picking_id
                                         GROUP BY PICK.id
                                         ) as TLINES ON PICK.id = TLINES.pick_id
                              WHERE PICK.state = 'done' AND PICK.picking_type_id IN (4, 11)  -- Delivery Orders	, Amazon FBA to Customer
                              GROUP BY SO.id
                              ) as PICK on PICK.id = SO.id
                   LEFT JOIN (SELECT so.name so_name, sum(boxline.quantity * PRICELIST.price) as box_cost
                              FROM stock_picking PICK
                              LEFT JOIN stock_picking_packaging_line BOXLINE ON BOXLINE.picking_id = PICK.id
                              LEFT JOIN product_product PP ON BOXLINE.packaging_product_id = PP.id
                              LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                              LEFT JOIN product_supplierinfo PRICELIST ON PRICELIST.product_tmpl_id = PT.id
                              LEFT JOIN sale_order so ON so.id = PICK.sale_id
                              WHERE sale_id IN (SELECT id
                                                FROM sale_order so
                                                WHERE SO.state IN ('sale', 'done')
                                                AND so.create_date >= '2018-05-01' AND so.date_order < '%(sdt_now)s')
                              AND BOXLINE.picking_id IS NOT NULL
                              AND PICK.picking_type_id IN (4, 11)
                              AND PICK.state = 'done'
                              GROUP BY so.name
                              ) AS box ON box.so_name = so.name
                      WHERE SO.total_items = 1  -- ONLY singles
                      AND SO.products IS NOT NULL
                      ORDER BY so.date_order""" % {'sdt_now': sdt_now}
                      # ORDER BY so.date_order""" % {'sdt_now': sdt_now, 'sale_order_ids': sale_order_ids}
        cr.execute(qry)
        res = cr.dictfetchall()
        return res


def list_to_sql_str(data_list):
    qry = ''
    for el in data_list:
        qry += "'" + str(el) + "' ,"
    qry = '(' + qry[:-1] + ")"
    return qry


def list_to_sql_int_list(data_list):
    qry = ''
    for el in data_list:
        qry += str(el) + ","
    qry = '(' + qry[:-1] + ")"
    return qry
