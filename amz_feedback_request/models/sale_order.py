# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ship_date = fields.Datetime('Date Shipped')
    message_state = fields.Selection([('none', 'None'), ('thank', 'Thank you message'), ('feedback', 'Feedback request message')], 'Messaging Status', default='none', copy=False)

    @api.model
    def amz_resend_feedback_request_mail(self, name, asin, email):
        _logger.info('Sending feedback request mail to %s' % name)
        feedback_request_template = self.env.ref('amz_feedback_request.email_resend_amz_feedback_request')
        feedback_request_template.with_context(
            name=name,
            asin=asin,
            email=email
        ).send_mail(20000, force_send=True)
        return True

    @api.multi
    def amz_send_thank_you_mail(self):
        if self.store_id.site == 'amz':
            thank_you_template = self.env.ref('amz_feedback_request.email_amz_thank_you')
            if thank_you_template:
                titles = ''
                titles_list = self.order_line.mapped('title')
                for title in titles_list:
                    if title:
                        titles += title + ', '
                if titles:
                    titles = titles[:-2]
                    self.with_context({'titles': titles}).message_post_with_template(thank_you_template.id)
            self.write({'message_state': 'thank'})

    @api.multi
    def amz_send_feedback_request_mail(self):
        _logger.info('Sending feedback request mail to %s' %self.name)
        feedback_request_template = self.env.ref('amz_feedback_request.email_amz_feedback_request')
        mapms = self.order_line.filtered(lambda l: l.item_id and l.item_id.startswith('MAPM')).mapped('item_id')
        for mapm in mapms:
            lines = self.order_line.filtered(lambda l: l.item_id == mapm)
            if lines:
                self.with_context({'title': lines[0].title, 'mapm': True, 'asin': lines[0].asin }).\
                    message_post_with_template(feedback_request_template.id)
        self.write({'message_state': 'feedback'})

    @api.multi
    def button_split_kits(self):
        self.ensure_one()
        if not self.has_kit:
            return
        for line in self.order_line:
            if line.product_id.bom_ids:
                # if line.product_id.qty_available - line.product_id.outgoing_qty >= line.product_uom_qty:
                #     continue
                if self.check_kit_availability(line):
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
                        'kit_line_id': kit_line_id.id,
                        'item_id': line.item_id,
                        'asin': line.asin,
                        'title': line.title
                    })
                line.unlink()

    def check_kit_availability(self, line):
        query = """
                   SELECT QUANT.qty,  LOC.id, LOC.complete_name
                   FROM stock_quant QUANT
                   LEFT JOIN stock_location LOC
                   ON QUANT.location_id = LOC.id
                   LEFT JOIN product_product PRODUCT
                   ON PRODUCT.id = QUANT.product_id
                   LEFT JOIN product_template TEMPLATE ON TEMPLATE.id = PRODUCT.product_tmpl_id
                   WHERE LOC.usage = 'internal' AND QUANT.qty > 0 AND QUANT.reservation_id IS NULL
                   AND (TEMPLATE.oversized = False OR TEMPLATE.oversized IS NULL)
                   AND PRODUCT.id = %s
                   AND QUANT.qty >= %s
                   AND LOC.name NOT IN ('Output', 'Amazon FBA')
                   """ % (line.product_id.id, line.product_uom_qty)
        self.env.cr.execute(query)
        quants = self.env.cr.fetchall()
        return quants


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    asin = fields.Char('ASIN')
    title = fields.Char('Title')
