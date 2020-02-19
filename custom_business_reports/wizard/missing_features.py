# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class MissingFeatures(models.TransientModel):
    _name = 'sale.missing.features.wizard'

    missing_feature = fields.Selection([('fitment', 'Fitment'),
        ('category', 'Category'),
        ('image', 'Image'),
        ('attributes', 'Attributes')], "Missing Feature", default='fitment', required=True)
    brand = fields.Selection([('lad', 'LAD'), ('pfg', 'PFG'), ('lkq', 'LKQ'),
        ('apc', 'AP Collission'), ('mg', 'Magnifiek')], "Brand", default='lad', required=True)

    @api.multi
    def button_download_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/reports/missing_features?id=%s' % (self.id),
            'target': 'new',
        }
