# -*- coding: utf-8 -*-

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


def dt_to_utc(sdt):
    return timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')


class ReturnsReports(http.Controller):

    @http.route('/reports/return_scrap', type='http', auth="user")
    def return_scrap(self, **post):
        wizard_id = request.env['return.scrap.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Date', 'SO', 'LAD', 'ID', 'Store', 'Cost']
        writer.writerow([name.encode('utf-8') for name in columns])
        sql = ("""SELECT sm.date as date_done,
                         so.name,
                         pp.part_number,
                         so.web_order_id,
                         ss.name as store_name,
                         sm.product_qty * sm.price_unit as cost
                  FROM sale_return sr
                  LEFT JOIN stock_picking sp ON sr.id = sp.receipt_return_id
                  LEFT JOIN stock_move sm ON sm.picking_id = sp.id
                  LEFT JOIN sale_order so ON sr.sale_order_id = so.id
                  LEFT JOIN sale_store ss ON so.store_id = ss.id
                  LEFT JOIN product_product pp ON sm.product_id = pp.id
                            WHERE sp.state ='done' 
                            AND sm.scrapped IS TRUE 
                            AND sm.date >= %s AND sm.date <= %s 
                            ORDER BY sm.date""")
        params = [from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            writer.writerow([res['date_done'],
                             res['name'],
                             res['part_number'],
                             res['web_order_id'],
                             res['store_name'],
                             res['cost']])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'return_scrap_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/return_percent', type='http', auth="user")
    def return_percent(self, **post):
        wizard_id = request.env['return.percent.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['LAD', 'Sales', 'WH returns', 'DS returns', 'Return %']
        writer.writerow([name.encode('utf-8') for name in columns])
        sql = ("""SELECT a.part_number as lad, a.SO,  c.WH, c.DS, round((c.WH+c.DS)*100/a.SO,0) as Percent, c.ret_ids
                    FROM (SELECT pp.part_number, SUM(sm.product_qty) SO
                     FROM sale_order so
                    LEFT JOIN stock_picking sp ON sp.sale_id = so.id
                    LEFT JOIN stock_move sm ON sm.picking_id = sp.id
                    LEFT JOIN product_product pp ON sm.product_id = pp.id
                    WHERE so.state IN ('sale', 'done') AND sp.picking_type_id in (4,6) and sm.date >= %s and sm.date <= %s and sp.state NOT IN ('draft', 'cancel')
                    GROUP BY pp.part_number
                    ORDER BY pp.part_number) as a
                    INNER JOIN (SELECT a.part_number,
                                      SUM(CASE WHEN b.picking_type_id = 4 THEN a.qty_done ELSE 0 END) as WH,
                                      SUM(CASE WHEN b.picking_type_id = 6 THEN a.qty_done ELSE 0 END) as DS,
                                      string_agg(a.sr_id::text, ',') as ret_ids FROM
                     (
                    SELECT pp.part_number, spo.qty_done, sr.id sr_id, sp.id, spo.id, so.id so_id
                    FROM sale_return sr
                    LEFT JOIN stock_picking sp ON sr.id = sp.receipt_return_id
                    LEFT JOIN stock_pack_operation spo ON spo.picking_id = sp.id
                    LEFT JOIN product_product pp ON spo.product_id = pp.id
                    LEFT JOIN sale_order so ON sr.sale_order_id = so.id
                    WHERE sp.state ='done'
                    and spo.date >= %s and spo.date <= %s ) a
                    LEFT JOIN(
                    SELECT pp.part_number, sp.id, spo.id, so.id so_id, sp.picking_type_id
                    FROM stock_picking sp
                    LEFT JOIN stock_pack_operation spo ON spo.picking_id = sp.id
                    LEFT JOIN product_product pp ON spo.product_id = pp.id
                    LEFT JOIN sale_order so ON sp.sale_id = so.id
                    WHERE  sp.picking_type_id IN (4, 6) and sp.state  NOT IN ('cancel', 'draft')) b
                    ON a.part_number = b.part_number AND a.so_id = b.so_id
                    GROUP BY a.part_number)  as c
                    on a.part_number = c.part_number WHERE c.WH+c.DS > 0 ORDER BY Percent DESC""")
        params = [from_date, to_date, from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            writer.writerow([res['lad'],
                             res['so'],
                             res['wh'],
                             res['ds'],
                             res['percent']])
        fp.seek(0)
        data = fp.read()
        fp.close()
        now = datetime.now().strftime('%Y%m%d%H%M%S')
        valid_fname = 'return_percent_%s.csv' % now
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