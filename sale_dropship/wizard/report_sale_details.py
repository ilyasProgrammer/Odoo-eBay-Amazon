# -*- coding: utf-8 -*-
import base64
import csv
from cStringIO import StringIO
from odoo import api, fields, models, _
import logging

_log = logging.getLogger(__name__)

class Output(models.Model):
    _name = 'output'

    name = fields.Char(string='Name', size=256)
    csv_output = fields.Binary(string='CSV output', readonly=True)


class ReportSaleDetails(models.TransientModel):
    _name = 'report.sale.details'

    from_so = fields.Char(string="From SO", required=True)
    to_so = fields.Char(string="To SO", required=True)

    @api.multi
    def print_report(self):
        SaleOrder = self.env['sale.order']
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Sale Order', 'Store', 'Web Order', 'Customer', 'Purchase Order', 'Vendor', 'Vendor Order ID', 'Tracking Number', 'Carrier', 'Service']
        writer.writerow([name.encode('utf-8') for name in columns])
        from_so = SaleOrder.search([('name', '=', self.from_so)], limit=1).id or 0
        to_so = SaleOrder.search([('name', '=', self.to_so)], limit=1).id or 0
        for order in SaleOrder.search([('id', '>=', from_so), ('id', '<=', to_so)]).sorted(key=lambda r: r.id):
            picking = order.picking_ids.filtered(lambda x: x.picking_type_id.id == x.warehouse_id.out_type_id.id)
            row = [
                order.name or '',
                order.store_id.name or '',
                order.web_order_id or '',
                order.partner_id.name.encode('ascii', 'ignore') or '',
                order.purchase_order_id.name or '',
                order.purchase_order_id.partner_id.name or '',
                order.purchase_order_id.vendor_order_id or '',
                picking[-1].tracking_number if picking and picking[-1].tracking_number else '',
                picking[-1].carrier_id.name if picking and picking[-1].carrier_id else '',
                picking[-1].service_id.name if picking and picking[-1].service_id else '',
            ]
            try:
                writer.writerow(row)
            except Exception as e:
                _log.error(e)
                _log.error(order)
        fp.seek(0)
        data = fp.read()
        fp.close()
        self.env.cr.execute(""" DELETE FROM output""")
        attach_id = self.env['output'].create({'name': 'Sale Details.csv', 'csv_output': base64.encodestring(data)})
        return {
            'name': _('Notification'),
            'context': self.env.context,
            'view_id': self.env.ref('sale_dropship.csv_output_view').id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'output',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
