# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class BoxBarcodes(models.AbstractModel):
    _name = 'report.stock_order_processing.stock_box_barcodes_report'

    @api.multi
    def render_html(self, doc_ids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('stock_order_processing.stock_box_barcodes_report')
        docargs = {
            'product_tmpl_ids': self.env['product.template'].search([('is_packaging_product', '=', True)])
        }
        return report_obj.render('stock_order_processing.stock_box_barcodes_report', docargs)
