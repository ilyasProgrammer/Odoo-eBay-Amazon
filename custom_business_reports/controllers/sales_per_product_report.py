# -*- coding: utf-8 -*-

import csv
from pytz import timezone
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from calendar import monthrange
from cStringIO import StringIO
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
import logging

_logger = logging.getLogger(__name__)


class SalesPerProductReport(http.Controller):

    @http.route('/reports/sales_per_product', type='http', auth="user")
    def sales_per_product_report(self, **post):
        wizard_id = request.env['sales.per.product.wizard'].browse([int(post.get('id'))])
        #current_period_start = datetime.strptime(wizard_id.period_start + ' 00:00:00' , '%Y-%m-%d %H:%M:%S')
        current_period_start = str_to_utc(wizard_id.period_start + ' 00:00:00')
        if wizard_id.grouping_criteria == 'day':
            current_period_start = str_to_utc(wizard_id.period_start + ' 00:00:00')
            current_period_end = current_period_start + timedelta(days=1)
            previous_period_start = current_period_start + timedelta(days=-1)
        if wizard_id.grouping_criteria == 'week':
            current_period_start = str_to_utc(wizard_id.period_start + ' 00:00:00')
            current_period_start = current_period_start + timedelta(days=-current_period_start.weekday())
            current_period_end = current_period_start + timedelta(weeks=1)
            previous_period_start = current_period_start + timedelta(weeks=-1)
        if wizard_id.grouping_criteria == 'month':
            current_period_start = str_to_utc(wizard_id.period_start + ' 00:00:00')
            current_period_start = dt_to_utc(datetime(current_period_start.year, current_period_start.month, 1, 0, 0, 0))
            last_day_of_month = monthrange(current_period_start.year, current_period_start.month)[1]
            current_period_end = dt_to_utc(datetime(current_period_start.year, current_period_start.month, last_day_of_month))
            previous_period_last_day = current_period_start + timedelta(days=-1)
            previous_period_start = dt_to_utc(datetime(previous_period_last_day.year, previous_period_last_day.month, 1, 0, 0, 0))
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['LAD', 'Previous Period', 'Current Period', 'Drop Percentage']
        writer.writerow([name.encode('utf-8') for name in columns])
        products = {}
        current_period_sales = request.env['sale.order'].search([('state', 'in', ['sale', 'done']), ('date_order', '>=', current_period_start.strftime('%Y-%m-%d %H:%M:%S')), ('date_order', '<=', current_period_end.strftime('%Y-%m-%d %H:%M:%S'))])
        previous_period_sales = request.env['sale.order'].search([('state', 'in', ['sale', 'done']), ('date_order', '>=', previous_period_start.strftime('%Y-%m-%d %H:%M:%S')), ('date_order', '<', current_period_start.strftime('%Y-%m-%d %H:%M:%S'))])
        for sale in current_period_sales:
            for line in sale.order_line:
                if products.get(line.product_id.id):
                    products[line.product_id.id]['current_sales'] += int(line.product_uom_qty)
                else:
                    products[line.product_id.id] = { 
                        'lad': line.product_id.name,
                        'current_sales': int(line.product_uom_qty),
                        'previous_sales': 0
                    }
        for sale in previous_period_sales:
            for line in sale.order_line:
                if products.get(line.product_id.id):
                    products[line.product_id.id]['previous_sales'] += int(line.product_uom_qty)
                else:
                    products[line.product_id.id] = { 
                        'lad': line.product_id.name,
                        'previous_sales': int(line.product_uom_qty),
                        'current_sales': 0
                    }
        min_drop_percentage = wizard_id.drop_percentage
        for id, data in products.items():
            drop_percentage = ((data['previous_sales'] - data['current_sales']) * 100 / data['previous_sales'] ) \
                if data['previous_sales'] else 0
            if drop_percentage >= min_drop_percentage:
                writer.writerow([
                    data['lad'],
                    data['previous_sales'],
                    data['current_sales'],
                    drop_percentage,
                ])
        fp.seek(0)
        data = fp.read()
        fp.close()
        valid_fname = 'sales_per_product_%s_%s%s_%s.csv' % (current_period_start, wizard_id.drop_percentage, chr(37), wizard_id.grouping_criteria)
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])


def str_to_utc(sdt):
    return timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc'))


def dt_to_utc(dt):
    return timezone('US/Eastern').localize(dt).astimezone(timezone('utc'))
