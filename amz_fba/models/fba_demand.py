# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models

from datetime import datetime, timedelta


class FBADemand(models.Model):
    _name = "sale.fba.demand.report"
    _description = "FBA Demand Report"
    _auto = False
    _rec_name = 'asin'
    _order = 'asin desc'

    asin = fields.Char('ASIN', required=True)
    seller_sku = fields.Char('Seller SKU')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template')
    current_qty = fields.Integer('Current Qty')
    demand_14 = fields.Integer('14-Day Demand')
    demand_30 = fields.Integer('30-Day Demand')
    suggested_qty = fields.Integer('Suggested Ship Qty', compute='_compute_suggested_qty')

    @api.multi
    @api.depends('current_qty', 'demand_14', 'demand_30')
    def _compute_suggested_qty(self):
        for r in self:
            qty = 21 * r.demand_30/30 - max(r.current_qty - 7 * r.demand_30/30, 0)
            if qty > 0:
                r.suggested_qty = int(qty)
            else:
                r.suggested_qty = 0

    @api.model_cr
    def init(self):
        now = datetime.now()
        dt_format = '%Y-%m-%d %H:%M:%S'
        days_14_str = (now - timedelta(days=14)).strftime(dt_format)
        days_30_str = (now - timedelta(days=30)).strftime(dt_format)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT
              L.id,
              L.name as seller_sku,
              L.product_tmpl_id,
              L.asin,
              L.fba_qty as current_qty,
              (CASE WHEN DAY14KIT.qty > 0 THEN DAY14KIT.qty ELSE DAY14.qty END) as demand_14,
              (CASE WHEN DAY30KIT.qty > 0 THEN DAY30KIT.qty ELSE DAY30.qty END) as demand_30
            FROM product_listing L
            LEFT JOIN (
              SELECT RES.item_id, SUM(RES.qty) as qty FROM (
                SELECT SOL.item_id, MAX(SOL.product_uom_qty) as qty
                FROM sale_order_line SOL
                LEFT JOIN product_product PP on SOL.product_id = PP.id
                WHERE SOL.create_date >= '%s'
                AND SOL.kit_line_id IS NOT NULL
                GROUP BY SOL.item_id, SOL.kit_line_id
              ) as RES
              GROUP BY RES.item_id
            ) as DAY14KIT ON DAY14KIT.item_id = L.name
            LEFT JOIN (
              SELECT RES.item_id, SUM(RES.qty) as qty FROM (
                SELECT SOL.item_id, MAX(SOL.product_uom_qty) as qty
                FROM sale_order_line SOL
                LEFT JOIN product_product PP on SOL.product_id = PP.id
                WHERE SOL.create_date >= '%s'
                AND SOL.kit_line_id IS NOT NULL
                GROUP BY SOL.item_id, SOL.kit_line_id
              ) AS RES
              GROUP BY RES.item_id
            ) as DAY30KIT ON DAY30KIT.item_id = L.name
            LEFT JOIN (
              SELECT SOL.item_id, SUM(SOL.product_uom_qty) as qty
              FROM sale_order_line SOL
              LEFT JOIN product_product PP on SOL.product_id = PP.id
              WHERE SOL.create_date >= '%s'
              GROUP BY SOL.item_id
            ) as DAY14 ON DAY14.item_id = L.name
            LEFT JOIN (
              SELECT SOL.item_id, SUM(SOL.product_uom_qty) as qty
              FROM sale_order_line SOL
              LEFT JOIN product_product PP on SOL.product_id = PP.id
              WHERE SOL.create_date >= '%s'
              GROUP BY SOL.item_id
            ) as DAY30 ON DAY30.item_id = L.name
            WHERE L.listing_type = 'fba'    
        )""" % (self._table, days_14_str, days_30_str, days_14_str, days_30_str))
