# -*- coding: utf-8 -*-

import base64
import csv
import logging
import xml.etree.ElementTree as ET
import urllib
from cStringIO import StringIO
from datetime import datetime
from pytz import timezone
from suds.client import Client
from suds.xsd.doctor import Import, ImportDoctor
import unicodedata
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LKQRequest():

    def __init__(self):
        imp = Import('http://www.w3.org/2001/XMLSchema', location='http://www.w3.org/2001/XMLSchema.xsd')
        imp.filter.add('http://schemas.microsoft.com/2003/10/Serialization/')
        imp.filter.add('http://schemas.microsoft.com/2003/10/Serialization/Arrays')
        imp.filter.add('http://schemas.datacontract.org/2004/07/LKQIntegrationService.Core.Entities')
        imp.filter.add('http://schemas.datacontract.org/2004/07/LKQIntegrationService.Core.Ordering.Entities')
        imp.filter.add('LKQCorp.LKQIntegrationService')
        doctor = ImportDoctor(imp)
        self.client = Client('https://lkqintegration.ekeyconnect.com/Ordering.svc?singleWsdl', doctor=doctor)

    def process_order(self, config, order, line_alternates):
        UserRequestInfo = self.client.factory.create('ns1:UserInformation')
        UserRequestInfo.AccountNumber = config.get('AccountNumber', False)
        UserRequestInfo.UserName = config.get('UserName', False)
        UserRequestInfo.UserPassword = config.get('UserPassword', False)
        UserRequestInfo.VerificationCode = config.get('VerificationCode', False)
        UserRequestInfo.BusinessTypeForAccountNumber = 'Aftermarket'

        ShipToAddress = self.client.factory.create('ns2:OrderShipToAddress')
        ShipToAddress.AddressLine1 = order.dest_address_id.street
        ShipToAddress.AddressLine2 = order.dest_address_id.street2 or ''
        ShipToAddress.City = order.dest_address_id.city
        ShipToAddress.Country = order.dest_address_id.country_id.code
        ShipToAddress.PhoneNumber = order.dest_address_id.phone or '3136108402'
        ShipToAddress.PostalCode = order.dest_address_id.zip
        ShipToAddress.StateProvince = order.dest_address_id.state_id.code
        ShipToAddress.ShipToCode = 'M'
        ShipToAddress.ShipToCodeType = 'Manual'
        ShipToAddress.ShipToName = order.dest_address_id.name
        ShipToAddress.ShipVia = 39

        OrderingRequest = self.client.factory.create('ns2:OrderingRequest')
        OrderingRequest.UserRequestInfo = UserRequestInfo
        OrderingRequest.AMPurchaseOrderNumber = order.name
        OrderingRequest.ContactName = order.dest_address_id.name
        OrderingRequest.CopyMethod = 'Email'
        OrderingRequest.ShipToAddress = ShipToAddress
        OrderingRequest.LineItemTypes = 'Aftermarket'
        OrderingRequest.EmailAddress = 'xtremejeeperz@gmail.com'
        OrderingRequest.PartnerCode = config.get('PartnerCode', False)

        ArrayOfOrderLineItem = self.client.factory.create('ns2:ArrayOfOrderLineItem')
        LineItems = []
        for line in order.order_line:
            LineItem = self.client.factory.create('ns2:OrderLineItem')
            LineItem.PartNumber = line_alternates[line.id]
            LineItem.Quantity = int(line.product_qty)
            LineItem.UnitOfMeasure = 'EA'
            LineItems.append(LineItem)
        ArrayOfOrderLineItem.OrderLineItem = LineItems
        OrderingRequest.LineItems = ArrayOfOrderLineItem
        _logger.info('Sent to LKQ: %s' % OrderingRequest)
        self.response = self.client.service.CreateOrder(request=OrderingRequest)
        if self.response.IsSuccessful:
            for result in self.response.Value:
                return result[1]
        else:
            return False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sale_line_id = fields.Many2one('sale.order.line', 'Sale Order Line')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    dropshipper_code = fields.Selection([], 'Dropshipper Code', related='partner_id.dropshipper_code')
    is_domestic = fields.Boolean('Domestic?', related='partner_id.is_domestic')
    sent_to_vendor = fields.Boolean('Sent to Vendor')
    vendor_order_id = fields.Char('Vendor Order ID')
    sale_id = fields.Many2one('sale.order', string="Sale Order")
    store_id = fields.Many2one('sale.store', related="sale_id.store_id", string="Store")

    @api.model
    def get_pfg_config(self):
        ParamsObj = self.env['ir.config_parameter'].sudo()
        base_endpoint = 'http://woscustomerservices-staging.usautoparts.com'
        env = ParamsObj.get_param('pfg_environment')
        if env == 'prod':
            # base_endpoint = 'https://wosinsservice.usautoparts.com'
            base_endpoint = 'https://wosapiext.usautoparts.com'
        return dict(
            customer_id=ParamsObj.get_param('pfg_customer_id'),
            username=ParamsObj.get_param('pfg_user_name'),
            password=ParamsObj.get_param('pfg_password'),
            shipping_code=ParamsObj.get_param('pfg_shipping_code'),
            base_endpoint=base_endpoint
        )

    @api.model
    def get_pfg_request_header(self, username, password):
        request_header = '<soap:Header><Authentication xmlns="http://usautoparts.com">'
        request_header += '<Username>%s</Username>' %username
        request_header += '<Password>%s</Password>' %password
        request_header += '</Authentication></soap:Header>'
        return request_header

    @api.multi
    def pfg_check_inventory(self, part_numbers_list):
        config = self.get_pfg_config()
        request_header = self.get_pfg_request_header(config['username'], config['password'])
        parts = ''
        brand_dict = {}
        for part in part_numbers_list:
            brand_row = self.env['sale.order'].autoplus_execute("""
                SELECT Mfg.MfgName FROM Inventory INV
                LEFT JOIN Mfg ON Mfg.MfgID = INV.MfgID
                WHERE INV.PartNo = '%s' and INV.MfgID > 0
            """ % part['part_number'])
            try:
                _logger.info('\n\n BRAND ROW:%s', brand_row)
                _logger.info('\n\n part_number:%s', part['part_number'])
                brand = brand_row[0]['MfgName'].replace('-', ' ')
                parts += '<Parts>'
                parts += '<Sku>%s</Sku>' % part['part_number']
                parts += '<Brand>%s</Brand>' % brand or brand_row[0]['MfgName']
                parts += '<Quantity>%s</Quantity></Parts>' % part['qty']
                brand_dict[part['part_number']] = brand
            except Exception as e:
                _logger.error(e)
                continue

        body = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
        body += request_header
        body += '<soap:Body><CheckInventory xmlns="http://usautoparts.com">'
        body += '<usa:CustomerId>%s</usa:CustomerId>' % config['customer_id']
        body += parts
        body += '</CheckInventory></soap:Body></soap:Envelope>'
        url = config['base_endpoint'] + '/wosCustomerService.php'
        headers = {'content-type': 'application/soap+xml'}
        # url = 'https://wosservices.usautoparts.com/wosMerchantService.php?WSDL'
        _logger.info('\n\nPFG Check Inventory URL: %s' % url)
        _logger.info('\n\nPFG Check Inventory request body: %s' % body)
        response = urllib.urlopen(url, data=body).read()
        _logger.info('\n\nPFG Check Inventory responded: %s' % response)
        res = []
        tree = ET.fromstring(response)
        for n1 in tree.getchildren():
            if n1.tag.endswith('Body'):
                for n2 in n1.getchildren():
                    if n2.tag.endswith('CheckInventoryResponse'):
                        for n3 in n2.getchildren():
                            if n3.tag.endswith('Parts'):
                                for n4 in n3.getchildren():
                                    if n4.tag.endswith('Sku'):
                                        part_number = n4.text
                                    elif n4.tag.endswith('UnitCost'):
                                        cost = float(n4.text)
                                    elif n4.tag.endswith('maxAvailableStock'):
                                        qty = int(n4.text)
                                res.append({'part_number': part_number, 'cost': cost, 'qty': qty, 'brand': brand_dict[part_number]})
        return res

    @api.multi
    def pfg_process_order(self):
        slack_critical_channel_id = self.env['ir.config_parameter'].get_param('slack_critical_channel_id')
        self.ensure_one()
        line_alternates = {}
        part_numbers_list = []
        pfg_brands = ['BFHZ', 'REPL', 'STYL', 'NDRE', 'BOLT', 'EVFI']
        for line in self.order_line:
            PartNo = ''
            product_id = line.product_id
            if product_id.mfg_code == 'BFHZ':
                PartNo = product_id.part_number
            elif product_id.mfg_code == 'ASE':
                pfg_product_id = product_id.alternate_ids.filtered(lambda r: r.mfg_code in pfg_brands)
                if not pfg_product_id:
                    product_id.button_sync_with_autoplus(raise_exception=False)
                    pfg_product_id = product_id.alternate_ids.filtered(lambda r: r.mfg_code in pfg_brands)
                if pfg_product_id:
                    PartNo = pfg_product_id[0].part_number

            if not PartNo:
                return {'error': '%s does not have an alternate USAP SKU.' %product_id.name }
            else:
                line_alternates[line.id] = {'part_number': PartNo, 'qty': int(line.product_qty)}
                part_numbers_list.append(line_alternates[line.id])
        try:
            res = self.pfg_check_inventory(part_numbers_list)
        except Exception as e:
            _logger.error(e)
            return 'fail'

        for line in self.order_line:
            for r in res:
                if line_alternates[line.id]['part_number'] == r['part_number']:
                    if line_alternates[line.id]['qty'] > r['qty']:
                        return {'error': '%s does not have sufficient stock.' %line_alternates[line.id]['part_number'] }
                    else:
                        line_alternates[line.id]['cost'] = r['cost']
                        line_alternates[line.id]['brand'] = r['brand']
                    break

        Parts = ''
        for line in line_alternates:
             Parts += '<Parts>'
             Parts += '<Sku>%s</Sku>' % line_alternates[line]['part_number']
             Parts += '<BrandText>%s</BrandText>' % line_alternates[line].get('brand')
             Parts += '<Qty>%s</Qty>' % line_alternates[line]['qty']
             Parts += '<PartWarehouse>All</PartWarehouse>'
             Parts += '</Parts>'

        config = self.get_pfg_config()
        request_header = self.get_pfg_request_header(config['username'], config['password'])
        ship_person = self.dest_address_id.name.replace('&','and').encode('ascii','ignore')
        ship_address = self.dest_address_id.street.replace('&','and').encode('ascii','ignore')
        if self.dest_address_id.street2:
            ship_address += ' ' + self.dest_address_id.street2.replace('&','and').encode('ascii','ignore')
        ship_city = self.dest_address_id.city.encode('ascii','ignore')
        ship_state_code = self.dest_address_id.state_id.code
        ship_zip = self.dest_address_id.zip
        ship_country_code = self.dest_address_id.country_id.code
        phone = self.dest_address_id.phone or '3136108402'

        order_id = self.name
        if self.vendor_order_id == 'ERROR':
            order_id = self.name + '-' + datetime.now().strftime('%H%M%S')

        body = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
        body += request_header
        body += '<soap:Body><SaveCustomersQuote xmlns="http://usautoparts.com"><QuoteDS><QuoteDetails>'
        body += '<CustomerId>%s</CustomerId>' % config['customer_id']
        body += '<OrderId>%s</OrderId>' % order_id
        body += '<ShipContactPerson>%s</ShipContactPerson>' % ship_person
        body += '<ShipAddress>%s</ShipAddress>' % ship_address
        body += '<ShipCity>%s</ShipCity>' % ship_city
        body += '<ShipState>%s</ShipState>' % ship_state_code
        body += '<ShipZip>%s</ShipZip>' % ship_zip
        body += '<ShipCountry>%s</ShipCountry>' % ship_country_code
        body += '<ShipDayPhone1>%s</ShipDayPhone1>' % phone  # re.sub('[^A-Za-z0-9()-+]+', '', '+7(580) 782-3483\xe2\x80\xac</')  TODO ?
        body += '<CrossReferenceNumber>%s</CrossReferenceNumber>' % order_id
        body += '<ShippingMethod>%s</ShippingMethod>' % config['shipping_code']
        body += '</QuoteDetails>'
        body += Parts
        body += '</QuoteDS>'
        body += '</SaveCustomersQuote></soap:Body></soap:Envelope>'
        url = config['base_endpoint'] + '/wosCustomerService.php'
        headers = {'content-type': 'application/soap+xml'}
        _logger.info("\n\nPFG request: %s" % body)
        # Here sometimes some weird symbols appears that cant be decoded.
        # normalized = unicodedata.normalize('NFKD', body.replace(u'\xe2', u'').replace(u'\u202c', u'').replace(u'\u202d', u'').replace(u'\x80', '').replace(u'\xad', '').replace(u'\xac', ''))
        # normalized = body.decode('unicode_escape').encode('ascii', 'ignore')
        normalized = body.replace(u'\xa0', u'').replace(u'\xe2', u'').replace(u'\u202c', u'').replace(u'\u202d', u'').replace(u'\x80', '').replace(u'\xad', '').replace(u'\xac', '')
        normalized = ''.join([i if ord(i) < 128 else ' ' for i in normalized])
        _logger.info("\n\nPFG request normalized: %s" % normalized)
        # url = 'https://wosservices.usautoparts.com/wosMerchantService.php?WSDL'
        _logger.info("\n\nPFG URL: %s" % url)
        try:
            response = urllib.urlopen(url, data=normalized).read()
        except Exception as e:
            logging.error(e)
            attachment = {
                'color': '#DC3545',
                'fallback': 'PFG PO processing',
                'title': 'PFG PO processing',
                'text': 'Order: %s Error: %s' % (self.name, e)
            }
            self.env['slack.calls'].notify_slack('PFG PO processing', 'Error', slack_critical_channel_id, attachment)
            return {'error': e}
        _logger.info("\n\nPFG response: %s" % response)
        tree = ET.fromstring(response)
        quote_id = -1
        for n1 in tree.getchildren():
            if n1.tag.endswith('Body'):
                for n2 in n1.getchildren():
                    if n2.tag.endswith('SaveCustomersQuoteResponse'):
                        for n3 in n2.getchildren():
                            if n3.tag.endswith('QuoteID'):
                                quote_id = n3.text
                                break
        if quote_id != -1:
            return {'success': True, 'quote_id': quote_id}
        else:
            attachment = {
                'color': '#DC3545',
                'fallback': 'PFG PO processing',
                'title': 'PFG PO processing',
                'text': 'Order: %s Response: %s' % (self.name, response)
            }
            self.env['slack.calls'].notify_slack('PFG PO processing', 'Rejected', slack_critical_channel_id, attachment)
            return {'error': 'PFG rejected this order'}

    @api.multi
    def action_send_po_to_pfg_api(self, raise_exception=True):
        self.ensure_one()
        if self.dropshipper_code == 'pfg' and not self.vendor_order_id:
            for po in self:
                res = po.pfg_process_order()
                if 'success' in res:
                    self.write({'sent_to_vendor': True, 'vendor_order_id': res['quote_id']})
                else:
                    if raise_exception:
                        raise UserError(_('%s') % (res['error']))
                    else:
                        _logger.error('%s' %res['error'])
        elif self.sent_to_vendor:
            if raise_exception:
                raise UserError(_('This order is already sent to the vendor.'))
            else:
                _logger.info('This order is already sent to the vendor.')
        else:
            if raise_exception:
                raise UserError(_('This PO does not seem to have PFG set as the vendor.'))
            else:
                _logger.info('This PO does not seem to have PFG set as the vendor.')

    @api.multi
    def action_send_to_vendor_api(self):
        self.ensure_one()
        if self.vendor_order_id and self.vendor_order_id != 'ERROR':
            raise UserError(_('This PO was already sent to vendor.'))
        elif self.sent_to_vendor:
            raise UserError(_('This PO is currently queued to be sent to vendor.'))

        res = {}
        if self.dropshipper_code == 'lkq':
            res = self.lkq_process_order()
        elif self.dropshipper_code == 'pfg':
            res = self.pfg_process_order()

        if 'success' in res:
            self.write({'vendor_order_id': res['quote_id']})
            message = _("PO manually sent to vendor. New Order ID from %s: %s."
                %(self.partner_id.name, self.vendor_order_id))
            self.message_post(body=message)
        elif 'error' in res:
            raise UserError(_('%s.' %res['error']))

    @api.multi
    def lkq_process_order(self):
        self.ensure_one()
        ParamsObj = self.env['ir.config_parameter'].sudo()
        config = dict(
            AccountNumber = ParamsObj.get_param('lkq_account_number'),
            UserName = ParamsObj.get_param('lkq_user_name'),
            UserPassword = ParamsObj.get_param('lkq_user_password'),
            VerificationCode = ParamsObj.get_param('lkq_verification_code'),
            PartnerCode = ParamsObj.get_param('lkq_partner_code')
        )
        line_alternates = {}
        for line in self.order_line:
            product_id = line.product_id
            if product_id.mfg_code not in ['GMK', 'BXLD']:
                result = self.env['sale.order'].autoplus_execute("""
                    SELECT TOP 1 INV2.PartNo, INV2.QtyOnHand, PR.Cost
                    FROM Inventory INV
                    LEFT JOIN InventoryAlt ALT on ALT.InventoryID = INV.InventoryID
                    LEFT JOIN Inventory INV2 on ALT.InventoryIDAlt = INV2.InventoryID
                    LEFT JOIN InventoryMiscPrCur PR ON INV2.InventoryID = PR.InventoryID
                    WHERE INV2.MfgID IN (17,21) AND INV2.QtyOnHand > 0 AND INV.PartNo = '%s'
                    ORDER BY PR.Cost ASC
                """ %product_id.part_number)
                if result:
                    line_alternates[line.id] = result[0]['PartNo']
                else:
                    return {'error': '%s does not have an alternate LKQ SKU.' %product_id.name}
        srm = LKQRequest()
        quote_id = srm.process_order(config, self, line_alternates)
        if quote_id:
            return {'success': True, 'quote_id': quote_id}
        else:
            return {'error': 'LKQ rejected this order'}

    @api.model
    def cron_reroute_po_to_wh(self):
        po_ids = self.search([('dropshipper_code', 'in', ('pfg', 'lkq')), ('sent_to_vendor', '=', False), ('state', '=', 'draft')])
        for po_id in po_ids:
            for line in po_id.order_line:
                if po_id.product_id.qty_available>0:
                    _logger.info("Cancelling %s" %po_id.name)
                    po_id.button_cancel()
                    po_id.sale_id.action_cancel()
                    po_id.sale_id.action_draft()
                    self.env.cr.commit()
                    break

    @api.multi
    def queue_for_sending_to_vendor(self):
        self.write({'sent_to_vendor': True})
        self.env.cr.commit()

    @api.model
    def cron_pfg_send_purchase_orders(self):
        self.env['slack.calls'].notify_slack('[ODOO] Send POs to PFG', 'Started at %s' % datetime.utcnow())
        po_ids_to_send = self.search([('dropshipper_code', '=', 'pfg'), ('vendor_order_id', '=', False), ('state', '=', 'draft'), ('dest_address_id', '!=', False)])
        po_ids_to_send.queue_for_sending_to_vendor()
        confirmed = 0
        declined = 0
        if len(po_ids_to_send):
            for po_id in po_ids_to_send:
                if po_id.sale_id.has_duplicates():
                    continue
                _logger.info('Sending %s to vendor' % po_id.name)
                res = po_id.pfg_process_order()
                if 'success' in res:
                    po_id.write({'vendor_order_id': res['quote_id']})
                    message = _("PO sent to vendor from scheduler. New Order ID from %s: %s." % (po_id.partner_id.name, po_id.vendor_order_id))
                    po_id.message_post(body=message)
                    po_id.button_confirm()
                    confirmed += 1
                else:
                    declined += 1
                po_id.write({'sent_to_vendor': False})
                self.env.cr.commit()
        opsyst_info_channel = self.env['ir.config_parameter'].get_param('slack_odoo_opsyst_info_channel_id')
        attachment = {
                'color': '#7CD197' if declined == 0 else '#DC3545',
                'fallback': 'PFG POs report',
                'title': 'Total orders sent: %s' % len(po_ids_to_send),
                'text': 'Confirmed by PFG: %s \nDeclined by PFG: %s' % (confirmed, declined)
            }
        self.env['slack.calls'].notify_slack('[ODOO] Send POs to PFG', 'PFG POs report', opsyst_info_channel, attachment)
        self.env['slack.calls'].notify_slack('[ODOO] Send POs to PFG', 'Ended at %s' % datetime.utcnow())

    @api.model
    def cron_lkq_send_purchase_orders(self):
        po_ids_to_send = self.search([('dropshipper_code', '=', 'lkq'), ('vendor_order_id', '=', False), ('state', '=', 'draft'), ('dest_address_id', '!=', False)])
        po_ids_to_send.queue_for_sending_to_vendor()
        for po_id in po_ids_to_send:
            if po_id.sale_id.has_duplicates():
                continue
            _logger.info('Sending %s to vendor' %po_id.name)
            res = po_id.lkq_process_order()
            if 'success' in res:
                po_id.write({'vendor_order_id': res['quote_id']})
                message = _("PO sent to vendor from scheduler. New Order ID from %s: %s."
                            % (po_id.partner_id.name, po_id.vendor_order_id))
                po_id.message_post(body=message)
                po_id.button_confirm()
            po_id.write({'sent_to_vendor': False})
            self.env.cr.commit()

    @api.model
    def _prepare_picking(self):
        values = super(PurchaseOrder, self)._prepare_picking()
        if self.store_id:
            values['store_id'] = self.store_id.id
        return values

    @api.multi
    def send_to_ppr(self):
        # Make sure not to send an email if there are no POs from the wizard
        if not self:
            return
        order_date = timezone('US/Eastern').localize(datetime.now()).strftime('%Y-%m-%d')
        # create the attachment
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)
        columns = ['Cross Ref No.', 'Buyer Full Name', 'Street Address 1', 'Street Address 2', 'City', 'State', 'ZIP/Postal Code', 'Contact Number', 'Part Number', 'Qty']
        writer.writerow([name.encode('utf-8') for name in columns])
        for po in self:
            for line in po.order_line:
                part_number = line.product_id.part_number
                if line.product_id.mfg_code != 'PPR':
                    ppr_alt = line.product_id.alternate_ids.filtered(lambda r: r.mfg_code == 'PPR')
                    if ppr_alt:
                        part_number = ppr_alt[0].part_number
                    else:
                        line.product_id.button_sync_with_autoplus(raise_exception=False)
                        ppr_alt = line.product_id.alternate_ids.filtered(lambda r: r.mfg_code == 'PPR')
                        if ppr_alt:
                            part_number = ppr_alt[0].part_number

                row = [
                    po.name.encode('ascii','ignore') or '',
                    po.dest_address_id.name.encode('ascii','ignore') if po.dest_address_id.name else '',
                    po.dest_address_id.street.encode('ascii','ignore') if po.dest_address_id.street else '',
                    po.dest_address_id.street2.encode('ascii','ignore') if po.dest_address_id.street2 else '',
                    po.dest_address_id.city.encode('ascii','ignore') if po.dest_address_id.city else '',
                    po.dest_address_id.state_id.code.encode('ascii','ignore') if po.dest_address_id.state_id.code else '',
                    po.dest_address_id.zip.encode('ascii','ignore') if po.dest_address_id.zip else '',
                    po.dest_address_id.phone.encode('ascii','ignore') if po.dest_address_id.phone else '',
                    part_number,
                    int(line.product_qty) or '1'
                ]
                writer.writerow(row)
        fp.seek(0)
        data = fp.read()
        fp.close()
        attachment_id = self.env['ir.attachment'].create({
            'name': 'PPRIC Orders ' + order_date,
            'datas_fname': 'PPRIC Orders ' + order_date + '.csv',
            'datas': base64.encodestring(data)
        })
        message_template = self.env.ref('sale_dropship.send_po_to_ppr')
        values = message_template.sudo().with_context(order_date=order_date).generate_email(1)
        mail = self.env['mail.mail'].sudo().create(values)
        mail.write({'attachment_ids': [(6, 0, [attachment_id.id])]})
        mail.send()

        for po in self:
            po.write({'vendor_order_id': 'Mail Sent ' + order_date})
            po.button_confirm()

    @api.multi
    def cron_ppr_send_purchase_orders(self):
        # Do not run cron on weekends
        weekday = datetime.now(timezone('US/Eastern')).weekday()
        if weekday >= 5:
            _logger.info('PPR orders will not be sent because it is a weekend.')
            return
        po_ids = self.search([('state', '=', 'draft'), ('partner_id.dropshipper_code', '=', 'ppr')])
        po_ids.send_to_ppr()
