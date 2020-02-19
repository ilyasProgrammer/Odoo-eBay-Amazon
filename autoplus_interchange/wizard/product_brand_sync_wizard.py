# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class SyncBrands(models.TransientModel):
    _name = 'product.brand.sync.wizard'
    _description = 'Product Brand Sync Wizard'

    @api.multi
    def button_sync_brands(self):
        BrandObj = self.env['product.brand']
        query = """
            SELECT * FROM Mfg
        """
        results = self.env['sale.order'].autoplus_execute(query)
        for r in results:
            brand_id = BrandObj.search([('code', '=', r['MfgCode'])])
            if not brand_id:
                values = {'code': r['MfgCode'], 'brand_name': r['MfgName']}
                if r['ShortDesc']:
                    values['description'] = r['ShortDesc']
                BrandObj.create(values)
                self.env.cr.commit()
