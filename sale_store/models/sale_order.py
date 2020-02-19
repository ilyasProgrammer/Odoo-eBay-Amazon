# -*- coding: utf-8 -*-

import pymssql
from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    web_order_id = fields.Char(string="Web Order ID", required=True, help="Order ID as provided by the web store")
    ebay_sales_record_number = fields.Char(string="eBay Record Number", help="Sales record number for eBay orders")
    store_id = fields.Many2one('sale.store', string='Web Store')
    weight = fields.Float(string="Weight", digits=dp.get_precision('Stock Weight'))
    length = fields.Float(string="Length", digits=dp.get_precision('Product Dimension'))
    width = fields.Float(string="Width", digits=dp.get_precision('Product Dimension'))
    height = fields.Float(string="Height", digits=dp.get_precision('Product Dimension'))
    service_id = fields.Many2one('ship.carrier.service', 'Service Name', help="Service used by the shipment")
    carrier_id = fields.Many2one('ship.carrier', 'Carrier', related='service_id.carrier_id')
    package_id = fields.Many2one('ship.carrier.package', 'Package')
    rate = fields.Float(string="Shipping Price")
    has_dimension_warning = fields.Boolean('Has dimension warning?', compute='_get_dimension_warning')
    exceeds_limits = fields.Boolean(string="Exceeds Limits?")
    has_kit = fields.Boolean('Has kit?', compute='_get_has_kit')
    kit_line_ids = fields.One2many('sale.order.line.kit', 'sale_order_id', 'Kit Order Lines')
    show_btn = fields.Boolean(compute="_check_orderlines", help="Technical field to hide update autoplus button if line is more than one")
    related_ids = fields.Many2many('sale.order', compute='_compute_related', store=False)
    order_url = fields.Char('Order URL', compute='_get_order_url')

    @api.one
    def _compute_related(self):
        if self.web_order_id:
            related = self.env['sale.order'].search([('web_order_id', '=', self.web_order_id), ('id', '!=', self.id)])
            if related:
                self.related_ids = related.ids

    @api.multi
    @api.depends('name', 'store_id', 'web_order_id')
    def _get_order_url(self):
        for l in self:
            if l.store_id.site == 'ebay' and l.web_order_id:
                if '-' in l.web_order_id:
                    transaction = l.web_order_id.split('-')[1]
                    item = l.web_order_id.split('-')[0]
                    l.order_url = 'https://k2b-bulk.ebay.com/ws/eBayISAPI.dll?EditSalesRecord&transid=%s&&itemid=%s' % (transaction, item)
            elif l.store_id.site == 'amz' and l.web_order_id:
                l.order_url = 'https://sellercentral.amazon.com/hz/orders/details?_encoding=UTF8&orderId=' + l.web_order_id

    @api.multi
    @api.onchange('service_id')
    def onchange_service_id(self):
        if not self.service_id:
            return {'domain': {'package_id': []}}
        return {'domain': {'package_id': [('carrier_id.id', '=', self.carrier_id.id)]}}

    @api.multi
    @api.depends('order_line', 'product_id')
    def _get_has_kit(self):
        for so in self:
            for line in so.order_line:
                if line.product_id.bom_ids:
                    has_kit = True
                    break
            else:
                has_kit = False
            so.has_kit = has_kit

    @api.multi
    def button_split_kits(self):
        self.ensure_one()
        if not self.has_kit:
            return
        for line in self.order_line:
            if line.product_id.bom_ids:
                if line.product_id.qty_available - line.product_id.outgoing_qty >= line.product_uom_qty:
                    continue
                kit_line_id = self.env['sale.order.line.kit'].create({
                    'sale_order_id': self.id,
                    'web_orderline_id': line.web_orderline_id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_qty,
                    'price_unit': line.price_unit
                })
                sorted_bom_ids = line.product_id.bom_ids.sorted(key=lambda r: r.sequence)

                bom_id = sorted_bom_ids[0]
                bom_total_qty = sum([bom_line.product_qty for bom_line in bom_id.bom_line_ids])

                for bom_line in bom_id.bom_line_ids:
                    product_id = bom_line.product_id
                    if product_id.mfg_code != 'ASE' and product_id.alternate_ids.filtered(lambda p: p.mfg_code == 'ASE'):
                        product_id = product_id.alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')[0]
                    new_line_id = self.env['sale.order.line'].create({
                        'order_id': self.id,
                        'product_id': product_id.id,
                        'product_uom_qty': bom_line.product_qty * line.product_uom_qty,
                        'web_orderline_id': line.web_orderline_id,
                        'price_unit': line.price_unit * (bom_line.product_qty / bom_total_qty),
                        'kit_line_id': kit_line_id.id
                    })
                line.unlink()

    @api.multi
    @api.depends('order_line', 'order_line.product_id')
    def _get_dimension_warning(self):
        for so in self:
            has_dimension_warning = False
            dim = [so.length, so.width, so.height, so.weight]
            for d in dim:
                if d == 0.0:
                    has_dimension_warning = True
                    break
            if not has_dimension_warning and so.order_line:
                p = so.order_line[0].product_id
                p_dim = [p.length, p.width, p.height, p.weight]
                if p_dim != dim:
                    has_dimension_warning = True
            so.has_dimension_warning = has_dimension_warning

    @api.multi
    @api.depends('order_line')
    def _check_orderlines(self):
        for order in self:
            order.show_btn = True if len(order.order_line) == 1 else False

    @api.multi
    def button_set_dimension_from_first_order_line(self):
        for so in self:
            if so.order_line:
                p = so.order_line[0].product_id
                dim = [p.length, p.width, p.height, p.weight]
                for d in dim:
                    if d == 0.0:
                        p.button_sync_with_autoplus(raise_exception=False)
                        break
                so.write({'length': p.length, 'width': p.width, 'height': p.height, 'weight': p.weight})

    @api.multi
    def update_autoplus(self):
        SaleOrderLine = self.env['sale.order.line']
        for so in self:
            if so.order_line:
                product = so.order_line[0].product_id
                product.write({'length': so.length, 'width': so.width, 'height': so.height, 'weight': so.weight})
                product.update_autoplus()
                sale_orders = SaleOrderLine.search([('product_id', '=', product.id), ('order_id.state', '!=', 'done')]).mapped('order_id')
                sale_orders.button_set_dimension_from_first_order_line()
        return True

    @api.model
    def autoplus_execute(self, query, insert=False):
        result = []
        params = self.env['ir.config_parameter'].sudo()
        server = params.get_param('autoplus_server')
        db = params.get_param('autoplus_db_name')
        username = params.get_param('autoplus_username')
        password = params.get_param('autoplus_password')
        conn = pymssql.connect(server, username, password, db)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query)
        if not insert:
            if not self.env.context.get('update'):
                result = cursor.fetchall()
        conn.commit()
        cursor.close()
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    web_orderline_id = fields.Char(string="Web Order Line ID", help="Order Line ID as provided by the web store")
    kit_line_id = fields.Many2one('sale.order.line.kit', 'Kit Line Origin', help="Kit that was originally ordered by customer")
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date')
    store_id = fields.Many2one('sale.store', related='order_id.store_id', string='Store')


class SaleOrderLineKit(models.Model):
    _name ='sale.order.line.kit'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_qty = fields.Integer('Quantity', required=True)
    web_orderline_id = fields.Char('Web Order Line ID', help="Order Line ID as provided by the web store")
    sale_order_id = fields.Many2one('sale.order', 'Sale Order ID', required=True)
    price_unit = fields.Float('Unit Price', digits=dp.get_precision('Product Price'))
