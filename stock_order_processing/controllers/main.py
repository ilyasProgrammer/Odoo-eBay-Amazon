# -*- coding: utf-8 -*-

import csv
import pytz
from cStringIO import StringIO
from datetime import datetime, timedelta
from pytz import timezone
from odoo import http, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.web.controllers.main import content_disposition
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


def dt_to_utc(sdt):
    return timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')


class StockBarcodeController(http.Controller):

    @http.route('/order_processing/done', type='json', auth='user')
    def order_processing_done(self, **kw):
        try:
            pick_id = request.env['stock.picking'].search([('name', '=', kw['name']), ('state', '=', 'assigned')], limit=1)
            result = pick_id.quick_process_order(kw['packaging_not_required'], kw['packages'])
        except UserError as e:
            raise UserError('%s' % (e[0],))
        return result

    @http.route('/order_processing/open_order', type='json', auth='user')
    def order_processing_open_order(self, name, **kw):
        pick_id = request.env['stock.picking'].search([('name', '=', name)], limit=1)
        if pick_id.sale_id:
            action_order_form = request.env.ref('stock_order_processing.sale_order_action_form')
            action_order_form = action_order_form.read()[0]
            action_order_form['res_id'] = pick_id.sale_id.id
            return {'action': action_order_form}
        elif pick_id.replacement_return_id:
            action_return_form = request.env.ref('stock_order_processing.sale_return_action_form')
            action_return_form = action_return_form.read()[0]
            action_return_form['res_id'] = pick_id.replacement_return_id.id
            return {'action': action_return_form}
        return False

    @http.route('/order_processing/open_processed_orders', type='json', auth='user')
    def order_processing_open_processed_orders(self, **kw):
        pick_ids = request.env['stock.picking'].get_orders_processed()
        action_pick_list = request.env.ref('stock.action_picking_tree_all')
        action_pick_list = action_pick_list.read()[0]
        action_pick_list['domain'] = [('id', 'in', pick_ids.ids)]
        return {'action': action_pick_list}

    @http.route('/order_processing/open_prime_orders', type='json', auth='user')
    def order_processing_open_prime_orders(self, **kw):
        prime_ship_ids = request.env['stock.picking'].search([('picking_type_id.name', '=', 'Delivery Orders'), ('amz_order_type', '=', 'fbm'), ('state', 'not in', ('cancel', 'done'))])
        action_pick_list = request.env.ref('stock.action_picking_tree_all')
        action_pick_list = action_pick_list.read()[0]
        action_pick_list['domain'] = [('id', 'in', prime_ship_ids.ids)]
        action_pick_list['context'] = {}
        action_pick_list['view_mode'] = 'form'
        print action_pick_list
        return {'action': action_pick_list}

    @http.route('/order_processing/open_late_orders', type='json', auth='user')
    def order_processing_open_late_orders(self, **kw):
        from_time = (datetime.now() - timedelta(days=2)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        late_ship_ids = request.env['stock.picking'].search([('picking_type_id.name', '=', 'Delivery Orders'), ('create_date', '<=', from_time), ('state', 'not in', ('cancel', 'done'))])
        action_pick_list = request.env.ref('stock.action_picking_tree_all')
        action_pick_list = action_pick_list.read()[0]
        action_pick_list['domain'] = [('id', 'in', late_ship_ids.ids)]
        action_pick_list['context'] = {}
        action_pick_list['view_mode'] = 'form'
        return {'action': action_pick_list}

    @http.route('/order_processing/get_new_label', type='json', auth='user')
    def order_processing_get_new_label(self, **kw):
        ship_id = request.env['stock.picking'].search([('id', '=', int(kw['ship_id']))], limit=1)
        now = datetime.now().strftime('%Y%m%d%H%M%S')
        if ship_id.sale_id:
            order_result = ship_id.sale_id.ss_send_order(ship_id.sale_id.name + now)
        elif ship_id.replacement_return_id:
            order_result = ship_id.replacement_return_id.sale_order_id.ss_send_order(ship_id.replacement_return_id.sale_order_id.name + now)
        data = ship_id.prepare_get_label_data(order_result['orderId'])
        result = request.env['sale.order'].ss_execute_request('POST', '/orders/createlabelfororder', data)
        tracking_line_id = request.env['stock.picking.tracking.line'].create({
            'name': result['trackingNumber'],
            'label': result['labelData'],
            'picking_id': ship_id.id,
            'shipstation_id': order_result['orderId']
        })
        # tracking_line_id = ship_id.tracking_line_ids[0]
        return {'tracking_number': tracking_line_id.name, 'label': tracking_line_id.label}

    @http.route('/order_processing/get_box_prices', type='json', auth='user')
    def order_processing_get_box_prices(self, **kw):
        box_recs = request.env['product.supplierinfo'].search([('product_tmpl_id.is_packaging_product', '=', True)])
        res = []
        for box_rec in box_recs:
            res.append({'name': box_rec.product_tmpl_id.name, 'id': box_rec.product_tmpl_id.id, 'price': box_rec.price})
        return res

    @http.route('/order_processing', type='json', auth='user')
    def order_processing(self, barcode, **kw):

        # Comment when testing
        pick_id = request.env['stock.picking'].search([('name', '=', barcode), ('state', '=', 'assigned')], limit=1)

        # Uncomment when testing
        # pick_id = request.env['stock.picking'].search([('state', '=', 'assigned'), ('picking_type_id.name', '=', 'Pick'), ('name', '=', 'WH/PICK/37812')], limit=1)
        # pick_id = request.env['stock.picking'].browse(479416)

        if pick_id:
            # Find total sale amount and product cost of pick
            total_sale_price = 0
            total_product_cost = 0
            for m in pick_id.move_lines:
                total_sale_price += m.procurement_id.sale_line_id.price_total
                total_product_cost += sum(q.qty * q.cost for q in m.reserved_quant_ids)

            ops = []
            barcodes = []
            for p in pick_id.pack_operation_product_ids:
                barcodes.append(p.product_id.barcode)
                ops.append({
                    'id': p.id,
                    'product': p.product_id.name,
                    'mfg_label': p.mfg_label,
                    'qty_to_do': p.product_qty,
                    'qty_done': p.qty_done,
                    'location': p.from_loc,
                    'barcode': p.product_id.barcode
                })
            packages = []
            if pick_id.replacement_return_id:
                ship_id = pick_id.replacement_return_id.replacement_picking_ids.filtered(lambda x: x.picking_type_id.name == 'Replacement' and x.state != 'cancel')
                if len(ship_id) > 1:
                    raise UserError('More than 1 shipping pickings for replacement')
            else:
                ship_id = request.env['stock.picking'].search([('group_id', '=', pick_id.group_id.id), ('picking_type_id.require_packaging', '=', True)], limit=1)

            for l in ship_id.packaging_line_ids:
                packages.append({'name': l.packaging_product_id.name,
                                 'quantity': l.quantity,
                                 'barcode': l.packaging_product_id.barcode,
                                 'packaging_product_id': l.packaging_product_id.id,
                                 'id': l.packaging_product_id.product_tmpl_id.id})
            return {
                'name': pick_id.name,
                'store': pick_id.store_id.name,
                'site': pick_id.store_id.site,
                'order': pick_id.sale_id.name if pick_id.sale_id else pick_id.replacement_return_id.name,
                'ops': ops,
                'barcodes': barcodes,
                'carrier': ship_id.carrier_id.name,
                'service': ship_id.service_id.name,
                'rate': ship_id.rate,
                'packaging_not_required': pick_id.packaging_not_required,
                'packages': packages,
                'tracking_lines': [],
                'ship_id': ship_id.id,
                'length': ship_id.length or 0,
                'width': ship_id.width or 0,
                'height': ship_id.height or 0,
                'weight': ship_id.weight or 0,
                'total_sale_price': total_sale_price,
                'total_product_cost': total_product_cost
            }
        else:
            return {'warning': _('No picking corresponding to barcode %(barcode)s') % {'barcode': barcode}}

    @http.route('/reports/wh_margins', type='http', auth="user")
    def wh_margins_report(self, **post):
        wizard_id = request.env['stock.wh.margins.report.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') +timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

        ebay_fees = {'visionary': 0.1051, 'revive': 0.1103, 'rhino': 0.1303, 'ride': 0.0847}
        paypal_fee = 0.0215

        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = [
            'SO Number', 'Web Order ID', 'Buyer', 'State', 'City', 'Street', 'PO', 'Vendor', 'Store', 'Carrier', 'Order Type',
            'Processed Date', 'Processed By', 'Part Numbers', 'Qty', 'Sale Price',
            'Product Cost', 'Landed Cost', 'Total Cost', 'Box Cost',
            'Computed Shipping Cost', 'Actual Shipping Cost', 'Fee', 'Tax %', 'Tax', 'Margin'
        ]
        writer.writerow([name.encode('utf-8') for name in columns])

        sql = ("""SELECT   pick.id, SO.name AS sale_order, SO.amz_order_type, SO.web_order_id, SO.fba_commission, SO.fba_fulfillment_fee, so.amount_tax,
                           SO_PARTNER.name buyer, SO_PARTNER.city,SO_PARTNER.street, st.name partner_state, STORE.site AS site, STORE.code AS code,
                           STORE.name AS store, sc.name AS carrier, PICK.processed_date, PARTNER.name AS processed_by,
                           PICK_GROUP.part_numbers, PICK_GROUP.qty, PICK_GROUP.sale_price, PICK_GROUP.product_cost, PICK_GROUP.landed_cost,
                           PICK_GROUP.total_cost, PICK_GROUP.TAX, PICK_GROUP.PO, PICK_GROUP.VENDOR, PICK_GROUP.QUANT_IDS, PICK_GROUP.MOVE_IDS,
                           (CASE WHEN BOX.box_cost > 0 THEN BOX.box_cost ELSE 0 END) AS box_cost, PICK_SHIP.computed_wh_shipping_cost,
                           PICK_SHIP.actual_pick_shipping_price
                FROM stock_picking PICK
                left join ship_carrier sc on PICK.carrier_id = sc.id
                LEFT JOIN stock_picking_type PTYPE on PTYPE.id = PICK.picking_type_id
                LEFT JOIN sale_order SO on SO.id = PICK.sale_id
                LEFT JOIN (SELECT  PICK.id,
                                   string_agg(PT.part_number, ',') as part_numbers,
                                   SUM(MOVE.product_qty) as qty,
                                   SUM(SOL.price_total) as sale_price,
                                   SUM(QUANT_RES.product_cost) as product_cost,
                                   SUM(QUANT_RES.landed_cost) as landed_cost,
                                   SUM(QUANT_RES.total_cost) as total_cost,
                                   string_agg(distinct QUANT_RES.PO, ',') as PO,
                                   string_agg(distinct QUANT_RES.VENDOR, ',') as VENDOR,
                                   string_agg(QUANT_RES.QUANT_IDS::text, ',') as QUANT_IDS,
                                   string_agg(QUANT_RES.MOVE_IDS::text, ',') as MOVE_IDS,
                                   string_agg(at.amount::text, ',') as TAX
                           FROM stock_picking PICK
                           LEFT JOIN stock_move MOVE ON MOVE.picking_id = PICK.id
                           LEFT JOIN product_product PP ON PP.id = MOVE.product_id
                           LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                           LEFT JOIN
                           (select move_id as move_id,
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
                                          QUANT.cost as total_cost
                                  FROM stock_move MOVE
                                  LEFT JOIN stock_quant_move_rel MQREL on MQREL.move_id = MOVE.id
                                  LEFT JOIN stock_quant QUANT on QUANT.id = MQREL.quant_id
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
                                 group by move_id
                           ) as QUANT_RES on QUANT_RES.move_id = MOVE.id
                           LEFT JOIN procurement_order PROC on PROC.id = MOVE.procurement_id
                           LEFT JOIN sale_order_line SOL on SOL.id = PROC.sale_line_id
                           left join account_tax_sale_order_line_rel tax_id on tax_id.sale_order_line_id = sol.id
                           left join account_tax at on tax_id.account_tax_id = at.id
                           WHERE MOVE.state = 'done'
                           GROUP BY PICK.id
                           ) as PICK_GROUP ON PICK_GROUP.id = PICK.id
                LEFT JOIN (
                                SELECT PICK.id, SUM(PICK.rate + PICK.rate * (CASE WHEN TLINES.count > 0 THEN TLINES.count ELSE 0 END)) as computed_wh_shipping_cost,
                                SUM(
                                    (CASE WHEN RECPICK.actual_pick_shipping_price > 0 THEN RECPICK.actual_pick_shipping_price ELSE 0 END)
                                    + (CASE WHEN TLINES.actual_tline_shipping_price > 0 THEN TLINES.actual_tline_shipping_price ELSE 0 END)
                                ) as actual_pick_shipping_price
                                FROM stock_picking PICK
                                LEFT JOIN
                                (
                                    SELECT PICK.id as pick_id, SUM(RECSHIP.shipping_price) as actual_pick_shipping_price
                                    FROM purchase_shipping_recon_line RECSHIP
                                    LEFT JOIN stock_picking PICK ON PICK.id = RECSHIP.pick_id
                                    GROUP BY PICK.id
                                ) as RECPICK on PICK.id = RECPICK.pick_id
                                LEFT JOIN
                                (
                                    SELECT PICK.id as pick_id, COUNT(*) as count, SUM(RECSHIPLINES.shipping_price) as actual_tline_shipping_price
                                    FROM stock_picking_tracking_line TLINE
                                    LEFT JOIN (
                                        SELECT TLINE.id, SUM(RECSHIP.shipping_price) as shipping_price
                                        FROM purchase_shipping_recon_line RECSHIP
                                        LEFT JOIN stock_picking_tracking_line TLINE ON TLINE.id = RECSHIP.tracking_line_id
                                        GROUP BY TLINE.id
                                    ) as RECSHIPLINES on RECSHIPLINES.id = TLINE.id
                                    LEFT JOIN stock_picking PICK ON PICK.id = TLINE.picking_id
                                    GROUP BY PICK.id
                                ) as TLINES ON PICK.id = TLINES.pick_id
                                GROUP BY PICK.id
                            ) as PICK_SHIP ON PICK_SHIP.id = PICK.id
                LEFT JOIN (
                                SELECT PICK.id, SUM(PRICELIST.price * BOXLINE.quantity) as box_cost
                                FROM stock_picking PICK
                                LEFT JOIN stock_picking_packaging_line BOXLINE ON BOXLINE.picking_id = PICK.id
                                LEFT JOIN product_product PP ON BOXLINE.packaging_product_id = PP.id
                                LEFT JOIN product_template PT on PT.id = PP.product_tmpl_id
                                LEFT JOIN product_supplierinfo PRICELIST ON PRICELIST.product_tmpl_id = PT.id
                                GROUP BY PICK.id
                            ) as BOX on BOX.id = PICK.id
                LEFT JOIN sale_store STORE ON STORE.id = SO.store_id
                LEFT JOIN res_users U ON U.id = PICK.processed_by_uid
                LEFT JOIN res_partner PARTNER ON U.partner_id = PARTNER.id
                LEFT JOIN res_partner SO_PARTNER ON SO.partner_id = SO_PARTNER.id
                LEFT JOIN res_country_state st on SO_PARTNER.state_id = st.id
                WHERE PICK.state = 'done' AND PTYPE.name = 'Delivery Orders'
                AND PICK.delivery_return_id IS NULL
                AND SO.id is not NULL
                AND pick.sale_id is not NULL
                AND PICK.processed_date >= %s AND PICK.processed_date < %s
                ORDER BY SO.name
        """)
        params = [from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            fee = 0
            if res['site'] == 'ebay':
                if res['code'] in ebay_fees:
                    fee = 0.03 + (ebay_fees[res['code']] + paypal_fee) * res['sale_price']
                else:
                    fee = 0.03 + (0.11 + paypal_fee) * res['sale_price']
            else:
                if res['amz_order_type'] == 'fba':
                    fee = res['fba_commission'] + res['fba_fulfillment_fee']
                else:
                    try:
                        fee = max(1.00, 0.12 * res['sale_price'])
                    except Exception as e:
                        _logger.error(res)
                        _logger.error(e)
            computed_wh_shipping_cost = res['computed_wh_shipping_cost'] if res['computed_wh_shipping_cost'] > 0 else 0
            actual_pick_shipping_price = res['actual_pick_shipping_price'] if res['actual_pick_shipping_price'] > 0 else 0
            final_shipping_cost = actual_pick_shipping_price if actual_pick_shipping_price > 0 else computed_wh_shipping_cost
            margin = res['sale_price'] - fee - res['box_cost'] - res['total_cost'] - final_shipping_cost - res['amount_tax'] or 0
            try:
                row = [
                    res['sale_order'],
                    res['web_order_id'],
                    res['buyer'].encode('utf8'),
                    res['partner_state'].encode('utf8'),
                    res['city'].encode('utf8'),
                    res['street'].encode('utf8'),
                    res['po'],
                    res['vendor'],
                    res['store'],
                    res['carrier'],
                    res['amz_order_type'],
                    res['processed_date'],
                    res['processed_by'],
                    res['part_numbers'],
                    res['qty'],
                    '{0:,.2f}'.format(res['sale_price'] or 0),
                    '{0:,.2f}'.format(res['product_cost'] or 0),
                    '{0:,.2f}'.format(res['landed_cost'] or 0),
                    '{0:,.2f}'.format(res['total_cost'] or 0),
                    '{0:,.2f}'.format(res['box_cost'] or 0),
                    '{0:,.2f}'.format(res['computed_wh_shipping_cost'] or 0),
                    '{0:,.2f}'.format(res['actual_pick_shipping_price'] or 0),
                    '{0:,.2f}'.format(fee),
                    res['tax'],
                    '{0:,.2f}'.format(res['amount_tax'] or 0),
                    '{0:,.2f}'.format(margin),
                ]
                writer.writerow(row)
            except Exception as e:
                logging.error(e)
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'wh_margins_report_%s_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])
