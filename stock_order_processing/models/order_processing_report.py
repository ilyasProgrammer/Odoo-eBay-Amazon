# -*- coding: utf-8 -*-


from odoo import tools
from odoo import api, fields, models


class OrderProcessingReport(models.Model):
    _name = "stock.order.processing.report"
    _description = "Order Processing Report"
    _auto = False
    _rec_name = 'processed_date'
    _order = 'processed_date desc'

    name = fields.Char('Order Reference', readonly=True)
    processed_by_uid = fields.Many2one('res.users', 'Processed By')
    processed_date = fields.Datetime('Processed Date')

    @api.model_cr
    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT min(P.id) as id, P.name, P.processed_by_uid, P.processed_date
            FROM (stock_picking P
            LEFT JOIN stock_picking_type PTYPE on PTYPE.id = P.picking_type_id)
            WHERE PTYPE.require_packaging = True AND P.state = 'done'
            GROUP BY
            P.name, P.processed_by_uid, P.processed_date
        )""" % (self._table))
