# -*- coding: utf-8 -*-


from odoo import models, fields, api, _


class ProductTemplateListed(models.Model):
    _name = 'product.template.listed'
    _description = 'Listed Product Templates'
    _rec_name = 'product_tmpl_id'
    _order = 'id desc'

    _sql_constraints = [
        ('product_tmpl_id_uniq', 'unique(product_tmpl_id)', _("A product can be added here only once!")),
    ]

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', required=True)
    wh_qty = fields.Integer('WH Qty')
    wh_prev_qty = fields.Integer('Previous WH Qty')
    wh_qty_write_date = fields.Datetime('WH Qty Last Updated On')
    wh_product_cost = fields.Float('WH Product Cost')
    wh_prev_product_cost = fields.Float('Previous WH Product Cost')
    wh_product_cost_write_date = fields.Datetime('WH Product Cost Last Updated On')
    wh_shipping_cost = fields.Float('WH Shipping Cost')
    wh_box_cost = fields.Float('WH Box Cost', default=0.0, help='Average box cost')
    wh_prev_shipping_cost = fields.Float('Previous WH Shipping Cost')
    wh_shipping_cost_write_date = fields.Datetime('WH Shipping Cost Last Updated On')
    wh_sale_price = fields.Float('eBay WH Sale Price')
    vendor_qty = fields.Integer('Vendor Qty')
    vendor_qty_write_date = fields.Datetime('Vendor Qty Last Updated On')
    vendor_cost = fields.Float('Vendor Product Cost')
    vendor_cost_write_date = fields.Datetime('Vendor Cost Last Updated On')
    total_min_cost = fields.Float('Total Min Cost')
    ebay_min_price = fields.Float('eBay Min Price', compute='_compute_ebay_min_price')
    amz_min_price = fields.Float('Amazon Min Price', compute='_compute_amz_min_price')
    prev_total_min_cost = fields.Float('Previous Total Min Cost')
    total_min_cost_write_date = fields.Datetime('Total Min Cost Last Updated On')
    state = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], required=True, copy=False, default='active')

    competitors_count = fields.Integer('# of Competitors', compute='_compute_competitors_count')
    listings_count = fields.Integer('# of Listings', compute='_compute_listings_count')
    sales_count = fields.Integer('# of Sales', compute='_compute_sales_count')
    is_a_kit = fields.Boolean('Is a Kit', compute='_compute_is_a_kit')
    is_component_of = fields.Boolean('Is Component Of', compute='_compute_is_component_of')

    @api.multi
    def button_set_as_active(self):
        self.write({'state': 'active'})

    @api.multi
    def button_set_as_inactive(self):
        self.write({'state': 'inactive'})

    @api.multi
    @api.depends('product_tmpl_id')
    def _compute_sales_count(self):
        for p in self:
            p.sales_count = sum([r.sales_count for r in p.product_tmpl_id.product_variant_ids])

    @api.multi
    @api.depends('total_min_cost')
    def _compute_ebay_min_price(self):
        for p in self:
            p.ebay_min_price = round(p.total_min_cost / 0.89, 2)

    @api.multi
    @api.depends('total_min_cost')
    def _compute_amz_min_price(self):
        for p in self:
            p.amz_min_price = round(p.total_min_cost / 0.88, 2)

    @api.multi
    @api.depends('product_tmpl_id')
    def _compute_competitors_count(self):
        for p in self:
            p.competitors_count = len(p.product_tmpl_id.competitor_ids)

    @api.multi
    @api.depends('product_tmpl_id')
    def _compute_listings_count(self):
        for p in self:
            p.listings_count = len(p.product_tmpl_id.listing_ids)

    @api.multi
    @api.depends('product_tmpl_id')
    def _compute_is_a_kit(self):
        for p in self:
            if p.product_tmpl_id.bom_ids:
                p.is_a_kit = True
            else:
                p.is_a_kit = False

    @api.multi
    @api.depends('product_tmpl_id')
    def _compute_is_component_of(self):
        for p in self:
            bom_line_ids = self.env['mrp.bom.line'].search([('product_id', 'in', p.product_tmpl_id.product_variant_ids.ids)])
            if bom_line_ids:
                p.is_component_of = True
            else:
                p.is_component_of = False

    @api.multi
    def action_view_competitors(self):
        action = self.env.ref('stock_update_store_real_time.action_repricer_competitor')
        result = action.read()[0]
        result['context'] = {'search_default_product_tmpl_id': [self.product_tmpl_id.id]}
        return result

    @api.multi
    def action_view_listings(self):
        action = self.env.ref('sale_store.action_product_listing')
        result = action.read()[0]
        result['context'] = {'search_default_product_tmpl_id': [self.product_tmpl_id.id]}
        return result

    @api.multi
    def action_view_components(self):
        if self.product_tmpl_id.bom_ids:
            action = self.env.ref('product_template_with_listing.action_product_template_listed')
            result = action.read()[0]
            bom_line_ids = self.product_tmpl_id.bom_ids[0].bom_line_ids
            comp_product_tmpl_ids = bom_line_ids.mapped('product_id').mapped('product_tmpl_id')
            result['domain'] = "[('product_tmpl_id','in',[" + ','.join(map(str, comp_product_tmpl_ids.ids)) + "])]"
            return result

    @api.multi
    def action_view_component_of(self):
        bom_line_ids = self.env['mrp.bom.line'].search([('product_id', 'in', self.product_tmpl_id.product_variant_ids.ids)])
        if bom_line_ids:
            action = self.env.ref('product_template_with_listing.action_product_template_listed')
            result = action.read()[0]
            kit_product_tmpl_ids = bom_line_ids.mapped('bom_id').mapped('product_tmpl_id')
            result['domain'] = "[('product_tmpl_id','in',[" + ','.join(map(str, kit_product_tmpl_ids.ids)) + "])]"
            return result

    @api.multi
    def action_view_sales(self):
        action = self.env.ref('sale.action_product_sale_list')
        product_ids = self.product_tmpl_id.product_variant_ids.ids
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{'default_product_id': " + str(product_ids[0]) + "}",
            'res_model': action.res_model,
            'domain': [('state', 'in', ['sale', 'done']), ('product_id.product_tmpl_id', '=', self.product_tmpl_id.id)],
        }

    @api.multi
    def button_do_not_restock_all_listings(self):
        for r in self:
            r.product_tmpl_id.listing_ids.write({'do_not_restock': True })

    @api.multi
    def button_restock_all_listings(self):
        for r in self:
            r.product_tmpl_id.listing_ids.write({'do_not_restock': False })

    @api.multi
    def button_do_not_reprice_all_listings(self):
        for r in self:
            r.product_tmpl_id.listing_ids.write({'do_not_reprice': True })

    @api.multi
    def button_reprice_all_listings(self):
        for r in self:
            r.product_tmpl_id.listing_ids.write({'do_not_reprice': False })
