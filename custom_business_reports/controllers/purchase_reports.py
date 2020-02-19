# -*- coding: utf-8 -*-

import csv
from cStringIO import StringIO
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
import logging

_logger = logging.getLogger(__name__)


class PurchaseReports(http.Controller):

    @http.route('/reports/po_international_diff', type='http', auth="user")
    def po_international_diff(self, **post):
        wizard_id = request.env['po.international.diff.wizard'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['PO', 'Vendor', 'Date', 'LAD', 'Cost', 'Ordered Qty', 'Received Qty', 'Qty Drop',  'Ordered Cost', 'Received Cost', 'Cost Drop']
        writer.writerow([name.encode('utf-8') for name in columns])
        sql = ("""SELECT PO.name, rp.name as vendor, DATE(PO.date_order) as date_order, pp.part_number as lad, pol.price_unit as cost, pol.product_qty as ordered_qty,
                           pol.qty_received as received_qty, (pol.product_qty - pol.qty_received) as qty_drop,
                           pol.product_qty*pol.price_unit as ordered_cost,
                           pol.qty_received*pol.price_unit as received_cost,
                           (pol.product_qty - pol.qty_received)*pol.price_unit as cost_drop
                    FROM purchase_order_line POL
                    LEFT JOIN purchase_order PO ON POL.order_id = PO.id
                    LEFT JOIN product_product pp ON pp.id = POL.product_id
                    LEFT JOIN res_partner rp on PO.partner_id = rp.id
                    where PO.state in ('purchase','done') and po.dest_address_id is NULL and (rp.is_domestic is NULL or rp.is_domestic = FALSE)
                    order by PO.id, pol.id""")
        cr = request.env.cr
        cr.execute(sql)
        results = cr.dictfetchall()
        total_qty_diff = 0
        total_cost_diff = 0
        for res in results:
            writer.writerow([res['name'],
                             res['vendor'],
                             res['date_order'],
                             res['lad'],
                             res['cost'],
                             res['ordered_qty'],
                             res['received_qty'],
                             res['qty_drop'],
                             res['ordered_cost'],
                             res['received_cost'],
                             res['cost_drop'],
                             ])
            total_qty_diff += int(res['qty_drop'])
            total_cost_diff += float(res['received_cost'])
        total_orders = len(set([r['name'] for r in results]))
        writer.writerow([''])
        writer.writerow(['TOTAL Orders', total_orders])
        writer.writerow(['TOTAL Qty Drop', total_qty_diff])
        writer.writerow(['TOTAL Cost Drop', total_cost_diff])
        writer.writerow([''])
        writer.writerow(['Qty Drop shows how much less units WH received.'])
        writer.writerow(['Cost Drop shows how much less WH received.'])
        writer.writerow(['Negative value means WH received more that was ordered.'])

        fp.seek(0)
        data = fp.read()
        fp.close()

        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition('po_international_diff.csv'))])
