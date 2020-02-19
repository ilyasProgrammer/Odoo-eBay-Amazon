# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductBrand(models.Model):
    _name = 'product.brand'
    _rec_name = 'code'

    code = fields.Char('Brand Code', required=True)
    brand_name = fields.Char('Brand Name')
    description = fields.Char('Description')
    multiplier = fields.Float(default=0.0, help="If set then final price = min_cost * multiplier, ignoring other rules")
    do_not_reprice = fields.Boolean('Do Not Reprice', help="Applied to all listings of this brand. Could be overridden by listing value.")
    use_supplier_price = fields.Boolean('Use Suppliers Price', default=False)


class ProductListing(models.Model):
    _inherit = 'product.listing'

    brand_id = fields.Many2one('product.brand', string='Store Brand')
    multiplier = fields.Float(related='brand_id.multiplier', readonly=True)
    brand_do_not_reprice = fields.Boolean(related='brand_id.do_not_reprice', readonly=True)


class ProductInterchange(models.Model):
    _name = 'product.interchange'
    _rec_name = 'product_tmpl_id'

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', required=True)
    product_id = fields.Many2one('product.product', 'Product Variant', related='product_tmpl_id.product_variant_id', store=True)
    part_number = fields.Char('Part Number', required=True)
    brand_id = fields.Many2one('product.brand', 'Brand')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    interchange_ids = fields.One2many('product.interchange', 'product_tmpl_id', 'Interchange Part Nos.')

    @api.multi
    def button_sync_with_autoplus(self, raise_exception=True):
        res = super(ProductTemplate, self).button_sync_with_autoplus(raise_exception=raise_exception)
        query = """SELECT 
            INTE.PartNo,
            INTE.BrandID
            FROM Inventory INV
            LEFT JOIN InventoryPiesINTE INTE on INTE.InventoryID = INV.InventoryID
            WHERE INV.PartNo = '%s'
        """ %self.part_number
        results = self.env['sale.order'].autoplus_execute(query)
        interchange_ids_to_unlink = self.interchange_ids
        for r in results:
            if r['PartNo']:
                interchange_id = self.interchange_ids.filtered(lambda x: x.part_number == r['PartNo'] and x.brand_id.code == r['BrandID'])
                if interchange_id:
                    interchange_ids_to_unlink -= interchange_id
                else:
                    brand_id = self.env['product.brand'].search([('code', '=', r['BrandID'])])
                    if brand_id:
                        self.env['product.interchange'].create({
                            'product_tmpl_id': self.id,
                            'part_number': r['PartNo'],
                            'brand_id': brand_id.id
                        })
        for interchange_id in interchange_ids_to_unlink:
            interchange_id.unlink()
        return res

    @api.multi
    def action_product_interchange_filtered_by_product(self):
        self.ensure_one()
        action = self.env.ref('autoplus_interchange.action_product_interchange')
        return {
            'name': action.name,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{'default_product_tmpl_id': " + str(self.id) + "}",
            'res_model': action.res_model,
            'domain': [('product_tmpl_id', '=', self.id)],
        }