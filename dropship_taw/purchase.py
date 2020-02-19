# -*- coding: utf-8 -*-

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def cron_taw_send_purchase_orders(self):
        po_ids_to_send = self.search([('dropshipper_code', '=', 'taw'), ('vendor_order_id', '=', False), ('state', '=', 'draft'), ('dest_address_id', '!=', False)])
        po_ids_to_send.queue_for_sending_to_vendor()
        for po_id in po_ids_to_send:
            if po_id.sale_id.has_duplicates():
                continue
            _logger.info('Sending %s to vendor' % po_id.name)
            res = po_id.taw_process_order()
            if res:
                # po_id.write({'vendor_order_id': res['quote_id']})  # Usman should do it himself
                message = "PO sent to vendor from scheduler. New Order ID from %s: %s." % (po_id.partner_id.name, po_id.vendor_order_id)
                po_id.button_confirm()
                po_id.message_post(body=message)
                self.env.cr.commit()
            po_id.write({'sent_to_vendor': False})
        opsyst_info_channel = self.env['ir.config_parameter'].get_param('slack_odoo_opsyst_info_channel_id')
        attachment = {
                'color': '#7CD197',
                'fallback': 'TAW POs report',
                'title': 'Total orders sent: %s' % len(po_ids_to_send),
                'text': 'Sent POs to TAW (Usman Orders table)'
            }
        self.env['slack.calls'].notify_slack('[ODOO] Process TAW POs', 'TAW POs report', opsyst_info_channel, attachment)

    @api.multi
    def taw_process_order(self):
        #  Just write into Usmans table
        taw_partner_id = 316421
        parts = ''
        qtys = ''
        for r in self.order_line:
            pricelist_id = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', r.product_id.product_tmpl_id.id),
                ('name', '=', taw_partner_id)
            ])
            if pricelist_id:
                parts += pricelist_id.product_code + '<!>'
            else:
                parts += r.product_id.product_tmpl_id.name + '<!>'
            qtys += str(r.product_qty) + '<!>'
        parts = parts[:-3]
        qtys = qtys[:-3]
        buyer = self.sale_id.partner_id
        qry = """INSERT INTO TAWOrdersProcessing.dbo.Orders 
                 (PartNo, Qty, PhoneNumber, FullName, 
                 StreetAddress, 
                 CityAddress, StateAddress, ZipAddress, PONumber, OrderStatus)
                 VALUES ('%s','%s','%s','%s','%s','%s','%s','%s','%s',%s)
                 """ % (parts, qtys, buyer.phone, buyer.name,
                        buyer.street if buyer.street else '' + buyer.street2 if buyer.street2 else '',
                        buyer.city, buyer.state_id.code, buyer.zip, self.id, 0)
        _logger.info('\n\nTAW AUTOPLUS QRY: %s', qry)
        try:
            result = self.env['sale.order'].autoplus_execute(qry, insert=True)
            if result:
                _logger.info('Pushed into TAW PO into TAWOrdersProcessing. PO id: %s', self.id)
                return True
            else:
                _logger.warning('Error processing TAW PO. PO id: %s', self.id)
                return False
        except Exception as e:
            _logger.warning(e)
