# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
from cStringIO import StringIO

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
from odoo.addons.purchase_more_details.controllers.main import PurchaseReports

class PurchaseReportsExtension(PurchaseReports):

    @http.route()
    def rfq_report(self, **post):
        po_id = request.env['purchase.order'].browse([int(post.get('id'))])
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        if po_id.use_non_auto_supplies_layout:
            columns = ['Description', 'Qty']
            rows = po_id.get_non_auto_rfq_lines()
        else:
            columns = ['LAD Part Number', 'Vendor Code', 'Partslink', 'Description', 'Qty', 'Unit Price', 'Subtotal']
            rows = po_id.get_rfq_lines()
        writer.writerow([name.encode('utf-8') for name in columns])
        for row in rows:
            writer.writerow(row)
        fp.seek(0)
        data = fp.read()
        fp.close()

        valid_fname = '%s.csv' %(po_id.name)
        return request.make_response(data,
                [('Content-Type', 'text/csv'),('Content-Disposition', content_disposition(valid_fname))])
