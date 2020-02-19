# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models


class MAMPSales(models.Model):
    _name = "mapm.sales.report"
    _description = "mapm.sales.report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    order_id = fields.Many2one('sale.order', 'Order', readonly=True)
    item_id = fields.Char('Item', readonly=True)
    name = fields.Char('LAD', readonly=True)
    price_total = fields.Float('Price total', readonly=True)
    date = fields.Datetime('Date Order', readonly=True)

    @api.model_cr
    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        qry = """CREATE or REPLACE VIEW mapm_sales_report as (
                 SELECT row_number() OVER () AS id, sol.order_id as order_id, so.date_order - '4 hour'::interval as date, 
                        sol.item_id, sol.name as name, sol.price_total as price_total
                 FROM public.sale_order_line sol
                 LEFT JOIN sale_order so ON sol.order_id = so.id
                 WHERE so.state IN ('sale','done') AND  sol.item_id LIKE 'MAPM-%' AND sol.item_id NOT LIKE 'MAPM-PBL-%'
                 ORDER BY order_id, item_id
                 )"""
        self.env.cr.execute(qry)
