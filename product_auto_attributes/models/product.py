# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class ProductAutoAttribute(models.Model):
    _name = "product.auto.attribute"
    _description = "Product Auto Attribute"
    _order = 'name'

    name = fields.Char('Name', required=True)
    value_ids = fields.One2many('product.auto.attribute.value', 'auto_attribute_id', 'Values', copy=True)
    attribute_line_ids = fields.One2many('product.auto.attribute.line', 'auto_attribute_id', 'Lines')
    attribute_synonym_ids = fields.One2many('product.auto.attribute.synonym', 'auto_attribute_id', 'Synonyms')
    item_specific_attribute_ids = fields.Many2many('product.item.specific.attribute', 'product_att_specific_rel', 'att_id', 'specific_id', 'Linked Item Specifics')

class ProductAutoAttributeSynonym(models.Model):
    _name = "product.auto.attribute.synonym"
    _order = 'name'

    name = fields.Char('Synonym', required=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence')
    auto_attribute_id = fields.Many2one('product.auto.attribute', 'Attribute', ondelete='cascade', required=True)

class ProductAutoAttributevalue(models.Model):
    _name = "product.auto.attribute.value"
    _order = 'name'

    name = fields.Char('Value', required=True)
    auto_attribute_id = fields.Many2one('product.auto.attribute', 'Attribute', ondelete='cascade', required=True)

class ProductAutoAttributeLine(models.Model):
    _name = "product.auto.attribute.line"
    _rec_name = 'auto_attribute_id'

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', ondelete='cascade', required=True)
    auto_attribute_id = fields.Many2one('product.auto.attribute', 'Attribute', ondelete='restrict', required=True)
    value_ids = fields.Many2many('product.auto.attribute.value', string='Attribute Values')

    @api.constrains('value_ids', 'auto_attribute_id')
    def _check_valid_attribute(self):
        if any(line.value_ids > line.auto_attribute_id.value_ids for line in self):
            raise ValidationError(_('Error ! You cannot use this attribute with the following value.'))
        return True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            new_args = ['|', ('auto_attribute_id', operator, name), ('value_ids', operator, name)]
        else:
            new_args = args
        return super(ProductAutoAttributeLine, self).name_search(name=name, args=new_args, operator=operator, limit=limit)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    auto_attribute_line_ids = fields.One2many('product.auto.attribute.line', 'product_tmpl_id', 'Attributes')
    item_specific_line_ids = fields.One2many('product.item.specific.line', 'product_tmpl_id', 'Item Specifics')

    @api.multi
    def action_product_attribute_line_filtered_by_product(self):
        self.ensure_one()
        action = self.env.ref('product_auto_attributes.action_product_auto_attribute_line')
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

    @api.multi
    def action_product_item_specific_line_filtered_by_product(self):
        self.ensure_one()
        action = self.env.ref('product_auto_attributes.action_product_item_specific_line')
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

class ProductItemSpecificAttribute(models.Model):
    _name = "product.item.specific.attribute"
    _description = "Product Item Specific Attribute"
    _order = 'name'

    name = fields.Char('Name', required=True)
    listing_specific = fields.Boolean('Listing-specific?', help="e.g. Brand, MPN. New values entered through the wizard will not update existing values in the system if attribute is listing-specific.")
    value_ids = fields.One2many('product.item.specific.value', 'item_specific_attribute_id', 'Values', copy=True)
    item_line_ids = fields.One2many('product.item.specific.line', 'item_specific_attribute_id', 'Lines')
    auto_attribute_ids = fields.Many2many('product.auto.attribute', 'product_att_specific_rel', 'specific_id', 'att_id', 'Linked Auto Attributes')

class ProductItemSpecificValue(models.Model):
    _name = "product.item.specific.value"
    _order = 'name'

    name = fields.Char('Value', required=True)
    item_specific_attribute_id = fields.Many2one('product.item.specific.attribute', 'Attribute', ondelete='cascade', required=True)

class ProductItemSpecificLine(models.Model):
    _name = "product.item.specific.line"
    _rec_name = 'item_specific_attribute_id'

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', ondelete='cascade', required=True)
    item_specific_attribute_id = fields.Many2one('product.item.specific.attribute', 'Attribute', ondelete='restrict', required=True)
    value_id = fields.Many2one('product.item.specific.value', string='Attribute Value')

    @api.constrains('value_id', 'item_specific_attribute_id')
    def _check_valid_item_specific_attribute(self):
        if any(line.value_id not in line.item_specific_attribute_id.value_ids for line in self):
            raise ValidationError(_('Error ! You cannot use this attribute with the following value.'))
        return True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            new_args = ['|', ('item_specific_attribute_id', operator, name), ('value_id', operator, name)]
        else:
            new_args = args
        return super(ProductItemSpecificLine, self).name_search(name=name, args=new_args, operator=operator, limit=limit)
