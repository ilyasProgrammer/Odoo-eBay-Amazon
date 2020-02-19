# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SelectExistBox(models.TransientModel):
    _name = "select.exist.box"

    package_box = fields.Many2one('product.product', domain=[('box_packaging', '=', True)])

    @api.multi
    def confirm(self):
        context = self.env.context
        active_ids = context.get('active_ids')
        if context.get('active_model') == 'stock.pack.operation' and active_ids:
            operation = self.env['stock.pack.operation'].browse(active_ids)
            operation.write({'use_exsiting_box': True, 'package_box': self.package_box.id, 'box_barcode': self.package_box.barcode})
