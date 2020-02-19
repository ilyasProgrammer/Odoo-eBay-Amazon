# -*- coding: utf-8 -*-


from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def update_shipping_template_of_listings_to_default(self):
        listing_ids = self.env['product.listing'].search([('listing_type', '=', 'fbm'), ('product_tmpl_id', '=', self.id), ('title', '!=', False)])
        bom_line_ids = self.env['mrp.bom.line'].search([('product_id', '=', self.product_variant_id.id )])
        if bom_line_ids:
            bom_ids = bom_line_ids.mapped('bom_id')
            product_tmpl_ids = bom_ids.mapped('product_tmpl_id')
            listing_ids |= self.env['product.listing'].search([('listing_type', '=', 'fbm'), ('product_tmpl_id', 'in', product_tmpl_ids.ids), ('title', '!=', False)])
        if listing_ids:
            store_ids = listing_ids.mapped('store_id')
            for store_id in store_ids:
                listing_ids_in_store = listing_ids.filtered(lambda l: l.store_id.id == store_id.id)
                if listing_ids_in_store:
                    data = []
                    for listing_id in listing_ids_in_store:
                        data.append((listing_id.name, listing_id.title, listing_id.store_id.default_shipping_template_id.name))
                    store_id.update_shipping_template(data)

    @api.multi
    def reprice_listings_with_min_cost(self):
        super(ProductTemplate, self).reprice_listings_with_min_cost()
        self.update_shipping_template_of_listings_to_default()
