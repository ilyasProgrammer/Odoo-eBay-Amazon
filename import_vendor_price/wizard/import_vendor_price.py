# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import csv
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ImportVendorPrice(models.TransientModel):
    _name = 'import.vendor.price'

    data_file = fields.Binary(string='Price File', required=True)
    filename = fields.Char()

    def _create_update_infor(self, datas):
        ResPartner = self.env['res.partner']
        ProductTemplate = self.env['product.template']
        SupplierInfoObj = self.env['product.supplierinfo']
        counter = 0
        for data in datas:
            counter += 1
            if data.get('Vendor Name') == '' or data.get('Product Template') == '':
                continue
            _logger.info('Adding pricelist for %s %s: %s' %(counter, data.get('Vendor Name'), data.get('Product Template')))
            vendor = ResPartner.search([('name', '=', data['Vendor Name']), ('supplier', '=', True)], limit=1)
            if not vendor:
                raise UserError(_('No any vendor found of this name'))
            prod_template = ProductTemplate.search([('name', '=', data['Product Template'])], limit=1)
            if not prod_template:
                raise UserError(_('No any product found of this name'))
            vals = {
                'name': vendor.id,
                'product_tmpl_id': prod_template.id,
                'product_code': data['Vendor Product Code'],
                'product_name': data['Vendor Product Name'],
                'min_qty': data['Minimal Qty'],
                'price': data['Price'],
                'delay': data['Delivery Lead Time'],
                'cu_ft': data['Cubic Ft'],
                'barcode_unit': data['Unit Barcode'],
                'barcode_case': data['Case Barcode'],
                'qty_case': data['Case Quantity'],
                'barcode_inner_case': data['Inner Case Barcode'],
                'qty_inner_case': data['Inner Case Quantity'],
            }
            supplier_info = SupplierInfoObj.search([('name', '=', vendor.id), ('product_tmpl_id', '=', prod_template.id)])
            if supplier_info:
                supplier_info.write(vals)
            else:
                SupplierInfoObj.create(vals)

    @api.multi
    def import_file(self):
        self.ensure_one()
        if not self.filename.endswith('.csv'):
            raise UserError(_('Only csv file format is supported to import file'))
        data = csv.reader(StringIO(base64.b64decode(self.data_file)), quotechar='"', delimiter=',')
        # Read the column names from the first line of the file
        fields = data.next()
        datas = []
        for row in data:
            items = dict(zip(fields, row))
            datas.append(items)
        return self._create_update_infor(datas)
