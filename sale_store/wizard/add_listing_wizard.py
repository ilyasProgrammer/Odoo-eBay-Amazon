# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class StoreAddListing(models.TransientModel):
    _name = 'sale.store.add.listing'

    def _default_product_template(self):
        return self._context.get('active_model') == 'product.template' and self._context.get('active_ids')[0]

    product_tmpl_id = fields.Many2one('product.template', 'Product', required=True, default=_default_product_template)
    # store_id = fields.Many2one('sale.store', 'Store to Publish the Product', required=True, domain=[('enabled', '=', True)])
    store_id = fields.Many2one('sale.store', 'Store to Publish the Product', required=False, domain=[('enabled', '=', True)])
    site = fields.Selection([], 'Site', related='store_id.site')
    product_name = fields.Char('Product Name')
    price = fields.Float('Price')
    quantity = fields.Integer('Quantity')
    ebay_category_id = fields.Integer('Category')
    image = fields.Binary('Upload an image')

    @api.multi
    def button_add_listing(self):
        # METHOD OVERWRITTEN IN sale_store_ebay_ext
        self.ensure_one()
        now = datetime.now()
        params = {
            'product_name': self.product_name,
            'price': self.price,
            'quantity': self.quantity,
            'ebay_category_id': self.ebay_category_id
        }
        if self.image:
            attachment = self.env['ir.attachment'].create({
                'name': 'ebay_listing_image_' + self.product_tmpl_id.name,
                'datas': self.image,
                'datas_fname': self.product_tmpl_id.name + '.png',
                'public': True,
                'res_model': 'sale.store.add.listing',
            })
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            params['image_url'] = base_url + '/web/content/' + str(attachment.id)
        if hasattr(self.store_id, '%s_list_new_product' % self.store_id.site):
            getattr(self.store_id, '%s_list_new_product' % self.store_id.site)(now, self.product_tmpl_id, params)
        return {'type': 'ir.actions.act_window_close'}
