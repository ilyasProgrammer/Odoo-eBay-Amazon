# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from datetime import datetime, timedelta
from pytz import timezone
import xml.etree.ElementTree as ET
import urllib

import logging

_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    show_shipping_info = fields.Boolean('Show Shipping Info')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_order_id = fields.Many2one('purchase.order', 'Rerouted to PO')
    show_shipping_info = fields.Boolean(related='picking_type_id.show_shipping_info')
    dropshipper_code = fields.Selection([], 'Dropshipper Code', related='partner_id.dropshipper_code')
    pfg_order_id = fields.Char('PFG Order ID')

    @api.multi
    def get_pfg_tracking_info(self):
        self.ensure_one()
        config = self.env['purchase.order'].get_pfg_config()
        request_header = self.env['purchase.order'].get_pfg_request_header(config['username'], config['password'])
        if self.purchase_id.vendor_order_id:
            body = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
            body += request_header
            body += '<soap:Body><GetOrderByQuote xmlns="http://usautoparts.com">'
            body += '<usa:QuoteID>%s</usa:QuoteID>' % self.purchase_id.vendor_order_id
            body += '</GetOrderByQuote></soap:Body></soap:Envelope>'
            url = config['base_endpoint'] + '/wosCustomerService.php'
            headers = {'content-type': 'application/soap+xml'}
            _logger.info('%s' % body)
            response = urllib.urlopen(url, data=body).read()
            _logger.info('%s' % response)
            tree = ET.fromstring(response)

            order = {}

            for n1 in tree.getchildren():
                if n1.tag.endswith('Body'):
                    for n2 in n1.getchildren():
                        if n2.tag.endswith('GetOrderByQuoteResponse'):
                            for n3 in n2.getchildren():
                                if n3.tag.endswith('order'):
                                    order['parts'] = []
                                    for n4 in n3.getchildren():
                                        if n4.tag.endswith('order_status'):
                                            order['order_status'] = n4.text
                                        elif n4.tag.endswith('total_total'):
                                            order['total'] = n4.text
                                        elif n4.tag.endswith('parts'):
                                            part = {'shipping':[]}
                                            for n5 in n4.getchildren():
                                                if n5.tag.endswith('sku'):
                                                    part['sku'] = n5.text
                                                elif n5.tag.endswith('shipping'):
                                                    shipping = {}
                                                    for n6 in n5.getchildren():
                                                        if n6.tag.endswith('shipping_method'):
                                                            shipping['shipping_method'] = n6.text
                                                        elif n6.tag.endswith('tracking_number'):
                                                            shipping['tracking_number'] = n6.text
                                                    part['shipping'].append(shipping)
                                            order['parts'].append(part)

            _logger.info("\nPO: %s Date: %s  \nOrder data: %s" % (self.purchase_id, self.create_date, order))

            if 'order_status' in order:
                if order['order_status'] == 'Complete':
                    vals = {}
                    vals['tracking_number'] = order['parts'][0]['shipping'][0]['tracking_number']
                    if order['parts'][0]['shipping'][0].get('shipping_method'):
                        shipping_method = order['parts'][0]['shipping'][0]['shipping_method']
                        if shipping_method == 'FDX':
                            carrier_id = self.env['ship.carrier'].search([('name', '=', 'FedEx')], limit=1)
                            if carrier_id:
                                vals['carrier_id'] = carrier_id.id
                    self.write(vals)
                    _logger.info("\nTracking number updated: %s  for: %s Date:%s" % (vals['tracking_number'], self, self.create_date))
                    message = _("Tracking number received from %s." % (self.partner_id.name, ))
                    self.message_post(body=message)
                    return True
                elif order['order_status'] == 'Deleted':
                    self.purchase_id.button_cancel()
                    self.purchase_id.button_draft()
                    self.purchase_id.write({'vendor_order_id': 'ERROR'})
                    _logger.warning("Order status deleted. PO: %s Picking: %s" % (self.purchase_id, self))
                    message = _("PO was rejected by %s." % (self.purchase_id.partner_id.name, ))
                    self.purchase_id.message_post(body=message)
                    return False

    @api.model
    def cron_pfg_get_tracking_numbers(self, force_run):
        self.env['slack.calls'].notify_slack('[ODOO] Get Tracking Numbers for PFG Orders', 'Started at %s' % datetime.utcnow())
        # Do not run cron between Saturday 6AM and Monday 6AM
        usnow = datetime.now(timezone('US/Eastern'))
        hour = usnow.hour
        weekday = usnow.weekday()
        if not force_run and (weekday >= 5 and hour > 6) or (weekday == 0 and hour <= 6):
            _logger.info('Will not get PFG tracking numbers this time because it is a weekend.')
            return
        now = (datetime.now() - timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M:%S')
        from_date = '2017-04-19 00:00:00'
        pickings = self.search([('create_date', '>=', from_date), ('create_date', '<=', now), ('tracking_number', '=', False), ('state', '=', 'assigned'), ('partner_id.dropshipper_code', '=', 'pfg')], order='create_date')
        pick_no_tracks = len(pickings)
        pick_track_set = 0
        pick_track_unset = 0
        for picking in pickings:
            _logger.info('\nTrying to get tracking number for %s' % picking.purchase_id.name)
            res = picking.get_pfg_tracking_info()
            if res:
                pick_track_set += 1
            else:
                pick_track_unset += 1
            self.env.cr.commit()
        opsyst_info_channel = self.env['ir.config_parameter'].get_param('slack_odoo_opsyst_info_channel_id')
        attachment = {
            'color': '#7CD197',
            'fallback': 'Tracking numbers report',
            'title': 'Period from %s to %s' % (str(from_date), str(now)),
            'text': 'Total drop pickings: %s \nTracks received for: %s \nNo tracks for: %s' % (pick_no_tracks, pick_track_set, pick_track_unset)
        }
        self.env['slack.calls'].notify_slack('[ODOO] Get Tracking Numbers for PFG Orders', 'Tracking numbers report', opsyst_info_channel, attachment)
        self.env['slack.calls'].notify_slack('[ODOO] Get Tracking Numbers for PFG Orders', 'Ended at %s' % datetime.utcnow())

    @api.multi
    def button_reroute_to_dropship(self):
        for picking in self:
            sale_id = picking.sale_id
            line = sale_id.order_line[0]
            query = """
                SELECT ALT.InventoryID, PR.Cost , INV.MfgID
                FROM InventoryAlt ALT
                LEFT JOIN Inventory INV on ALT.InventoryIDAlt = INV.InventoryID
                LEFT JOIN InventoryMiscPrCur PR ON INV.InventoryID = PR.InventoryID
                WHERE INV.MfgID IN (16,17,21,35,36,37,38,39) AND INV.QtyOnHand >= %s AND ALT.InventoryID = %s
            """ % (line.product_uom_qty, line.product_id.inventory_id)
            result = self.env['sale.order'].autoplus_execute(query)
            if not result:
                vendor_id = self.env['res.partner'].browse([6662])
            if result:
                result = sorted(result, key=lambda k: k['Cost'])
                mfg_id = result[0].get('MfgID')
                if mfg_id in [17, 21]:
                    vendor_id = self.env.ref('sale_dropship.partner_lkq')
                else:
                    vendor_id = self.env.ref('sale_dropship.partner_pfg')
            fpos = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(vendor_id.id)
            purchase_order = self.env['purchase.order'].create({
                'partner_id': vendor_id.id,
                'picking_type_id': self.env['stock.picking.type'].search([('name', 'ilike', 'dropship')]).id,
                'company_id': picking.company_id.id,
                'currency_id': vendor_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
                'dest_address_id': line.order_id.partner_id.id,
                'origin': line.order_id.name,
                'payment_term_id': vendor_id.property_supplier_payment_term_id.id,
                'date_order': fields.Datetime.now(),
                'fiscal_position_id': fpos,
                'sale_id': sale_id.id
            })
            for l in sale_id.order_line:
                purchase_order_line = self.env['purchase.order.line'].create({
                    'name': l.product_id.display_name,
                    'product_qty': l.product_uom_qty,
                    'product_id': l.product_id.id,
                    'product_uom': l.product_id.uom_po_id.id,
                    'price_unit': float(result[0].get('Cost')) if result else 1.0,
                    'date_planned': fields.Datetime.now(),
                    'order_id': purchase_order.id,    
                })
            sale_id.write({ 'purchase_order_id': purchase_order.id })
            for p in sale_id.picking_ids:
                p.write({ 'purchase_order_id': purchase_order.id })
                p.action_cancel()
