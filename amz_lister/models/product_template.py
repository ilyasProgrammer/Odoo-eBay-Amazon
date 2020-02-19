# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def get_image_urls(self, limit=8):
        # Use USAP alternate images first
        image_urls = self.env['sale.order'].autoplus_execute("""
            SELECT TOP %s ASST.URI
            FROM Inventory INV
            LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
            LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
            LEFT JOIN InventoryPiesASST ASST on INV2.InventoryID = ASST.InventoryID
            WHERE INV.PartNo = '%s' and INV.MfgID = 1 AND INV2.MfgID IN (16,35,36,37,38,39)
            AND ASST.URI IS NOT NULL
            ORDER BY ASST.InventoryPiesAsstID ASC
        """ %(limit, self.part_number,))

        if not image_urls:
            image_urls = self.env['sale.order'].autoplus_execute("""
                SELECT TOP %s ASST.URI
                FROM Inventory INV
                LEFT JOIN InventoryPiesASST ASST on INV.InventoryID = ASST.InventoryID
                WHERE INV.PartNo = '%s'
                AND ASST.URI IS NOT NULL
                ORDER BY ASST.InventoryPiesAsstID ASC
            """ %(limit, self.part_number,))

        res = []
        for i in image_urls:
            res.append(i['URI'])

        return res
