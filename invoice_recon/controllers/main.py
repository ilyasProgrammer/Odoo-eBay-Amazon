# -*- coding: utf-8 -*-

import csv

from cStringIO import StringIO

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition


class InvoiceReconController(http.Controller):

    @http.route('/reports/recon', type='http', auth="user")
    def download_recon_summary(self, **post):
        recon_id = request.env['purchase.recon'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['PO Reference',
            'Vendor PO Reference',
            'Product Price',
            'Shipping Price',
            'Handling Price',
            'Total Price',
            'Expected Price',
            'Status',
            'Variance',
            'Note'
        ]
        writer.writerow([name.encode('utf-8') for name in columns])

        recon_line_ids = recon_id.recon_line_ids
        for l in recon_line_ids:
            writer.writerow([
                l.name,
                l.vendor_ref,
                l.product_price,
                l.shipping_price,
                l.handling_price,
                l.total_price,
                l.purchase_order_id.amount_total or 0,
                l.state,
                l.variance,
                l.note or ''
            ])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s_recon_report.csv' %(recon_id.name)
        return request.make_response(data,
            [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/purchase_shipping_recon', type='http', auth="user")
    def download_purchase_shipping_recon_summary(self, **post):
        recon_id = request.env['purchase.shipping.recon'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['tracking_number',
                   'shipping_price',
                   'pick_id',
                   'variance',
                   'state',
                   'carrier_id',
                   ]
        writer.writerow([name.encode('utf-8') for name in columns])

        recon_line_ids = recon_id.recon_line_ids
        for l in recon_line_ids:
            writer.writerow([
                l.tracking_number,
                l.shipping_price,
                l.pick_id.name,
                l.variance,
                l.state,
                l.carrier_id.name
            ])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s_purchase_shipping_recon.csv' % recon_id.name
        return request.make_response(data, [('Content-Type', 'text/csv'), ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/ebay_recon', type='http', auth="user")
    def download_ebay_recon_summary(self, **post):
        recon_id = request.env['ebay.recon'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Store',
                   'eBay Record',
                   'Product Price',
                   'Opsyst Amount',
                   'Status',
                   'Variance']
        writer.writerow([name.encode('utf-8') for name in columns])

        recon_line_ids = recon_id.recon_line_ids
        for l in recon_line_ids:
            writer.writerow([
                l.store_id.code,
                l.name,
                round(l.price, 2),
                round(l.sale_order_id.amount_total, 2),
                round(l.variance, 2),
                l.state
            ])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s_ebay_recon_report.csv' % recon_id.name
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])

    @http.route('/reports/amazon_recon', type='http', auth="user")
    def download_amazon_recon_summary(self, **post):
        recon_id = request.env['amazon.recon'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Store',
                   'Web ID',
                   'Product Price',
                   'Opsyst Amount',
                   'Fee',
                   'Status',
                   'Fee Variance',
                   'Variance']
        writer.writerow([name.encode('utf-8') for name in columns])

        recon_line_ids = recon_id.recon_line_ids
        for l in recon_line_ids:
            writer.writerow([
                l.store_id.code,
                l.name,
                round(l.price, 2),
                round(l.sale_order_id.amount_total, 2),
                round(l.fee, 2),
                l.state,
                round(l.fee_variance, 2),
                round(l.variance, 2),
            ])
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s_amazon_recon_report.csv' % recon_id.name
        return request.make_response(data, [('Content-Type', 'text/csv'),
                                            ('Content-Disposition', content_disposition(valid_fname))])
