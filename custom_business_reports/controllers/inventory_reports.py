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


class InventoryReports(http.Controller):

    @http.route('/reports/box_demand', type='http', auth="user")
    def box_demand(self, **post):
        wizard_id = request.env['box.demand.wizard'].browse([int(post.get('id'))])
        from_date = dt_to_utc(wizard_id.from_date + ' 04:00:00')
        to_date = (datetime.strptime(wizard_id.to_date + ' 04:00:00', '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['LAD', 'Box', 'Qty', 'Cost', 'Picks']
        writer.writerow([name.encode('utf-8') for name in columns])
        sql = ("""SELECT pt.name lad, pt.mfg_label box, sum(boxline.quantity) qty, sum(boxline.quantity * PRICELIST.price) as cost, 
                              string_agg(pick.name, ', ') picks
                              FROM stock_picking PICK
                              LEFT JOIN stock_picking_packaging_line BOXLINE ON BOXLINE.picking_id = PICK.id
                              LEFT JOIN product_product PP ON BOXLINE.packaging_product_id = PP.id
                              LEFT JOIN product_template PT ON PT.id = PP.product_tmpl_id
                              LEFT JOIN product_supplierinfo PRICELIST ON PRICELIST.product_tmpl_id = PT.id
                              LEFT JOIN sale_order so ON so.id = PICK.sale_id
                              WHERE sale_id IN (SELECT id
                                                FROM sale_order so
                                                WHERE SO.state IN ('sale', 'done')
                                                AND so.create_date >= %s AND so.date_order < %s)
                              AND BOXLINE.picking_id IS NOT NULL
                              AND PICK.picking_type_id IN (4, 11)
                              AND PICK.state = 'done'
                              GROUP BY pt.name, pt.mfg_label""")
        params = [from_date, to_date]
        cr = request.env.cr
        cr.execute(sql, params)
        results = cr.dictfetchall()
        for res in results:
            writer.writerow([res['lad'],
                             res['box'],
                             res['qty'],
                             res['cost'],
                             res['picks']])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = 'box_demand_%s_to_%s.csv' % (wizard_id.from_date, wizard_id.to_date)
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