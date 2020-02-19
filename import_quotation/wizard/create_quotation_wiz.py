# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreateQuotationWizard(models.TransientModel):
    _name = 'create.quotation.wizard'

    customer_name = fields.Char(required=True)
    street = fields.Char(required=True)
    street2 = fields.Char()
    city = fields.Char(required=True)
    state = fields.Char(required=True)
    zip = fields.Char(required=True)
    phone = fields.Char()
    store_code = fields.Char(required=True)
    web_order_id = fields.Char()
    route = fields.Char()
    sku1 = fields.Char(required=True)
    qty1 = fields.Float(default=1.0, required=True)
    price1 = fields.Float()
    sku2 = fields.Char()
    qty2 = fields.Float()
    price2 = fields.Float()
    sku3 = fields.Char()
    qty3 = fields.Float()
    price3 = fields.Float()
    sku4 = fields.Char()
    qty4 = fields.Float()
    price4 = fields.Float()
    sku5 = fields.Char()
    qty5 = fields.Float()
    price5 = fields.Float()

    @api.multi
    def create_quotation(self):
        self.ensure_one()
        customer_domain = []
        lines = []
        ResPartner = self.env['res.partner']
        SaleStore = self.env['sale.store']
        state = self.env['res.country.state'].search([('code', '=', self.state), ('country_id.code', '=', 'US')])
        if not state:
            raise UserError(_('%s does not match any state.' % (self.state)))

        route_id = False
        if self.route and self.route not in ('LKQ', 'PFG', 'WH'):
            raise UserError(_('%s is not a valid route.' % (self.route)))
        else:
            if self.route == 'LKQ':
                route_id = self.env.ref('sale_dropship.route_lkq_drop_shipping').id
            elif self.route == 'PFG':
                route_id = self.env.ref('sale_dropship.route_pfg_drop_shipping').id
            elif self.route == 'WH':
                warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
                route_id = warehouse_id.delivery_route_id.id
        if self.customer_name:
            customer_domain.append(('name', '=', self.customer_name))
        if self.street:
            customer_domain.append(('street', '=', self.street))
        if self.street2:
            customer_domain.append(('street2', '=', self.street2))
        if self.city:
            customer_domain.append(('city', '=', self.city))
        if self.state:
            customer_domain.append(('state_id', '=', state.id))
        if self.zip:
            if len(self.zip) < 5:
                raise UserError(_('%s is not a valid zip.' % (self.zip)))
            customer_domain.append(('zip', '=', self.zip))
        if self.phone:
            customer_domain.append(('phone', '=', self.phone))

        if self.sku1 and self.qty1 > 0:
            product = SaleStore._get_product(self.sku1)
            if product:
                lines.append((0, 0, {'product_id': product.id, 'product_uom_qty': self.qty1, 'price_unit': self.price1, 'route_id': route_id}))
            else:
                raise UserError(_('%s does not match any sku.' % (self.sku1)))
        if self.sku2 and self.qty2 > 0:
            product = SaleStore._get_product(self.sku2)
            if product:
                lines.append((0, 0, {'product_id': product.id, 'product_uom_qty': self.qty2, 'price_unit': self.price2, 'route_id': route_id}))
            else:
                raise UserError(_('%s does not match any sku.' % (self.sku2)))
        if self.sku3 and self.qty3 > 0:
            product = SaleStore._get_product(self.sku3)
            if product:
                lines.append((0, 0, {'product_id': product.id, 'product_uom_qty': self.qty3, 'price_unit': self.price3, 'route_id': route_id}))
            else:
                raise UserError(_('%s does not match any sku.' % (self.sku3)))
        if self.sku4 and self.qty4 > 0:
            product = SaleStore._get_product(self.sku4)
            if product:
                lines.append((0, 0, {'product_id': product.id, 'product_uom_qty': self.qty4, 'price_unit': self.price4, 'route_id': route_id}))
            else:
                raise UserError(_('%s does not match any sku.' % (self.sku4)))
        if self.sku5 and self.qty5 > 0:
            product = SaleStore._get_product(self.sku5)
            if product:
                lines.append((0, 0, {'product_id': product.id, 'product_uom_qty': self.qty5, 'price_unit': self.price5, 'route_id': route_id}))
            else:
                raise UserError(_('%s does not match any sku.' % (self.sku5)))

        partner = ResPartner.search(customer_domain, limit=1)
        if not partner:
            vals = {
                'name': self.customer_name,
                'street': self.street,
                'street2': self.street2,
                'city': self.city,
                'state_id': state.id if state else False,
                'zip': self.zip,
                'phone': self.phone,
                'country_id': state.country_id.id
            }
            partner = ResPartner.create(vals)
        store = SaleStore.search([('code', '=', self.store_code)], limit=1)
        if not store:
            raise UserError(_('%s does not match any store code.' % (self.store_code)))

        order_vals = {
            'partner_id': partner.id,
            'store_id': store.id if store else False,
            'web_order_id': self.web_order_id,
            'order_line': lines,
            'uploaded_from_file': True
        }
        order = self.env['sale.order'].create(order_vals)
        if self.route in ('LKQ', 'PFG'):
            order.action_confirm()
        else:
            if len(order.order_line) == 1:
                order.button_set_dimension_from_first_order_line()
        return order
