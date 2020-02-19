# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    more_info_url = fields.Char('More Info URL', compute='_get_more_info_url')
    dropship_shipping_cost = fields.Float('Dropship Shipping Cost', compute='_compute_qty_autoplus')
    dropship_handling_cost = fields.Float('Dropship Handling Cost', compute='_compute_qty_autoplus')
    dropship_base_cost = fields.Float('Dropship Base Cost', compute='_compute_qty_autoplus')
    dropship_total_cost = fields.Float('Dropship Total Cost', compute='_compute_qty_autoplus')

    @api.multi
    @api.depends()
    def _get_more_info_url(self):
        for p in self:
            p.more_info_url = '/autoplus/products/' + str(p.id)

    @api.multi
    def _compute_qty_autoplus(self):
        for product_tmpl_id in self:
            qty_onhand = 0.0
            dropship_base_cost = 0.0
            dropship_handling_cost = 0.0
            dropship_shipping_cost = 0.0
            dropship_total_cost = 0.0

            query = """
                SELECT INV.QtyOnHand as qty_onhand, PR.Cost as dropship_total_cost FROM Inventory INV
                LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
                WHERE INV.PartNo = '%s'
            """ %product_tmpl_id.part_number
            if product_tmpl_id.mfg_code in ['BXLD', 'GMK']:
                query = """
                    SELECT INV.QtyOnHand as qty_onhand, C2C.DomesticCost as dropship_base_cost, C2C.ShippingCost as dropship_shipping_cost, PR.Cost as dropship_total_cost FROM Inventory INV
                    LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
                    LEFT JOIN C2C.dbo.Warehouse C2C on C2C.PartNumber = INV.PartNo
                    WHERE INV.PartNo = '%s'
                """ %product_tmpl_id.part_number
            elif product_tmpl_id.mfg_code in ['BFHZ', 'REPL', 'STYL', 'NDRE', 'BOLT', 'EVFI']:
                query = """
                    SELECT INV.QtyOnHand as qty_onhand, USAP.Cost as dropship_base_cost, USAP.ShippingPrice as dropship_shipping_cost, USAP.HandlingPrice as dropship_handling_cost, PR.Cost as dropship_total_cost FROM Inventory INV
                    LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
                    LEFT JOIN USAP.dbo.Warehouse USAP on USAP.PartNo = INV.PartNo
                    WHERE INV.PartNo = '%s'
                """ %product_tmpl_id.part_number
            elif product_tmpl_id.mfg_code in ['PPR']:
                query = """
                    SELECT INV.QtyOnHand as qty_onhand, USAP.Cost as dropship_base_cost, USAP.ShippingPrice as dropship_shipping_cost, USAP.HandlingPrice as dropship_handling_cost, PR.Cost as dropship_total_cost FROM Inventory INV
                    LEFT JOIN InventoryMiscPrCur PR on INV.InventoryID = PR.InventoryID
                    LEFT JOIN USAP.dbo.Warehouse USAP on USAP.PartNo = INV.PartNo
                    WHERE INV.PartNo = '%s'
                """ %product_tmpl_id.part_number
            if query:
                result = self.env['sale.order'].autoplus_execute(query)
                if result:
                    qty_onhand = float(result[-1]['qty_onhand']) if result[-1]['qty_onhand'] > 0 else 0.0
                    dropship_base_cost = float(result[-1]['dropship_base_cost']) if 'dropship_base_cost' in result[-1] and result[-1]['dropship_base_cost'] > 0 else 0.0
                    dropship_shipping_cost = float(result[-1]['dropship_shipping_cost']) if 'dropship_shipping_cost' in result[-1] and result[-1]['dropship_shipping_cost'] > 0 else 0.0
                    dropship_handling_cost = float(result[-1]['dropship_handling_cost']) if 'dropship_handling_cost' in result[-1] and result[-1]['dropship_handling_cost'] > 0 else 0.0
                    dropship_total_cost = float(result[-1]['dropship_total_cost']) if 'dropship_total_cost' in result[-1] and result[-1]['dropship_total_cost'] > 0 else 0.0
            product_tmpl_id.qty_onhand = qty_onhand
            product_tmpl_id.dropship_base_cost = dropship_base_cost
            product_tmpl_id.dropship_handling_cost = dropship_handling_cost
            product_tmpl_id.dropship_shipping_cost = dropship_shipping_cost
            product_tmpl_id.dropship_total_cost = dropship_total_cost

    @api.multi
    def _compute_purchase_info(self):
        return
