# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

import json

class stockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    
    product_barcodes = fields.Char(compute='_compute_product_barcodes')

    @api.depends('product_id')
    @api.multi
    def _compute_product_barcodes(self):
        print self
        for r in self:
            r.product_barcodes = (r.product_id.barcode + ',') if r.product_id.barcode else ''
            r.product_barcodes += (r.product_id.partslink + ',') if r.product_id.partslink else ''
            for alt in r.product_id.alternate_ids:
                r.product_barcodes += (alt.barcode + ',') if alt.barcode else ''
            for pl in r.product_id.product_tmpl_id.seller_ids:
                r.product_barcodes += (pl.barcode_unit + ',') if pl.barcode_unit else ''
                r.product_barcodes += (pl.barcode_inner_case + ',') if pl.barcode_inner_case else ''
                r.product_barcodes += (pl.barcode_case + ',') if pl.barcode_case else ''

class StockInventory(models.Model):
    _name = 'stock.inventory'
    _inherit = ['stock.inventory', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        actual_barcode = barcode
        barcode = barcode.replace("-", "").replace("\n","")
        _logger.info('Processing: %s' %barcode)
        add_qty = 1
        product = self.env['product.product'].search(['|', ('barcode', '=', barcode), ('partslink', '=', barcode), ('mfg_code', '=', 'ASE')], limit=1)
        _logger.info('Processing: %s' %product)
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
            if not supplierinfo:
                supplierinfo = self.env['product.supplierinfo'].search([('barcode_case', '=', barcode)], limit=1)
                add_qty = supplierinfo.qty_case
            if not supplierinfo:
                supplierinfo = self.env['product.supplierinfo'].search([('barcode_inner_case', '=', barcode)], limit=1)
                add_qty = supplierinfo.qty_inner_case
            if supplierinfo:
                product_id = supplierinfo.product_tmpl_id.product_variant_id
                if product_id.mfg_code == 'ASE':
                    product = product_id
                else:
                    ase_product = product_id.alternate_ids.filtered(lambda r: r.mfg_code == 'ASE')
                    if ase_product:
                        product = ase_product[0]
                    else:
                        product = product_id
                barcode = product.barcode
        if not product:
            barcode = barcode[:-1]
            product = self.env['product.product'].search([('barcode', '=', barcode), ('mfg_code', '=', 'ASE')], limit=1)
        if product:
            corresponding_line = self.line_ids.filtered(lambda r: r.product_id.barcode == barcode and (self.scan_location_id.id == r.location_id.id or not self.scan_location_id))
            if corresponding_line:
                corresponding_line[0].product_qty += add_qty
            else:
                quant_obj = self.env['stock.quant']
                company_id = self.company_id.id
                if not company_id:
                    company_id = self._uid.company_id.id
                dom = [('company_id', '=', company_id), ('location_id', '=', self.scan_location_id.id or self.location_id.id), ('lot_id', '=', False),
                            ('product_id','=', product.id), ('owner_id', '=', False), ('package_id', '=', False)]
                quants = quant_obj.search(dom)
                th_qty = sum([x.qty for x in quants])
                self.line_ids += self.line_ids.new({
                    'location_id': self.scan_location_id.id or self.location_id.id,
                    'product_id': product.id,
                    'product_uom_id': product.uom_id.id,
                    'theoretical_qty': th_qty,
                    'product_qty': add_qty,
                })
            return
        barcode = actual_barcode
        location = self.env['stock.location'].search([('barcode', '=', barcode)])
        if location:
            self.scan_location_id = location[0]
            return
