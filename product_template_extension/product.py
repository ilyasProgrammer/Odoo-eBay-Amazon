# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ebay_min_price = fields.Float(compute='_get_prices_from_ptl', string='eBay min price')
    amz_min_price = fields.Float(compute='_get_prices_from_ptl', string='Amz min price')
    ebay_min_price_raised = fields.Float(compute='_get_prices_from_ptl', string='eBay min price + 5%')
    amz_min_price_raised = fields.Float(compute='_get_prices_from_ptl', string='Amz min price + 5%')
    stop_on_rfq = fields.Boolean('Stop On Quotation', default=False)
    stop_on_rfq_site = fields.Selection([('all', 'All'), ('ebay', 'eBay'), ('amz', 'Amazon')], string='Stop On RFQ Type', default='all')

    @api.multi
    def _get_prices_from_ptl(self):
        for rec in self:
            ptl = self.env['product.template.listed'].search([('product_tmpl_id', '=', rec.id)])
            if ptl:
                rec.ebay_min_price = ptl.ebay_min_price
                rec.amz_min_price = ptl.amz_min_price
                rec.ebay_min_price_raised = ptl.ebay_min_price * 1.05
                rec.amz_min_price_raised = ptl.amz_min_price * 1.05

