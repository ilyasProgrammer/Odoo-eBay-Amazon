# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class PrintBoxBarcodeWizard(models.TransientModel):
    _name = 'stock.print.box.barcodes.wizard'

    @api.multi
    def print_report(self):
        self.ensure_one()
        data = {'vals': {}}
        return self.env['report'].get_action(self, 'stock_order_processing.stock_box_barcodes_report', data=data)
