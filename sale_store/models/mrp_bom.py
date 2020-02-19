# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MRPBOM(models.Model):
    _inherit = 'mrp.bom'

    @api.multi
    def sync_bom_with_autoplus(self):
        for bom_id in self:
            _logger.info('Syncing BOM %s' % bom_id.product_tmpl_id.name)
            query = """
                SELECT INV.InventoryID, KIT.Qty FROM InventoryPiesKit KIT
                LEFT JOIN Inventory INV on INV.PartNo = KIT.PartNo
                WHERE KIT.InventoryID = %s
            """ % bom_id.product_tmpl_id.inventory_id
            comp_results = self.env['sale.order'].autoplus_execute(query)
            _logger.info('Syncing BOM %s' % comp_results)
            # Remove lines that are deleted as component
            inventory_id_list = []
            for c in comp_results:
                if c['InventoryID']:
                    inventory_id_list.append(c['InventoryID'])
            bom_line_ids_to_delete = bom_id.bom_line_ids.filtered(lambda r: r.product_id.inventory_id in inventory_id_list)
            for bom_line_id in bom_line_ids_to_delete:
                bom_line_id.unlink()

            for c in comp_results:
                # Update if product is existing as a line in the bom
                bom_line_id = bom_id.bom_line_ids.filtered(lambda r: r.product_id.inventory_id == c['InventoryID'])
                if bom_line_id:
                    bom_line_id.write({'product_qty': c['Qty']})
                elif c['InventoryID']:
                    comp_product_id = self.env['product.product'].search([('inventory_id', '=', c['InventoryID'])])
                    if not comp_product_id:
                        comp_product_tmpl = self.env['product.template'].create({'name': 'New', 'inventory_id': c['InventoryID']})
                        comp_product_tmpl.button_sync_with_autoplus()
                        comp_product_id = comp_product_tmpl.product_variant_id
                    self.env['mrp.bom.line'].create({'product_id': comp_product_id.id, 'bom_id': bom_id.id, 'product_qty': c['Qty'] or 1})
            _logger.info('Updated Kit for Inv ID %s' % bom_id.product_tmpl_id.inventory_id)
        return True

    @api.model
    def get_kits_from_autoplus(self, limit, offset):
        page = 1
        while (page - 1) *200 < limit:
            current_offset = offset + (200*(page-1))
            query = """
                SELECT DISTINCT InventoryID FROM InventoryPiesKit
                ORDER BY InventoryID
                OFFSET %s ROWS
                FETCH NEXT %s ROWS ONLY
            """ %(current_offset, min(200, offset + limit - current_offset))
            inventory_id_rows = self.env['sale.order'].autoplus_execute(query)
            for r in inventory_id_rows:
                product_tmpl = self.env['product.template'].search([('inventory_id', '=', r['InventoryID'])])
                if product_tmpl:
                    product_tmpl.write({'route_ids': [(6, 0, [self.env.ref('stock.route_warehouse0_mto').id] )]})
                if not product_tmpl:
                    product_tmpl = self.env['product.template'].create({'name': 'New', 'inventory_id': r['InventoryID']})
                    product_tmpl.button_sync_with_autoplus()
                bom_id = self.search([('product_tmpl_id.id', '=', product_tmpl.id)])
                if bom_id:
                    bom_id.sync_bom_with_autoplus()
                else:
                    bom_id = self.create({'product_tmpl_id': product_tmpl.id, 'product_qty': 1, 'type': 'phantom'})
                    query = """
                        SELECT INV.InventoryID, KIT.Qty FROM InventoryPiesKit KIT
                        LEFT JOIN Inventory INV on INV.PartNo = KIT.PartNo
                        WHERE KIT.InventoryID = %s
                    """ %(r['InventoryID'])
                    comp_results = self.env['sale.order'].autoplus_execute(query)
                    for c in comp_results:
                        if c['InventoryID']:
                            comp_product_id = self.env['product.product'].search([('inventory_id', '=', c['InventoryID'])])
                            if not comp_product_id:
                                comp_product_tmpl = self.env['product.template'].create({'name': 'New', 'inventory_id': c['InventoryID']})
                                comp_product_tmpl.button_sync_with_autoplus()
                                comp_product_id = comp_product_tmpl.product_variant_id
                            self.env['mrp.bom.line'].create({'product_id': comp_product_id.id, 'bom_id': bom_id.id, 'product_qty': c['Qty']})
                    _logger.info('Created Kit for Inv ID %s' %r['InventoryID'])
                self.env.cr.commit()
            _logger.info('Creating kits done with page %s, current offset is %s' %(page, current_offset))
            page += 1

