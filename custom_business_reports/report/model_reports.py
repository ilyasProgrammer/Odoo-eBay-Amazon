# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class ReturnCostReport(models.Model):
    _name = "return.cost.report"
    _description = "Return Cost Report"
    _auto = False
    _order = 'date_done desc'

    date_done = fields.Datetime('Date', readonly=True, index=True)
    cost = fields.Float(string='Cost')
    type = fields.Selection([('good', 'good'), ('scrapped', 'scrapped')], string='Type')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'return_cost_report')
        self.env.cr.execute("""
            create or replace view return_cost_report as (
            SELECT * FROM ( 
                            SELECT sm.id, sm.date as date_done, sm.product_qty * sm.price_unit as cost,  
                            CASE WHEN sm.scrapped IS TRUE THEN 'scrapped' ELSE 'good'END as type  -- 8743
                            FROM sale_return sr
                            LEFT JOIN stock_picking sp
                            ON sr.id = sp.receipt_return_id
                            left join stock_move sm
                            on sm.picking_id = sp.id
                            WHERE sp.state ='done'
                            ORDER BY sr.id, sp.id, sm.id
                    ) a
                    order by a.date_done                          
                )
            """)
