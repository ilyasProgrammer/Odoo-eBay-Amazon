# -*- coding: utf-8 -*-

import csv
from pytz import timezone
from odoo.exceptions import UserError
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


class MarginReports(http.Controller):

    @http.route('/reports/dropship_margin', type='http', auth="user")
    def dropship_margin_report(self, **post):
        wizard_id = request.env['sale.dropship.margin.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') +timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Store','SO Number','Part Number','Dropship Cost','Sale Price','Margin']
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""
            SELECT SO.name as SO, STORE.code as store, STORE.site, 
            SO.amz_order_type,
            SO.fba_commission, 
            SO.fba_fulfillment_fee,
            PT.name as Product, SOL.product_uom_qty, 
            SOL.dropship_cost, SOL.price_unit
            FROM sale_order_line SOL
            LEFT JOIN sale_order SO on SOL.order_id = SO.id
            LEFT JOIN sale_store STORE on SO.store_id = STORE.id
            LEFT JOIN product_product PP on SOL.product_id = PP.id
            LEFT JOIN product_template PT on PP.product_tmpl_id = PT.id
            WHERE SOL.dropship_cost > 0 and SOL.price_unit > 0 AND SO.date_order >= %s AND SO.date_order < %s
            AND SO.state = 'sale'
        """)
        params = [from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            dropship_cost = float(res['product_uom_qty']) * float(res['dropship_cost'])
            sale_price = float(res['product_uom_qty']) * float(res['price_unit'])
            fee = 0
            if res['site'] == 'ebay':
                if res['store'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[res['store']] + paypal_fee) * sale_price
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * sale_price
            else:
                if res['amz_order_type'] == 'fba':
                    fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * sale_price)
            margin = sale_price - fee - dropship_cost
            row = [
                res['store'].title() if res['store'] else '',
                res['so'],
                res['product'],
                "{0:,.2f}".format(float(dropship_cost)),
                "{0:,.2f}".format(float(sale_price)),
                "{0:,.2f}".format(float(margin))
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'dropship_margin_%s_to_%s.csv' %(wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_margin', type='http', auth="user")
    def sales_margin_report(self, **post):
        wizard_id = request.env['sale.margin.wizard'].browse([int(post.get('id'))])
        if wizard_id.report_timezone == 'est':
            from_date = wizard_id.from_date + ' 04:00:00'
            to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        elif wizard_id.report_timezone == 'pdt':
            from_date = wizard_id.from_date + ' 07:00:00'
            to_date = (datetime.strptime(wizard_id.to_date + ' 07:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        elif wizard_id.report_timezone == 'utc':
            from_date = wizard_id.from_date + ' 00:00:00'
            to_date = (datetime.strptime(wizard_id.to_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Dont Reprice', 'Buyer', 'State', 'City', 'Street', 'Quant PO', 'Quant Vendor', 'Date', 'Store', 'SO Number', 'eBay Record', 'Web ID', 'Order Type', 'Products', 'Total Items', 'Sale Price', 'Vendor',
                   'Computed Dropship Cost', 'Actual Dropship Cost', 'WH Product Cost', 'WH Computed Shipping Cost',
                   'WH Actual Shipping Cost', 'Fee Computed', 'Fee Actual', 'Tax', 'Box cost', 'Returns Boxes cost', 'Returns label costs',
                   'Refunds Products Cost', 'Returned', 'Refunded amount', 'Returns Computed Dropshiping Costs ', 'Returns Actual Dropshiping Costs ',
                   'Delivery Price', 'Total Cost', 'Margin', 'Margin After Returns', 'DROPSHIP_PO']

        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""SELECT  pl.do_not_reprice, SO_PARTNER.name buyer, SO_PARTNER.city,SO_PARTNER.street, coalesce(st.name,'') partner_state,
       PICK.PO quant_po, PICK.VENDOR quant_vendor, PICK.QUANT_IDS, PICK.MOVE_IDS, SO.id, so.date_order, SO.name, SO.ebay_sales_record_number, SO.web_order_id,
                            SO.so_total, SO.amount_tax, SO.delivery_price,
                            SO.fba_commission, SO.fba_fulfillment_fee, SO.store, SO.amz_order_type,
                            SO.products, SO.total_items, SO.site, PO.vendor, SO.computed_dropship_cost,
                            PO.actual_dropship_cost, PICK.computed_wh_shipping_cost, PICK.wh_product_cost,
                            PICK.actual_pick_shipping_price, coalesce(box.box_cost, 0) as box_cost, coalesce(arl.fee, 0) as actual_amz_fee,
                            return_box.returns_boxes_cost, SR.returns_labels_cost, PICK.returned_products_cost, RETURN_STATE.return_state,
                          RETURNED_SO_LINES.returns_computed_dropship_cost,
                            R_PO.returns_actual_dropship_cost, so.DROPSHIP_PO dropship_po
                      FROM (
                           SELECT SO.id,
                                  SO.date_order,
                                  SO.ebay_sales_record_number,
                                  SO.web_order_id,
                                  MAX(SO.amz_order_type) as amz_order_type,
                                  MAX(SO.fba_commission) as fba_commission,
                                  MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                                  MAX(SO.name) as name, MAX(SO.amount_total) as so_total,
                                  MAX(SO.amount_tax) as amount_tax,
                                  MAX(SO.delivery_price) as delivery_price,
                                  string_agg(PP.part_number, ', ') as products,
                                  SUM(SOL.product_uom_qty) as total_items,
                                  SUM(SOL.dropship_cost) as computed_dropship_cost,
                                  MAX(STORE.code) as store, MAX(store.site) as site,
                                  string_agg(po.name,',') dropship_po
                           FROM sale_order SO
                           LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                           LEFT JOIN product_product PP on PP.id = SOL.product_id
                           LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                           LEFT JOIN purchase_order PO ON so.purchase_order_id = po.id
                           WHERE SO.date_order >= %s and SO.date_order < %s AND SO.state in ('sale','done') AND STORE.id in %s
                           GROUP BY SO.id, SO.ebay_sales_record_number, SO.web_order_id
                      ) as SO
                      LEFT JOIN (SELECT sr.sale_order_id as so_id, SUM(sol.dropship_cost) as returns_computed_dropship_cost
                                 FROM sale_return sr
                                 INNER JOIN sale_order_line sol ON sr.sale_order_id = sol.order_id
                                 INNER JOIN sale_return_line srl ON srl.sale_order_id = sr.sale_order_id
                                                                    AND srl.product_id = sol.product_id AND srl.sale_order_id = sr.sale_order_id
                                 WHERE sr.state in ('done', 'replacement_sent')
                                 GROUP BY sr.sale_order_id
                                 )
                      AS RETURNED_SO_LINES on RETURNED_SO_LINES.so_id = SO.id
                      LEFT JOIN (SELECT sr.sale_order_id as sale_id, string_agg(coalesce(sr.state, ''), ', ') as return_state
                                 FROM sale_return sr
                                 WHERE state in ('done', 'replacement_sent')
                                 GROUP BY sr.sale_order_id)
                                 AS RETURN_STATE ON RETURN_STATE.sale_id = SO.id
                      LEFT JOIN (
                           SELECT PO.sale_id, string_agg(PARTNER.name, ', ') as vendor,
                                  SUM(RECL.product_price + coalesce(RECL.shipping_price, 0) + coalesce(RECL.handling_price, 0)) as actual_dropship_cost
                           FROM purchase_order PO
                           LEFT JOIN purchase_recon_line RECL on RECL.purchase_order_id = PO.id
                           LEFT JOIN res_partner PARTNER on PO.partner_id = PARTNER.id
                           WHERE PO.state != 'cancel'
                           GROUP BY PO.sale_id
                      ) as PO on PO.sale_id = SO.id
                      LEFT JOIN (
                           SELECT PO.sale_id, SUM(coalesce(RECL.shipping_price, 0) + coalesce(RECL.handling_price, 0)) as returns_actual_dropship_cost
                           FROM purchase_order PO
                           INNER JOIN purchase_recon_line RECL on RECL.purchase_order_id = PO.id
                           INNER JOIN sale_return sr on sr.sale_order_id = PO.sale_id
                           WHERE PO.state != 'cancel'
                           AND sr.state in ('done', 'replacement_sent')
                           GROUP BY PO.sale_id
                      ) as R_PO on R_PO.sale_id = SO.id
                      LEFT JOIN amazon_recon_line as arl on arl.sale_order_id = SO.id
                      LEFT JOIN (SELECT SO.id,
                                        SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                                        SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                                        SUM(MOVES.total_cost) as wh_product_cost,
                                        SUM(R_MOVES.returned_products_cost) as returned_products_cost,
                                        string_agg(distinct MOVES.PO, ',') as PO,
                                         string_agg(distinct MOVES.VENDOR, ',') as VENDOR,
                                         string_agg(MOVES.QUANT_IDS::text, ',') as QUANT_IDS,
                                         string_agg(MOVES.MOVE_IDS::text, ',') as MOVE_IDS
                                 FROM sale_order SO
                                 LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                                 LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id

                                 LEFT JOIN (select pick_id,
                                             SUM(qty * product_cost) as product_cost,
                                             SUM(qty * landed_cost) as landed_cost,
                                             SUM(qty * total_cost) as total_cost,
                                             string_agg(quant_id::text, ',') as QUANT_IDS,
                                             string_agg(move_id::text, ',') as MOVE_IDS,
                                             string_agg(name, ',') as PO,
                                             string_agg(VENDOR, ',') as VENDOR
                                            from
                                            (SELECT *
                                             FROM
                                             (SELECT  quant.id as quant_id, MOVE.id as move_id,
                                                      QUANT.qty,
                                                      (CASE WHEN QUANT.product_cost = 0 OR QUANT.product_cost IS NULL THEN QUANT.cost ELSE QUANT.product_cost END) as product_cost,
                                                      QUANT.landed_cost,
                                                      QUANT.cost as total_cost,
                                                      sp.id pick_id
                                              FROM stock_move MOVE
                                              LEFT JOIN stock_quant_move_rel MQREL on MQREL.move_id = MOVE.id
                                              LEFT JOIN stock_quant QUANT on QUANT.id = MQREL.quant_id
                                              LEFT JOIN stock_picking sp on sp.id = move.picking_id
                                              where  move.picking_type_id = 4 and move.state = 'done'
                                             ) as QUANT
                                             left join (SELECT p_qmr.quant_id po_quant, po.id PO_id, po.name, p_rp.name VENDOR from stock_quant_move_rel p_qmr
                                                      left join stock_move p_sm on p_qmr.move_id = p_sm.id
                                                      left join purchase_order_line pol on p_sm.purchase_line_id = pol.id
                                                      left join purchase_order po on pol.order_id = po.id
                                                      left join res_partner p_rp on po.partner_id = p_rp.id
                                                      where p_sm.picking_type_id = 1 and  po.state in ('done', 'purchase')
                                                      ) as po_data
                                           on QUANT.quant_id = po_data.po_quant) as z
                                           group by pick_id
                                     ) as MOVES on PICK.id = MOVES.pick_id

                                 LEFT JOIN (SELECT PICK.id as pick_id, SUM(SRL.product_uom_qty * MOVE.price_unit) as returned_products_cost
                                            FROM stock_move MOVE
                                            INNER JOIN stock_picking PICK ON PICK.id = MOVE.picking_id
                                            INNER JOIN sale_return_line SRL ON SRL.sale_order_id = PICK.sale_id
                                            INNER JOIN sale_return SR ON SR.id = SRL.return_id
                                            WHERE MOVE.state = 'done' AND SRL.product_id = MOVE.product_id AND SR.state in ('done', 'replacement_sent')
                                            GROUP BY PICK.id
                                            ) as R_MOVES on PICK.id = R_MOVES.pick_id
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
                                 WHERE PICK.state = 'done' AND PICK.picking_type_id IN (4, 11)  -- Delivery Orders , Amazon FBA to Customer
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
                                                   AND so.date_order >= %s AND so.date_order < %s)
                                 AND BOXLINE.picking_id IS NOT NULL
                                 AND PICK.picking_type_id IN (4, 11)
                                 AND PICK.state = 'done'
                                 GROUP BY so.name
                                 ) AS box ON box.so_name = so.name
                      LEFT JOIN (SELECT so.name so_name, sum(boxline.quantity * PRICELIST.price) as returns_boxes_cost
                                 FROM stock_picking PICK
                                 LEFT JOIN stock_picking_packaging_line BOXLINE ON BOXLINE.picking_id = PICK.id
                                 LEFT JOIN product_product PP ON BOXLINE.packaging_product_id = PP.id
                                 LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                                 LEFT JOIN product_supplierinfo PRICELIST ON PRICELIST.product_tmpl_id = PT.id
                                 LEFT JOIN sale_order so ON so.id = PICK.sale_id
                                 LEFT JOIN sale_return sr on so.id = sr.sale_order_id
                                 WHERE sale_id IN (SELECT id
                                                   FROM sale_order so
                                                   WHERE SO.state IN ('sale', 'done')
                                                  AND so.date_order >= %s AND so.date_order < %s)
                                 AND PICK.receipt_return_id = sr.id
                                 AND BOXLINE.picking_id IS NOT NULL
                                 GROUP BY so.name
                                 ) AS return_box ON return_box.so_name = SO.name
                      LEFT JOIN (SELECT so.name as so_name, SUM(coalesce(sr.amz_label_cost, sr.ebay_label_cost)) as returns_labels_cost
                                   FROM sale_order so
                                   LEFT JOIN sale_return sr on so.id = sr.sale_order_id
                                   GROUP BY so.name
                                   ) as SR on SR.so_name = SO.name
                      LEFT JOIN sale_order b_so on so.id = b_so.id
                      LEFT JOIN res_partner SO_PARTNER ON b_so.partner_id = SO_PARTNER.id
                      LEFT JOIN res_country_state st on SO_PARTNER.state_id = st.id
                      LEFT JOIN product_listing pl on split_part(SO.web_order_id,'-',1) = pl.name
                    ORDER BY so.date_order""")
        if wizard_id.store:
            stores = (wizard_id.store.id, wizard_id.store.id)
        else:
            stores = (1, 3, 4, 5, 7)
        params = [from_date, to_date, stores, from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            so_id = res['id']
            box_cost = res['box_cost'] if res['box_cost'] else 0
            so_total = res['so_total'] if res['so_total'] else 0
            tax = res['amount_tax'] if res['amount_tax'] else 0
            delivery_price = res['delivery_price'] if res['delivery_price'] else 0
            computed_dropship_cost = res['computed_dropship_cost'] if res['computed_dropship_cost'] else 0
            actual_dropship_cost = res['actual_dropship_cost'] if res['actual_dropship_cost'] else 0
            wh_product_cost = res['wh_product_cost'] if res['wh_product_cost'] else 0
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] else 0
            actual_fee = res['actual_amz_fee']  # + res['actual_ebay_fee']

            returns_boxes_cost = res['returns_boxes_cost'] if res['returns_boxes_cost'] else 0
            returns_labels_cost = res['returns_labels_cost'] if res['returns_labels_cost'] else 0
            returned_products_cost = res['returned_products_cost'] if res['returned_products_cost'] else 0
            returns_computed_dropship_cost = res['returns_computed_dropship_cost'] if res['returns_computed_dropship_cost'] else 0
            return_state = res['return_state'] if res['return_state'] else u''  # done, replacment_sent
            refunded_amount = 0
            returns_actual_dropship_cost = res['returns_actual_dropship_cost'] if res['returns_actual_dropship_cost'] else 0
            if return_state:
                sale_order = request.env['sale.order'].browse(so_id)
                sale_returns = request.env['sale.return'].search([('sale_order_id', '=', so_id), ('state', 'in', ('done', 'replacement_sent'))])
                for r in sale_returns:
                    """
                    for return_line in r.return_line_ids:
                        po_recon_line = request.env['purchase.recon.line'].search([('purchase_order_id', '!=', False), ('purchase_order_id.sale_id', '=', so_id), ('product_id', '=', return_line.product_id)], limit = 1)
                        returns_actual_dropship_cost += (recon_line.product_price) * return_line.sale_line_id.product_uom_qty        
                    """
                    refunded_amount += r.amz_refund_amount + r.ebay_sellerTotalRefund
                # There isn't a link between recon line and the product or the po_line, so this won't work when the client bought 2 or more of the same product and don't returns one or more of these prods
                #returns_actual_dropship_cost = actual_dropship_cost

            fee = 0
            if res['site'] == 'ebay':
                if res['store'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[res['store']] + paypal_fee) * so_total
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * so_total
            else:
                if res['amz_order_type'] == 'fba':
                    if res.get('fba_commission') and res.get('fba_fulfillment_fee'):
                        fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            final_fee = actual_fee if actual_fee else fee
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + final_fee + box_cost + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # margin = so_total - total_cost - tax + delivery_price
            margin = so_total - total_cost + delivery_price
            margin_after_returns = margin
            """
            if return_state:
                margin_after_returns -=  returns_boxes_cost + returns_labels_cost + refunded_amount - (returns_actual_dropship_cost
                            if returns_actual_dropship_cost > 0 else
                            returns_computed_dropship_cost) - returned_products_cost  + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            """
            if return_state:
                """margin_after_returns -=  (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + returns_boxes_cost + returns_labels_cost + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)  
                   """
                margin_after_returns = -returns_actual_dropship_cost - returns_boxes_cost - returns_labels_cost - (actual_pick_shipping_price
                                                                                                                   if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # + returns_actual_pick_shipping_price if returns_actual_pick_shipping_price > 0 else returns_computed_wh_shipping_cost
            # Missing shipping price calculations, using the shipping price if all products are returned
            try:
                if wizard_id.report_timezone == 'est':
                    order_date = convert_date(res['date_order']) - timedelta(hours=4)
                elif wizard_id.report_timezone == 'pdt':
                    order_date = convert_date(res['date_order']) - timedelta(hours=7)
                elif wizard_id.report_timezone == 'utc':
                    order_date = convert_date(res['date_order'])
                row = [
                    res['do_not_reprice'],
                    res['buyer'].encode('utf8'),
                    res['partner_state'].encode('utf8'),
                    res['city'].encode('utf8'),
                    res['street'].encode('utf8'),
                    res['quant_po'],
                    res['quant_vendor'],
                    order_date,
                    res['store'].title() if res['store'] else '',
                    res['name'],
                    res['ebay_sales_record_number'],
                    res['web_order_id'],
                    res['amz_order_type'],
                    res['products'],
                    int(res['total_items'] or 0),
                    "{0:,.2f}".format(so_total),
                    res['vendor'] if res['vendor'] else '',
                    "{0:,.2f}".format(computed_dropship_cost),
                    "{0:,.2f}".format(actual_dropship_cost),
                    "{0:,.2f}".format(wh_product_cost),
                    "{0:,.2f}".format(computed_wh_shipping_cost),
                    "{0:,.2f}".format(actual_pick_shipping_price),
                    "{0:,.2f}".format(fee),
                    "{0:,.2f}".format(actual_fee),
                    "{0:,.2f}".format(tax),
                    "{0:,.2f}".format(box_cost),
                    "{0:,.2f}".format(returns_boxes_cost),
                    "{0:,.2f}".format(returns_labels_cost),
                    "{0:,.2f}".format(returned_products_cost),
                    return_state,
                    refunded_amount,
                    "{0:,.2f}".format(returns_computed_dropship_cost),
                    "{0:,.2f}".format(returns_actual_dropship_cost),
                    "{0:,.2f}".format(delivery_price),
                    "{0:,.2f}".format(total_cost),
                    "{0:,.2f}".format(margin),
                    "{0:,.2f}".format(margin_after_returns),
                    res['dropship_po']
                ]
            except Exception as e:
                raise UserError("Something wrong here: %s  %s" % (res, e))
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'sales_margin_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_margin_returns', type='http', auth="user")
    def sales_margin_report_returns(self, **post):
        wizard_id = request.env['sale.margin.returns.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Date', 'Store', 'SO Number', 'eBay Record', 'Web ID', 'Order Type', 'Products', 'Total Items', 'Sale Price', 'Vendor',
                   'Computed Dropship Cost', 'Actual Dropship Cost', 'WH Product Cost', 'WH Computed Shipping Cost',
                   'WH Actual Shipping Cost', 'Fee Computed', 'Fee Actual', 'Tax', 'Box cost', 'Returns Boxes cost', 'Returns label costs', 'Refunds Products Cost', 'Returned',
                   'Refunded amount', 'Returns Computed Dropshiping Costs ', 'Returns Actual Dropshiping Costs ', 'Delivery Price', 'Total Cost', 'Margin', 'Margin After Returns']

        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""SELECT SO.id, so.date_order, SO.name, SO.ebay_sales_record_number, SO.web_order_id, 
                            SO.so_total, SO.amount_tax, SO.delivery_price,  
                            SO.fba_commission, SO.fba_fulfillment_fee, SO.store, SO.amz_order_type,
                            SO.products, SO.total_items, SO.site, PO.vendor, SO.computed_dropship_cost,
                            PO.actual_dropship_cost, PICK.computed_wh_shipping_cost, PICK.wh_product_cost,
                            PICK.actual_pick_shipping_price, coalesce(box.box_cost, 0) as box_cost, coalesce(arl.fee, 0) as actual_amz_fee,
                            return_box.returns_boxes_cost, SR.returns_labels_cost, PICK.returned_products_cost, RETURN_STATE.return_state, RETURNED_SO_LINES.returns_computed_dropship_cost,
                            R_PO.returns_actual_dropship_cost
                      FROM (
                           SELECT SO.id, 
                                  SO.date_order, 
                                  SO.ebay_sales_record_number,
                                  SO.web_order_id,
                                  MAX(SO.amz_order_type) as amz_order_type,
                                  MAX(SO.fba_commission) as fba_commission,
                                  MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                                  MAX(SO.name) as name, MAX(SO.amount_total) as so_total, 
                                  MAX(SO.amount_tax) as amount_tax,
                                  MAX(SO.delivery_price) as delivery_price,
                                  string_agg(PP.part_number, ', ') as products,
                                  SUM(SOL.product_uom_qty) as total_items,
                                  SUM(SOL.dropship_cost) as computed_dropship_cost,
                                  MAX(STORE.code) as store, MAX(store.site) as site
                           FROM sale_order SO
                           LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                           LEFT JOIN product_product PP on PP.id = SOL.product_id
                           LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                           WHERE SO.date_order >= %s and SO.date_order < %s AND SO.state in ('sale','done')
                           GROUP BY SO.id, SO.ebay_sales_record_number, SO.web_order_id
                      ) as SO
                      LEFT JOIN (SELECT sr.sale_order_id as so_id, SUM(sol.dropship_cost) as returns_computed_dropship_cost
                                 FROM sale_return sr
                                 INNER JOIN sale_order_line sol ON sr.sale_order_id = sol.order_id
                                 INNER JOIN sale_return_line srl ON srl.sale_order_id = sr.sale_order_id AND srl.product_id = sol.product_id AND srl.sale_order_id = sr.sale_order_id
                                 WHERE sr.state in ('done', 'replacement_sent')
                                 GROUP BY sr.sale_order_id
                                 )
                      AS RETURNED_SO_LINES on RETURNED_SO_LINES.so_id = SO.id
                      LEFT JOIN (SELECT sr.sale_order_id as sale_id, string_agg(coalesce(sr.state, ''), ', ') as return_state 
                                 FROM sale_return sr 
                                 WHERE state in ('done', 'replacement_sent')
                                 GROUP BY sr.sale_order_id)
                                 AS RETURN_STATE ON RETURN_STATE.sale_id = SO.id                  
                      LEFT JOIN (
                           SELECT PO.sale_id, string_agg(PARTNER.name, ', ') as vendor,
                                  SUM(RECL.product_price + coalesce(RECL.shipping_price, 0) + coalesce(RECL.handling_price, 0)) as actual_dropship_cost
                           FROM purchase_order PO
                           LEFT JOIN purchase_recon_line RECL on RECL.purchase_order_id = PO.id
                           LEFT JOIN res_partner PARTNER on PO.partner_id = PARTNER.id
                           WHERE PO.state != 'cancel'
                           GROUP BY PO.sale_id
                      ) as PO on PO.sale_id = SO.id                
                      LEFT JOIN (
                           SELECT PO.sale_id, SUM(coalesce(RECL.shipping_price, 0) + coalesce(RECL.handling_price, 0)) as returns_actual_dropship_cost
                           FROM purchase_order PO
                           INNER JOIN purchase_recon_line RECL on RECL.purchase_order_id = PO.id
                           INNER JOIN sale_return sr on sr.sale_order_id = PO.sale_id
                           WHERE PO.state != 'cancel'
                           AND sr.state in ('done', 'replacement_sent')
                           GROUP BY PO.sale_id
                      ) as R_PO on R_PO.sale_id = SO.id                                                       
                      LEFT JOIN amazon_recon_line as arl on arl.sale_order_id = SO.id
                      LEFT JOIN (SELECT SO.id, 
                                        SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                                        SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                                        SUM(MOVES.product_cost) as wh_product_cost,
                                        SUM(R_MOVES.returned_products_cost) as returned_products_cost
                                 FROM sale_order SO
                                 LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                                 LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id
                                 LEFT JOIN (SELECT PICK.id as pick_id, SUM(MOVE.product_uom_qty * MOVE.price_unit) as product_cost
                                            FROM stock_move MOVE
                                            LEFT JOIN stock_picking PICK ON PICK.id = MOVE.picking_id
                                            WHERE MOVE.state = 'done'
                                            GROUP BY PICK.id
                                            ) as MOVES on PICK.id = MOVES.pick_id
                                 LEFT JOIN (SELECT PICK.id as pick_id, SUM(SRL.product_uom_qty * MOVE.price_unit) as returned_products_cost
                                            FROM stock_move MOVE
                                            INNER JOIN stock_picking PICK ON PICK.id = MOVE.picking_id
                                            INNER JOIN sale_return_line SRL ON SRL.sale_order_id = PICK.sale_id
                                            INNER JOIN sale_return SR ON SR.id = SRL.return_id 
                                            WHERE MOVE.state = 'done' AND SRL.product_id = MOVE.product_id AND SR.state in ('done', 'replacement_sent')
                                            GROUP BY PICK.id
                                            ) as R_MOVES on PICK.id = R_MOVES.pick_id                                             
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
                                 WHERE PICK.state = 'done' AND PICK.picking_type_id IN (4, 11)  -- Delivery Orders , Amazon FBA to Customer
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
                                                   AND so.date_order >= %s AND so.date_order < %s)
                                 AND BOXLINE.picking_id IS NOT NULL 
                                 AND PICK.picking_type_id IN (4, 11) 
                                 AND PICK.state = 'done'
                                 GROUP BY so.name
                                 ) AS box ON box.so_name = so.name 
                      LEFT JOIN (SELECT so.name so_name, sum(boxline.quantity * PRICELIST.price) as returns_boxes_cost
                                 FROM stock_picking PICK
                                 LEFT JOIN stock_picking_packaging_line BOXLINE ON BOXLINE.picking_id = PICK.id
                                 LEFT JOIN product_product PP ON BOXLINE.packaging_product_id = PP.id
                                 LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                                 LEFT JOIN product_supplierinfo PRICELIST ON PRICELIST.product_tmpl_id = PT.id
                                 LEFT JOIN sale_order so ON so.id = PICK.sale_id
                                 LEFT JOIN sale_return sr on so.id = sr.sale_order_id
                                 WHERE sale_id IN (SELECT id
                                                   FROM sale_order so
                                                   WHERE SO.state IN ('sale', 'done') 
                                                   AND so.date_order >= %s AND so.date_order < %s)
                                 AND PICK.receipt_return_id = sr.id
                                 AND BOXLINE.picking_id IS NOT NULL 
                                 GROUP BY so.name
                                 ) AS return_box ON return_box.so_name = SO.name
                       LEFT JOIN (SELECT so.name as so_name, SUM(coalesce(sr.amz_label_cost, sr.ebay_label_cost)) as returns_labels_cost
                                   FROM sale_order so
                                   LEFT JOIN sale_return sr on so.id = sr.sale_order_id
                                   GROUP BY so.name 
                                   ) as SR on SR.so_name = SO.name
                       ORDER BY so.date_order""")
        params = [from_date, to_date, from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            so_id = res['id']
            box_cost = res['box_cost'] if res['box_cost'] else 0
            so_total = res['so_total'] if res['so_total'] else 0
            tax = res['amount_tax'] if res['amount_tax'] else 0
            delivery_price = res['delivery_price'] if res['delivery_price'] else 0
            computed_dropship_cost = res['computed_dropship_cost'] if res['computed_dropship_cost'] else 0
            actual_dropship_cost = res['actual_dropship_cost'] if res['actual_dropship_cost'] else 0
            wh_product_cost = res['wh_product_cost'] if res['wh_product_cost'] else 0
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] else 0
            actual_fee = res['actual_amz_fee']  # + res['actual_ebay_fee']

            returns_boxes_cost = res['returns_boxes_cost'] if res['returns_boxes_cost'] else 0
            returns_labels_cost = res['returns_labels_cost'] if res['returns_labels_cost'] else 0
            returned_products_cost = res['returned_products_cost'] if res['returned_products_cost'] else 0
            returns_computed_dropship_cost = res['returns_computed_dropship_cost'] if res['returns_computed_dropship_cost'] else 0
            return_state = res['return_state'] if res['return_state'] else u''  # done, replacment_sent
            refunded_amount = 0
            returns_actual_dropship_cost = res['returns_actual_dropship_cost'] if res['returns_actual_dropship_cost'] else 0
            if return_state:
                sale_order = request.env['sale.order'].browse(so_id)
                sale_returns = request.env['sale.return'].search([('sale_order_id', '=', so_id), ('state', 'in', ('done', 'replacement_sent'))])
                for r in sale_returns:
                    """
                    for return_line in r.return_line_ids:
                        po_recon_line = request.env['purchase.recon.line'].search([('purchase_order_id', '!=', False), ('purchase_order_id.sale_id', '=', so_id), ('product_id', '=', return_line.product_id)], limit = 1)
                        returns_actual_dropship_cost += (recon_line.product_price) * return_line.sale_line_id.product_uom_qty        
                    """
                    refunded_amount += r.amz_refund_amount + r.ebay_sellerTotalRefund
                    # There isn't a link between recon line and the product or the po_line, so this won't work when the client bought 2 or more of the same product and don't returns one or more of these prods
                    # returns_actual_dropship_cost = actual_dropship_cost

            fee = 0
            if res['site'] == 'ebay':
                if res['store'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[res['store']] + paypal_fee) * so_total
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * so_total
            else:
                if res['amz_order_type'] == 'fba':
                    if res.get('fba_commission') and res.get('fba_fulfillment_fee'):
                        fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            final_fee = actual_fee if actual_fee else fee
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + final_fee + box_cost + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # margin = so_total - total_cost - tax + delivery_price
            margin = so_total - total_cost + delivery_price
            margin_after_returns = margin
            """
            if return_state:
                margin_after_returns -=  returns_boxes_cost + returns_labels_cost + refunded_amount - (returns_actual_dropship_cost
                            if returns_actual_dropship_cost > 0 else
                            returns_computed_dropship_cost) - returned_products_cost  + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            """
            if return_state:
                """margin_after_returns -=  (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + returns_boxes_cost + returns_labels_cost + (actual_pick_shipping_price
                                                                                              if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)  
                   """
                margin_after_returns = -returns_actual_dropship_cost - returns_boxes_cost - returns_labels_cost - (actual_pick_shipping_price
                                                                                                                   if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
                # + returns_actual_pick_shipping_price if returns_actual_pick_shipping_price > 0 else returns_computed_wh_shipping_cost
            # Missing shipping price calculations, using the shipping price if all products are returned
            try:
                row = [
                    convert_date(res['date_order']) - timedelta(hours=4),
                    res['store'].title() if res['store'] else '',
                    res['name'],
                    res['ebay_sales_record_number'],
                    res['web_order_id'],
                    res['amz_order_type'],
                    res['products'],
                    int(res['total_items']),
                    "{0:,.2f}".format(so_total),
                    res['vendor'] if res['vendor'] else '',
                    "{0:,.2f}".format(computed_dropship_cost),
                    "{0:,.2f}".format(actual_dropship_cost),
                    "{0:,.2f}".format(wh_product_cost),
                    "{0:,.2f}".format(computed_wh_shipping_cost),
                    "{0:,.2f}".format(actual_pick_shipping_price),
                    "{0:,.2f}".format(fee),
                    "{0:,.2f}".format(actual_fee),
                    "{0:,.2f}".format(tax),
                    "{0:,.2f}".format(box_cost),
                    "{0:,.2f}".format(returns_boxes_cost),
                    "{0:,.2f}".format(returns_labels_cost),
                    "{0:,.2f}".format(returned_products_cost),
                    return_state,
                    refunded_amount,
                    "{0:,.2f}".format(returns_computed_dropship_cost),
                    "{0:,.2f}".format(returns_actual_dropship_cost),
                    "{0:,.2f}".format(delivery_price),
                    "{0:,.2f}".format(total_cost),
                    "{0:,.2f}".format(margin),
                    "{0:,.2f}".format(margin_after_returns),
                ]
            except Exception as e:
                raise UserError("Something wrong here: %s  %s" % (res, e))
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'marg_ret_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_margin_states', type='http', auth="user")
    def sales_margin_by_state_report(self, **post):
        wizard_id = request.env['sale.margin.states.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        store_id = wizard_id.store_id
        if store_id:
            store_condition = store_id.id
            valid_fname = 'margin_%s_%s_to_%s.csv' % (store_id.code, wizard_id.from_date, wizard_id.to_date)
        else:
            store_condition = tuple([r.id for r in request.env["sale.store"].search([('enabled', '=', True)])])
            valid_fname = 'margin_states_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['State', 'Store', 'SO Number', 'Order Type', 'Products', 'Total Items', 'Sale Price', 'Vendor',
                   'Computed Dropship Cost', 'Actual Dropship Cost', 'WH Product Cost', 'WH Computed Shipping Cost',
                   'WH Acutal Shipping Cost', 'Fee', 'Tax', 'Box cost', 'Delivery Price', 'Total Cost', 'Margin']

        writer.writerow([name.encode('utf-8') for name in columns])

        qry = ("""SELECT  so.id as id, rcs.name as state, so.date_order, SO.name, SO.so_total, SO.amount_tax, SO.delivery_price,
                          SO.fba_commission, SO.fba_fulfillment_fee, SO.store, SO.amz_order_type,
                          SO.products, SO.total_items, SO.site, PO.vendor, SO.computed_dropship_cost,
                          PO.actual_dropship_cost, PICK.computed_wh_shipping_cost, PICK.wh_product_cost,
                          PICK.actual_pick_shipping_price, coalesce(box.box_cost, 0) as box_cost
                   FROM (
                        SELECT SO.id,
                               SO.date_order,
                               SO.partner_id,
                               MAX(SO.amz_order_type) as amz_order_type,
                               MAX(SO.fba_commission) as fba_commission,
                               MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                               MAX(SO.name) as name, MAX(SO.amount_total) as so_total,
                               MAX(SO.amount_tax) as amount_tax,
                               MAX(SO.delivery_price) as delivery_price,
                               string_agg(PP.part_number, ', ') as products,
                               SUM(SOL.product_uom_qty) as total_items,
                               SUM(SOL.dropship_cost) as computed_dropship_cost,
                               MAX(STORE.code) as store, MAX(store.site) as site
                        FROM sale_order SO
                        LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                        LEFT JOIN product_product PP on PP.id = SOL.product_id
                        LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                        WHERE SO.date_order >= %s and SO.date_order < %s AND SO.state in ('sale','done') AND SO.store_id IN %s
                        GROUP BY SO.id
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
                   LEFT JOIN (SELECT SO.id,
                                     SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                                     SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                                     SUM(MOVES.product_cost) as wh_product_cost
                              FROM sale_order SO
                              LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                              LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id
                              LEFT JOIN (SELECT PICK.id as pick_id, SUM(MOVE.product_uom_qty * MOVE.price_unit) as product_cost
                                         FROM stock_move MOVE
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
                                                AND so.date_order >= %s AND so.date_order < %s)
                              AND BOXLINE.picking_id IS NOT NULL
                              AND PICK.picking_type_id IN (4, 11)
                              AND PICK.state = 'done'
                              GROUP BY so.name
                              ) AS box ON box.so_name = so.name
                   LEFT JOIN res_partner rp
                   ON so.partner_id = rp.id
                   LEFT JOIN res_country_state rcs
                   ON rp.state_id = rcs.id
                   ORDER BY state, store""")
        params = [from_date, to_date, store_condition, from_date, to_date]
        cr = request.env.cr
        cr.execute(qry, params)
        results = cr.dictfetchall()
        for res in results:
            box_cost = res['box_cost'] if res['box_cost'] else 0
            so_total = res['so_total'] if res['so_total'] else 0
            tax = res['amount_tax'] if res['amount_tax'] else 0
            delivery_price = res['delivery_price'] if res['delivery_price'] else 0
            computed_dropship_cost = res['computed_dropship_cost'] if res['computed_dropship_cost'] else 0
            actual_dropship_cost = res['actual_dropship_cost'] if res['actual_dropship_cost'] else 0
            wh_product_cost = res['wh_product_cost'] if res['wh_product_cost'] else 0
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] else 0
            if res['site'] == 'ebay':
                if res['store'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[res['store']] + paypal_fee) * so_total
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * so_total
            else:
                if res['amz_order_type'] == 'fba' and res.get('fba_commission') and res.get('fba_fulfillment_fee'):
                    fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + fee + box_cost + (actual_pick_shipping_price
                                                                                        if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # margin = so_total - total_cost - tax + delivery_price
            margin = so_total - total_cost + delivery_price
            try:
                row = [
                    res['state'],
                    res['store'].title() if res['store'] else '',
                    res['name'],
                    res['amz_order_type'],
                    res['products'],
                    int(res['total_items']),
                    "{0:,.2f}".format(so_total),
                    res['vendor'] if res['vendor'] else '',
                    "{0:,.2f}".format(computed_dropship_cost),
                    "{0:,.2f}".format(actual_dropship_cost),
                    "{0:,.2f}".format(wh_product_cost),
                    "{0:,.2f}".format(computed_wh_shipping_cost),
                    "{0:,.2f}".format(actual_pick_shipping_price),
                    "{0:,.2f}".format(fee),
                    "{0:,.2f}".format(tax),
                    "{0:,.2f}".format(box_cost),
                    "{0:,.2f}".format(delivery_price),
                    "{0:,.2f}".format(total_cost),
                    "{0:,.2f}".format(margin),
                ]
                writer.writerow(row)
            except Exception as e:
                _logger.error('SO: %s \n %s \n %s', res['id'], e, res)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_margin_mapm', type='http', auth="user")
    def sales_margin_mapm_report(self, **post):
        wizard_id = request.env['sale.margin.mapm.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Store', 'SO Number', 'Order Type', 'Products', 'Total Items', 'Sale Price', 'Vendor', 'Computed Dropship Cost',
                   'Actual Dropship Cost', 'WH Product Cost', 'WH Computed Shipping Cost', 'WH Acutal Shipping Cost', 'Fee', 'Tax',
                   'Box cost', 'Delivery Price', 'FBA ship', 'Total Cost', 'Margin']
        writer.writerow([name.encode('utf-8') for name in columns])
        sql = ("""SELECT so.date_order, SO.name, SO.so_total, SO.amount_tax, SO.delivery_price,  
                         SO.fba_commission, SO.fba_fulfillment_fee, SO.store, SO.amz_order_type,
                         SO.products, SO.total_items, SO.site, PO.vendor, SO.computed_dropship_cost,
                         PO.actual_dropship_cost, PICK.computed_wh_shipping_cost, PICK.wh_product_cost, PICK.amz_fba_shipping_cost,
                         PICK.actual_pick_shipping_price, coalesce(box.box_cost, 0) as box_cost
                   FROM (
                        SELECT SO.id, 
                               SO.date_order, 
                               MAX(SO.amz_order_type) as amz_order_type,
                               MAX(SO.fba_commission) as fba_commission,
                               MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                               MAX(SO.name) as name, MAX(SO.amount_total) as so_total, 
                               MAX(SO.amount_tax) as amount_tax,
                               MAX(SO.delivery_price) as delivery_price,
                               string_agg(PP.part_number, ', ') as products,
                               SUM(SOL.product_uom_qty) as total_items,
                               SUM(SOL.dropship_cost) as computed_dropship_cost,
                               MAX(STORE.code) as store, MAX(store.site) as site
                        FROM sale_order SO
                        LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                        LEFT JOIN product_product PP on PP.id = SOL.product_id
                        LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                        WHERE SO.date_order >= %s and SO.date_order < %s AND SO.state in ('sale','done')
                        AND SOL.item_id LIKE 'MAPM-%%' AND SOL.item_id NOT LIKE 'MAPM-PBL-%%' AND SOL.order_id is not NULL
                        GROUP BY SO.id
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
                   LEFT JOIN (SELECT SO.id, 
                                     SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                                     SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                                     SUM(MOVES.product_cost) as wh_product_cost,
                                     SUM(MOVES.amz_fba_shipping_cost) as amz_fba_shipping_cost
                              FROM sale_order SO
                              LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                              LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id
                              LEFT JOIN (SELECT PICK.id as pick_id, 
                                                SUM(MOVE.product_uom_qty * MOVE.price_unit) as product_cost,
                                                SUM(MOVE.product_uom_qty *q.amz_fba_shipping_cost) AS amz_fba_shipping_cost
                                         FROM stock_move MOVE
                                         LEFT JOIN stock_picking PICK ON PICK.id = MOVE.picking_id
                                         LEFT JOIN  stock_quant_move_rel sqmrel ON MOVE.id = sqmrel.move_id
                                         LEFT JOIN stock_quant q on sqmrel.quant_id = q.id
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
                                                AND so.date_order >= %s AND so.date_order < %s)
                              AND BOXLINE.picking_id IS NOT NULL 
                              AND PICK.picking_type_id IN (4, 11) 
                              AND PICK.state = 'done'
                              GROUP BY so.name
                              ) AS box ON box.so_name = so.name 
                   ORDER BY so.date_order""")
        params = [from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            box_cost = res['box_cost'] if res['box_cost'] else 0
            amz_ship = res['amz_fba_shipping_cost'] if res['amz_fba_shipping_cost'] else 0
            so_total = res['so_total'] if res['so_total'] else 0
            tax = res['amount_tax'] if res['amount_tax'] else 0
            delivery_price = res['delivery_price'] if res['delivery_price'] else 0
            computed_dropship_cost = res['computed_dropship_cost'] if res['computed_dropship_cost'] else 0
            actual_dropship_cost = res['actual_dropship_cost'] if res['actual_dropship_cost'] else 0
            wh_product_cost = res['wh_product_cost'] if res['wh_product_cost'] else 0
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] else 0
            fee = 0
            if res['site'] == 'amz':
                if res['amz_order_type'] == 'fba':
                    if res.get('fba_commission') and res.get('fba_fulfillment_fee'):
                        fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + fee + box_cost + (actual_pick_shipping_price
                                                                                        if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # margin = so_total - total_cost - amz_ship - tax + delivery_price
            margin = so_total - total_cost - amz_ship + delivery_price
            row = [
                res['store'].title() if res['store'] else '',
                res['name'],
                res['amz_order_type'],
                res['products'],
                int(res['total_items']),
                "{0:,.2f}".format(so_total),
                res['vendor'] if res['vendor'] else '',
                "{0:,.2f}".format(computed_dropship_cost),
                "{0:,.2f}".format(actual_dropship_cost),
                "{0:,.2f}".format(wh_product_cost),
                "{0:,.2f}".format(computed_wh_shipping_cost),
                "{0:,.2f}".format(actual_pick_shipping_price),
                "{0:,.2f}".format(fee),
                "{0:,.2f}".format(tax),
                "{0:,.2f}".format(box_cost),
                "{0:,.2f}".format(delivery_price),
                "{0:,.2f}".format(amz_ship),
                "{0:,.2f}".format(total_cost),
                "{0:,.2f}".format(margin),
            ]
            writer.writerow(row)
        fp.seek(0)
        data = fp.read()
        fp.close()
        valid_fname = 'sales_margin_mapm_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_margin_mapm_pbl', type='http', auth="user")
    def sales_margin_mapm_pbl_report(self, **post):
        wizard_id = request.env['sale.margin.mapm.pbl.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Store', 'SO Number', 'Order Type', 'Products', 'Total Items', 'Sale Price', 'Vendor', 'Computed Dropship Cost',
                   'Actual Dropship Cost', 'WH Product Cost', 'WH Computed Shipping Cost', 'WH Acutal Shipping Cost', 'Fee', 'Tax',
                   'Box Cost', 'Delivery Price', 'FBA ship', 'Total Cost', 'Margin']

        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""SELECT so.date_order, SO.name, SO.so_total, SO.amount_tax, SO.delivery_price,  
                         SO.fba_commission, SO.fba_fulfillment_fee, SO.store, SO.amz_order_type,
                         SO.products, SO.total_items, SO.site, PO.vendor, SO.computed_dropship_cost,
                         PO.actual_dropship_cost, PICK.computed_wh_shipping_cost, PICK.wh_product_cost, PICK.amz_fba_shipping_cost,
                         PICK.actual_pick_shipping_price, coalesce(box.box_cost, 0) as box_cost
                   FROM (
                        SELECT SO.id, 
                               SO.date_order, 
                               MAX(SO.amz_order_type) as amz_order_type,
                               MAX(SO.fba_commission) as fba_commission,
                               MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                               MAX(SO.name) as name, MAX(SO.amount_total) as so_total, 
                               MAX(SO.amount_tax) as amount_tax,
                               MAX(SO.delivery_price) as delivery_price,
                               string_agg(PP.part_number, ', ') as products,
                               SUM(SOL.product_uom_qty) as total_items,
                               SUM(SOL.dropship_cost) as computed_dropship_cost,
                               MAX(STORE.code) as store, MAX(store.site) as site
                        FROM sale_order SO
                        LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                        LEFT JOIN product_product PP on PP.id = SOL.product_id
                        LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                        WHERE SO.date_order >= %s and SO.date_order < %s AND SO.state in ('sale','done')
                        AND SOL.item_id LIKE 'MAPM-PBL-%%' AND SOL.order_id is not NULL
                        GROUP BY SO.id
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
                   LEFT JOIN (SELECT SO.id, 
                                     SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                                     SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                                     SUM(MOVES.product_cost) as wh_product_cost,
                                     SUM(MOVES.amz_fba_shipping_cost) as amz_fba_shipping_cost
                              FROM sale_order SO
                              LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                              LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id
                              LEFT JOIN (SELECT PICK.id as pick_id, 
                                                SUM(MOVE.product_uom_qty * MOVE.price_unit) as product_cost,
                                                SUM(MOVE.product_uom_qty *q.amz_fba_shipping_cost) AS amz_fba_shipping_cost
                                         FROM stock_move MOVE
                                         LEFT JOIN stock_picking PICK ON PICK.id = MOVE.picking_id
                                         LEFT JOIN  stock_quant_move_rel sqmrel ON MOVE.id = sqmrel.move_id
                                         LEFT JOIN stock_quant q on sqmrel.quant_id = q.id
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
                                                AND so.date_order >= %s AND so.date_order < %s)
                              AND BOXLINE.picking_id IS NOT NULL 
                              AND PICK.picking_type_id IN (4, 11) 
                              AND PICK.state = 'done'
                              GROUP BY so.name
                              ) AS box ON box.so_name = so.name 
                   ORDER BY so.date_order""")
        params = [from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            box_cost = res['box_cost'] if res['box_cost'] else 0
            amz_ship = res['amz_fba_shipping_cost'] if res['amz_fba_shipping_cost'] else 0
            so_total = res['so_total'] if res['so_total'] else 0
            tax = res['amount_tax'] if res['amount_tax'] else 0
            delivery_price = res['delivery_price'] if res['delivery_price'] else 0
            computed_dropship_cost = res['computed_dropship_cost'] if res['computed_dropship_cost'] else 0
            actual_dropship_cost = res['actual_dropship_cost'] if res['actual_dropship_cost'] else 0
            wh_product_cost = res['wh_product_cost'] if res['wh_product_cost'] else 0
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] else 0
            fee = 0
            if res['site'] == 'amz':
                if res['amz_order_type'] == 'fba':
                    if res.get('fba_commission') and res.get('fba_fulfillment_fee'):
                        fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + fee + box_cost + (actual_pick_shipping_price
                                                                                        if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # margin = so_total - total_cost - amz_ship - tax + delivery_price
            margin = so_total - total_cost - amz_ship + delivery_price
            row = [
                res['store'].title() if res['store'] else '',
                res['name'],
                res['amz_order_type'],
                res['products'],
                int(res['total_items']),
                "{0:,.2f}".format(so_total),
                res['vendor'] if res['vendor'] else '',
                "{0:,.2f}".format(computed_dropship_cost),
                "{0:,.2f}".format(actual_dropship_cost),
                "{0:,.2f}".format(wh_product_cost),
                "{0:,.2f}".format(computed_wh_shipping_cost),
                "{0:,.2f}".format(actual_pick_shipping_price),
                "{0:,.2f}".format(fee),
                "{0:,.2f}".format(tax),
                "{0:,.2f}".format(box_cost),
                "{0:,.2f}".format(delivery_price),
                "{0:,.2f}".format(amz_ship),
                "{0:,.2f}".format(total_cost),
                "{0:,.2f}".format(margin),
            ]
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'sales_margin_mapm_pbl_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/sales_margin_grouped', type='http', auth="user")
    def sales_margin_grouped(self, **post):
        wizard_id = request.env['sale.margin.grouped.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Web ID', 'Date', 'Store', 'SO Number', 'eBay Record', 'Order Type', 'Products', 'Total Items', 'Sale Price', 'Vendor',
                   'Computed Dropship Cost', 'Actual Dropship Cost', 'WH Product Cost', 'WH Computed Shipping Cost',
                   'WH Actual Shipping Cost', 'Fee', 'Tax', 'Box cost', 'Delivery Price', 'Total Cost', 'Margin']

        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""-- sales margin report grouped by web order id --
                    SELECT so.web_order_id as web_id,
                           string_agg(SO.date_order::text, ', ') as date_order,
                           string_agg(SO.STORE, ', ') as store,
                           string_agg(SO.name, ', ') as so_number,
                           string_agg(SO.ebay_sales_record_number, ', ') as ebay_record,
                           string_agg(SO.AMZ_ORDER_TYPE, ', ') as amz_order_type,
                           string_agg(SO.PRODUCTS, ', ') as products,
                           sum(SO.TOTAL_ITEMS) as total_items,
                           sum(SO.so_total) as so_total,
                           string_agg(PO.VENDOR, ', ') as vendor,
                           sum(SO.computed_dropship_cost) as computed_dropship_cost,
                           sum(PO.actual_dropship_cost) as actual_dropship_cost,
                           sum(PICK.wh_product_cost) as wh_product_cost,
                           sum(PICK.computed_wh_shipping_cost) as computed_wh_shipping_cost,
                           sum(PICK.actual_pick_shipping_price) as actual_pick_shipping_price,
                           sum(SO.fba_fulfillment_fee) as fba_fee,
                           sum(SO.amount_tax) as amount_tax,
                           sum(coalesce(box.box_cost, 0)) as box_cost,
                           sum(SO.delivery_price) as delivery_price,
                           sum(SO.fba_commission) as fba_commission,
                           string_agg(SO.SITE, ', ') as site
                    FROM (SELECT SO.id,
                                 SO.date_order,
                                 SO.ebay_sales_record_number,
                                 SO.web_order_id,
                                 MAX(SO.amz_order_type) as amz_order_type,
                                 MAX(SO.fba_commission) as fba_commission,
                                 MAX(SO.fba_fulfillment_fee) as fba_fulfillment_fee,
                                 MAX(SO.name) as name, MAX(SO.amount_total) as so_total,
                                 MAX(SO.amount_tax) as amount_tax,
                                 MAX(SO.delivery_price) as delivery_price,
                                 string_agg(PP.part_number, ', ') as products,
                                 SUM(SOL.product_uom_qty) as total_items,
                                 SUM(SOL.dropship_cost) as computed_dropship_cost,
                                 MAX(STORE.code) as store, MAX(store.site) as site
                          FROM sale_order SO
                          LEFT JOIN sale_order_line SOL ON SOL.order_id = SO.id
                          LEFT JOIN product_product PP on PP.id = SOL.product_id
                          LEFT JOIN sale_store STORE on STORE.id = SO.store_id
                          WHERE SO.date_order >= %s and SO.date_order < %s AND SO.state in ('sale','done')
                          GROUP BY SO.id, SO.ebay_sales_record_number, SO.web_order_id
                         ) as SO
                    LEFT JOIN (SELECT PO.sale_id, string_agg(PARTNER.name, ', ') as vendor,
                                      SUM(RECL.product_price + coalesce(RECL.shipping_price, 0) + coalesce(RECL.handling_price, 0)) as actual_dropship_cost
                               FROM purchase_order PO
                               LEFT JOIN purchase_recon_line RECL on RECL.purchase_order_id = PO.id
                               LEFT JOIN res_partner PARTNER on PO.partner_id = PARTNER.id
                               WHERE PO.state != 'cancel'
                               GROUP BY PO.sale_id
                              ) as PO on PO.sale_id = SO.id
                    LEFT JOIN (SELECT SO.id,
                                      SUM(PICK.rate + PICK.rate * coalesce(TLINES.count, 0)) as computed_wh_shipping_cost,
                                      SUM(coalesce(RECPICK.actual_pick_shipping_price, 0) + coalesce(TLINES.actual_tline_shipping_price , 0)) as actual_pick_shipping_price,
                                      SUM(MOVES.product_cost) as wh_product_cost
                               FROM sale_order SO
                               LEFT JOIN procurement_group PG on SO.procurement_group_id = PG.id
                               LEFT JOIN stock_picking PICK ON PICK.group_id = PG.id
                               LEFT JOIN (SELECT PICK.id as pick_id, SUM(MOVE.product_uom_qty * MOVE.price_unit) as product_cost
                                          FROM stock_move MOVE
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
                               WHERE sale_id IN (SELECT id FROM sale_order so WHERE SO.state IN ('sale', 'done') AND so.date_order >= %s AND so.date_order < %s)
                               AND BOXLINE.picking_id IS NOT NULL
                               AND PICK.picking_type_id IN (4, 11) AND PICK.state = 'done'
                               GROUP BY so.name
                              ) AS box ON box.so_name = so.name
                    group by so.web_order_id""")
        params = [from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            box_cost = res['box_cost'] if res['box_cost'] else 0
            so_total = res['so_total'] if res['so_total'] else 0
            tax = res['amount_tax'] if res['amount_tax'] else 0
            delivery_price = res['delivery_price'] if res['delivery_price'] else 0
            computed_dropship_cost = res['computed_dropship_cost'] if res['computed_dropship_cost'] else 0
            actual_dropship_cost = res['actual_dropship_cost'] if res['actual_dropship_cost'] else 0
            wh_product_cost = res['wh_product_cost'] if res['wh_product_cost'] else 0
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] else 0
            fee = 0
            if 'ebay' in res['site']:
                if res['store'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[res['store']] + paypal_fee) * so_total
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * so_total
            else:
                if 'fba' in res['amz_order_type']:
                    if res.get('fba_commission') and res.get('fba_fulfillment_fee'):
                        fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    fee = max(1.00, 0.12 * so_total)
            total_cost = (actual_dropship_cost
                          if actual_dropship_cost > 0 else
                          computed_dropship_cost) + wh_product_cost + fee + box_cost + (actual_pick_shipping_price
                                                                                        if actual_pick_shipping_price > 0 else computed_wh_shipping_cost)
            # margin = so_total - total_cost - tax + delivery_price
            margin = so_total - total_cost + delivery_price
            try:
                row = [
                    res['web_id'],
                    convert_date(res['date_order']) - timedelta(hours=4),
                    res['store'].title() if res['store'] else '',
                    res['so_number'],
                    res['ebay_record'],
                    res['amz_order_type'],
                    res['products'],
                    int(res['total_items']),
                    "{0:,.2f}".format(so_total),
                    res['vendor'] if res['vendor'] else '',
                    "{0:,.2f}".format(computed_dropship_cost),
                    "{0:,.2f}".format(actual_dropship_cost),
                    "{0:,.2f}".format(wh_product_cost),
                    "{0:,.2f}".format(computed_wh_shipping_cost),
                    "{0:,.2f}".format(actual_pick_shipping_price),
                    "{0:,.2f}".format(fee),
                    "{0:,.2f}".format(tax),
                    "{0:,.2f}".format(box_cost),
                    "{0:,.2f}".format(delivery_price),
                    "{0:,.2f}".format(total_cost),
                    "{0:,.2f}".format(margin),
                ]
            except Exception as e:
                raise UserError("Something wrong here: %s  %s" % (res, e))
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'sales_margin_grouped_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])


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


def convert_date(dt):
    if len(dt) < 21:
        return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')  # 2019-12-21 23:59:59
    else:
        return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f').replace(microsecond=0)  # 2019-12-21 23:59:59.003
