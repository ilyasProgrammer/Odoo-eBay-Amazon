# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import openpyxl
import tempfile
import base64
import csv
import string
from datetime import datetime
import binascii

_logger = logging.getLogger(__name__)

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ImportTaxJarTaxes(models.TransientModel):
    _name = 'import.taxjar.taxes'

    data_file = fields.Binary(string='File', required=True)
    filename = fields.Char()

    @api.multi
    def import_file(self):
        if not self.filename.endswith('.csv'):
            raise UserError('Only csv file format is supported to import')
        # fp = tempfile.NamedTemporaryFile(suffix=".csv")
        # fp.write(binascii.a2b_base64(self.data_file))
        # fp.seek(0)
        # _logger.info('Temp file created')
        # with open(fp.name) as f:
        #     reader = csv.reader(f, skipinitialspace=True)
        #     header = next(reader)
        #     data = [dict(zip(header, map(str, row))) for row in reader]
        data = csv.reader(StringIO(base64.b64decode(self.data_file)), quotechar='"', delimiter=',')
        # Read the column names from the first line of the file
        fields = data.next()
        datas = []
        for row in data:
            items = dict(zip(fields, row))
            datas.append(items)
        _logger.info('File loaded to dict')
        cnt_found = 0
        cnt_not_found = 0
        cnt_total = 0
        report = 'Execution report: \n'
        _logger.info('Started data process')
        data_size = len(datas)
        for r in datas:
            cnt_total += 1
            _logger.info('Iteration %s of %s', cnt_total, data_size)
            if r['provider'] == 'amazon':
                sos = self.env['sale.order'].search([('web_order_id', '=', r['order_id']), ('state', 'in', ['sale', 'done'])])
            elif r['provider'] == 'paypal':
                sos = self.env['sale.order'].search([('paypal_transaction', '=', r['order_id']), ('state', 'in', ['sale', 'done'])])
            if not sos:
                msg = 'Cant find SO: %s\n' % r
                _logger.warning(msg)
                report += msg
                cnt_not_found += 1
            else:
                cnt_found += 1
                for so in sos:
                    so.taxjar_tax = float(r['sales_tax'])
                    so.taxjar_total = float(r['total_sale'])
                    msg = 'TaxJar Data loaded: %s %s %s\n' % (so.id, r['sales_tax'], r['total_sale'])
                    _logger.info(msg)
                    report += msg
        final_report = 'Mapped: %s\nNot mapped: %s\nTotal: %s\n\n' % (cnt_found, cnt_not_found, cnt_total) + report
        return {
            'name': 'Report TaxJar Taxes Import',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.message',
            'target': 'new',
            'context': {'default_text': final_report}
        }

    @api.model
    def excel_to_dict(self, excel_path, headers=[]):
        wb = openpyxl.load_workbook(excel_path)
        sheet = wb.worksheets[0]
        result_dict = []
        for row in range(2, sheet.max_row + 1):
            line = dict()
            for col, header in enumerate(headers):
                # cell_value = sheet[self.index_to_col(headers.index(header)) + str(row)].value
                try:
                    cell_value = sheet['A' + str(row)].value.split(',')[col]  # They have strange format. All data in single column
                except:
                    continue
                if type(cell_value) is unicode:
                    cell_value = cell_value.encode('utf-8').decode('ascii', 'ignore')
                    cell_value = cell_value.strip()
                elif type(cell_value) is int:
                    cell_value = str(cell_value)
                elif cell_value is None:
                    cell_value = ''
                line[header] = cell_value
            result_dict.append(line)
        return result_dict

    @api.model
    def index_to_col(self, index):
        return string.uppercase[index]
