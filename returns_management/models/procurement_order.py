# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    receipt_return_line_id = fields.Many2one('sale.return.line', 'Return')
    replacement_return_line_id = fields.Many2one('sale.return.line', 'Return')

    @api.multi
    def _prepare_purchase_order(self, partner):
        result = super(ProcurementOrder, self)._prepare_purchase_order(partner)
        if self.receipt_return_line_id:
            result['return_id'] = self.receipt_return_line_id.return_id.id
        return result
