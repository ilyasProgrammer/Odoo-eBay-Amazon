# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.exceptions import UserError
import json

class SyncEbayCategories(models.TransientModel):
    _name = 'product.ebay.category.sync.wizard'
    _description = 'eBay Categories Sync Wizard'

    parent_category_id = fields.Integer('Parent Category ID', help="Specify the ID of the parent category you wish to sync.", required=True)
    site_id = fields.Integer('eBay Site ID', default=100, help="Leave empty for non-eBay Motors Categories.")

    @api.multi
    def button_sync_ebay_categories(self):
        self.ensure_one()
        store_id = self.env['sale.store'].search([('site', '=', 'ebay'), ('enabled', '=', True)], limit=1)
        if not store_id:
            raise UserErrror('No eBay creadentials found.')
        call_values = {'ViewAllNodes': True, 'CategoryParent': self.parent_category_id, 'DetailLevel': 'ReturnAll' }
        if self.site_id:
            call_values['CategorySiteID'] = self.site_id
        results = store_id.ebay_execute('GetCategories', call_values).dict()
        categories = []
        for c in results['CategoryArray']['Category']:
            categories.append({
                'name': c['CategoryName'],
                'level': int(c['CategoryLevel']),
                'ebay_category_parent_id': int(c['CategoryParentID']) if 'CategoryParentID' in c else 0,
                'is_leaf_category': True if 'LeafCategory' in c else False,
                'ebay_category_id': int(c['CategoryID'])
            })
        categories = sorted(categories, key=lambda c: c['level'])
        for c in categories:
            CategoryObj = self.env['product.ebay.category']
            values = {
                'name': c['name'],
                'is_leaf_category': c['is_leaf_category'],
                'ebay_category_id': c['ebay_category_id']
            }
            if c['ebay_category_parent_id']:
                parent_id = CategoryObj.search([('ebay_category_id', '=', c['ebay_category_parent_id'])])
                if parent_id:
                    values['parent_id'] = parent_id.id
            existing_category_id = CategoryObj.search([('ebay_category_id', '=', c['ebay_category_id'])])
            if existing_category_id:
                existing_category_id.write(values)
            else:
                CategoryObj.create(values)
            self.env.cr.commit()



