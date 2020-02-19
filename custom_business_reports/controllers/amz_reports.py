# -*- coding: utf-8 -*-

import csv
from datetime import datetime, timedelta
import time
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
import logging
from pyexcel.cookbook import merge_all_to_a_book
from pytz import timezone
import os
import glob
import csv
from xlsxwriter.workbook import Workbook

_logger = logging.getLogger(__name__)


class AmazonReports(http.Controller):

    @http.route('/reports/amz_custom_report', type='http', auth="user")
    def amz_custom_report(self, **post):
        wizard_id = request.env['amz.custom.report.wizard'].browse([int(post.get('id'))])
        now = datetime.now()
        from_date = datetime.strptime(wizard_id.from_date, '%Y-%m-%d')
        to_date = datetime.strptime(wizard_id.to_date, '%Y-%m-%d')
        name = wizard_id['report_name']
        amz_store_id = request.env['sale.store'].search([('site', '=', 'amz')])[0]
        file_path = '/var/tmp/' + name + now.strftime('%Y-%m-%d') + '.csv'
        f = open(file_path, "w+")
        f.close()
        params = {'StartDate': from_date.strftime('%Y-%m-%d' + 'T' + '%H:%M:%S'),
                  'EndDate': to_date.strftime('%Y-%m-%d' + 'T' + '%H:%M:%S')}
        report_request_id = amz_store_id.amz_request_report(now, name, params)
        time.sleep(5)
        generated_report_id = amz_store_id.amz_get_status_of_report_request(now, report_request_id)
        if generated_report_id:
            amz_store_id.amz_get_report(now, generated_report_id, file_path)
            xls_file_name = '/var/tmp/' + name + now.strftime('%Y-%m-%d') + '.xlsx'
            # merge_all_to_a_book(glob.glob(file_path), xls_file_name)
            workbook = Workbook(xls_file_name)
            worksheet = workbook.add_worksheet()
            with open(file_path, 'rt') as f:
                reader = csv.reader(f, dialect="excel-tab")
                for r, row in enumerate(reader):
                    for c, col in enumerate(row):
                        worksheet.write(r, c, col)
            workbook.close()
            fp = open(xls_file_name, "r")
            data = fp.read()
            fp.close()
            return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(xls_file_name))])
        else:
            return "Canceled"


def dt_to_utc(sdt):
    return timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')
