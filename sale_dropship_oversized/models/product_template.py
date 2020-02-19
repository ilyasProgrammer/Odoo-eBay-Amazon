# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    oversized = fields.Boolean('Oversized', help="Oversized parts will not be routed to the warehouse. UPD: it will be routed to WH new fedex oversized account OR Dropshiping")
    avoid_ppr = fields.Boolean('Do Not Ship PPR')

    @api.multi
    def write(self, vals):
        length = float(vals['length']) if vals.get('length') else self.length
        width = float(vals['width']) if vals.get('width') else self.width
        height = float(vals['height']) if vals.get('height') else self.height
        if (length + width * 2 + height * 2) > 136:
            vals['oversized'] = True
        else:
            vals['oversized'] = False
        res = super(ProductTemplate, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        length = float(vals['length']) if vals.get('length') else self.length
        width = float(vals['width']) if vals.get('width') else self.width
        height = float(vals['height']) if vals.get('height') else self.height
        if (length + width * 2 + height * 2) > 136:
            vals['oversized'] = True
        else:
            vals['oversized'] = False
        res = super(ProductTemplate, self).create(vals)
        # below is fix cuz for some reason this values disappears on creation from template. Maybe because of compute and reverse.
        res.length = length
        res.width = width
        res.height = height
        return res

#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     @api.multi
#     def write(self, vals):
#         length = float(vals['length']) if vals.get('length') else self.length
#         width = float(vals['width']) if vals.get('width') else self.width
#         height = float(vals['height']) if vals.get('height') else self.height
#         if (length + width * 2 + height * 2) > 136:
#             vals['oversized'] = True
#         else:
#             vals['oversized'] = False
#         res = super(ProductProduct, self).write(vals)
#         return res
