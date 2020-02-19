# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools


class StockPackOperaion(models.Model):
    _inherit = 'stock.pack.operation'

    @api.model
    def create(self, vals):
        res = super(StockPackOperaion, self).create(vals)
        if res and res.picking_id:
            if res.location_id:
                res.picking_id.pick_src = res.location_id
            if res.location_dest_id:
                res.picking_id.pick_dst = res.location_dest_id
        return res
