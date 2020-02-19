# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ActiveListing(models.Model):
    _name = 'sale.store.active.listing'
    _rec_name = 'item_id'

    item_id = fields.Char("Item ID", required=True)
    custom_label = fields.Char("Custom Label")
    title = fields.Char("Title")

    @api.model
    def cron_ebay_get_duplicate_listing(self):
        lines = open('/var/tmp/OnlyCustomLabels.csv', 'r').readlines()
        out  = open('/var/tmp/duplicates.csv', 'w')
        lines_set = set(lines)
        for l in lines_set:
            list_ids = self.search([('custom_label', '=', l)])
            out.write('%s\n' %l)