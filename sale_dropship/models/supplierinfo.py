# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp

class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    cu_ft = fields.Float('Cubic Ft', digits=dp.get_precision('Product Dimension'))
    barcode_unit = fields.Char('Unit Barcode')
    barcode_case = fields.Char('Case Barcode')
    qty_case = fields.Float('Case Quantity', digits=dp.get_precision('Product Dimension'))
    barcode_inner_case = fields.Char('Inner Case Barcode')
    qty_inner_case = fields.Float('Inner Case Quantity', digits=dp.get_precision('Product Dimension'))