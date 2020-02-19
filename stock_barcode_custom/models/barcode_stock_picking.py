# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import json

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        if not self.picking_type_id.barcode_nomenclature_id:
            # Logic for products
            actual_barcode = barcode
            barcode = barcode.replace("-", "").replace("\n","")
            add_qty = 1
            product = self.env['product.product'].search(['|', ('barcode', '=', barcode), ('partslink', '=', barcode),('mfg_code', '=', 'ASE')], limit=1)
            if not product:
                product = self.env['product.product'].search([('barcode_case', '=', barcode),('mfg_code', '=', 'ASE')], limit=1)
                add_qty = product.qty_case
            if not product:
                product = self.env['product.product'].search([('barcode_inner_case', '=', barcode),('mfg_code', '=', 'ASE')], limit=1)
                add_qty = product.qty_inner_case
            if not product:
                add_qty = 1
                alt_product = self.env['product.product'].search(['|', ('barcode', '=', barcode), ('partslink', '=', barcode)], limit=1)
                if not alt_product:
                    alt_product = self.env['product.product'].search([('barcode_case', '=', barcode)], limit=1)
                    add_qty = alt_product.qty_case
                if not alt_product:
                    alt_product = self.env['product.product'].search([('barcode_inner_case', '=', barcode)], limit=1)
                    add_qty = alt_product.qty_inner_case
                if alt_product:
                    ase_product = alt_product.alternate_ids.filtered(lambda r: r.mfg_code == 'ASE')
                    if ase_product:
                        product = ase_product[0]
                    else:
                        product = alt_product
                    barcode = product.barcode
            if not product:
                add_qty = 1
                supplierinfo = self.env['product.supplierinfo'].search([('barcode_unit', '=', barcode)], limit=1)
                print supplierinfo
                if not supplierinfo:
                    supplierinfo = self.env['product.supplierinfo'].search([('barcode_case', '=', barcode)], limit=1)
                    add_qty = supplierinfo.qty_case
                if not supplierinfo:
                    supplierinfo = self.env['product.supplierinfo'].search([('barcode_inner_case', '=', barcode)], limit=1)
                    add_qty = supplierinfo.qty_inner_case
                if supplierinfo:
                    if supplierinfo.product_tmpl_id.mfg_code == 'ASE':
                        product = supplierinfo.product_tmpl_id.product_variant_id
                    else:
                        ase_product_tmpl = supplierinfo.product_tmpl_id.alternate_ids.filtered(lambda r: r.mfg_code == 'ASE')
                        if ase_product:
                            product = ase_product_tmpl[0].product_variant_id
                        else:
                            product = supplierinfo.product_tmpl_id.product_id

                    barcode = product.barcode
            # JAMES CODE -- END

            barcode = actual_barcode
            
            if product:
                if self._check_product(product, qty=add_qty):
                    return

            # Logic for packages in source location
            if self.pack_operation_pack_ids:
                package_source = self.env['stock.quant.package'].search([('name', '=', barcode), ('location_id', 'child_of', self.location_id.id)], limit=1)
                if package_source:
                    if self._check_source_package(package_source):
                        return

            # Logic for packages in destination location
            package = self.env['stock.quant.package'].search([('name', '=', barcode), '|', ('location_id', '=', False), ('location_id','child_of', self.location_dest_id.id)], limit=1)
            if package:
                if self._check_destination_package(package):
                    return

            # Logic only for destination location
            location = self.env['stock.location'].search(['|', ('name', '=', barcode), ('barcode', '=', barcode)], limit=1)
            if location and location.parent_left < self.location_dest_id.parent_right and location.parent_left >= self.location_dest_id.parent_left:
                if self._check_destination_location(location):
                    return
        else:
            parsed_result = self.picking_type_id.barcode_nomenclature_id.parse_barcode(barcode)
            if parsed_result['type'] in ['weight', 'product']:
                if parsed_result['type'] == 'weight':
                    product_barcode = parsed_result['base_code']
                    qty = parsed_result['value']
                else: #product
                    product_barcode = parsed_result['code']
                    qty = 1.0
                product = self.env['product.product'].search(['|', ('barcode', '=', product_barcode), ('default_code', '=', product_barcode)], limit=1)
                if product:
                    if self._check_product(product, qty):
                        return

            if parsed_result['type'] == 'package':
                if self.pack_operation_pack_ids:
                    package_source = self.env['stock.quant.package'].search([('name', '=', parsed_result['code']), ('location_id', 'child_of', self.location_id.id)], limit=1)
                    if package_source:
                        if self._check_source_package(package_source):
                            return
                package = self.env['stock.quant.package'].search([('name', '=', parsed_result['code']), '|', ('location_id', '=', False), ('location_id','child_of', self.location_dest_id.id)], limit=1)
                if package:
                    if self._check_destination_package(package):
                        return

            if parsed_result['type'] == 'location':
                location = self.env['stock.location'].search(['|', ('name', '=', parsed_result['code']), ('barcode', '=', parsed_result['code'])], limit=1)
                if location and location.parent_left < self.location_dest_id.parent_right and location.parent_left >= self.location_dest_id.parent_left:
                    if self._check_destination_location(location):
                        return

        return {'warning': {
            'title': _('Wrong barcode'),
            'message': _('The barcode "%(barcode)s" doesn\'t correspond to a proper product, package or location.') % {'barcode': barcode}
        }}