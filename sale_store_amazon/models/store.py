# -*- coding: utf-8 -*-

import urllib
import hashlib
import hmac
import base64
import pprint
import re
import utils
from requests import request
from requests.exceptions import HTTPError
from xml.etree.ElementTree import ParseError as XMLError
from datetime import datetime, timedelta
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class DictWrapper(object):
    def __init__(self, xml, rootkey=None):
        self.original = xml
        self._rootkey = rootkey
        self._mydict = utils.xml2dict().fromstring(remove_namespace(xml))
        self._response_dict = self._mydict.get(self._mydict.keys()[0],
                                               self._mydict)

    @property
    def parsed(self):
        if self._rootkey:
            return self._response_dict.get(self._rootkey)
        else:
            return self._response_dict


class DataWrapper(object):
    """
        Text wrapper in charge of validating the hash sent by Amazon.
    """
    def __init__(self, data, header):

        def get_md5(content):
            base64md5 = base64.b64encode(hashlib.md5(content).digest())
            if base64md5[-1] == '\n':
                base64md5 = self.base64md5[0:-1]
            return base64md5

        self.original = data
        if 'content-md5' in header:
            hash_ = get_md5(self.original)
            if header['content-md5'] != hash_:
                raise MWSError("Wrong Contentlength, maybe amazon error...")

    @property
    def parsed(self):
        return self.original


class MWSError(Exception):
    """
        Main MWS Exception class
    """
    # Allows quick access to the response object.
    # Do not rely on this attribute, always check if its not None.
    response = None


class OnlineStore(models.Model):
    _inherit = 'sale.store'

    amz_domain = fields.Char(string="Domain", required_if_site='amz')
    amz_access_id = fields.Char("Access ID", required_if_site='amz')
    amz_marketplace_id = fields.Char("Marketplace ID", required_if_site='amz')
    amz_seller_id = fields.Char("Seller ID", required_if_site='amz')
    amz_secret_key = fields.Char("Secret Key", required_if_site='amz')
    amz_signature_version = fields.Char("Signature Version", required_if_site='amz')
    amz_signature_method = fields.Char("Signature Method", required_if_site='amz')

    @api.model
    def get_md5(self, string):
        base64md5 = base64.b64encode(hashlib.md5(string).digest())
        if base64md5[-1] == '\n':
            base64md5 = self.base64md5[0:-1]
        return base64md5

    @api.multi
    def process_amz_request(self, verb, uri, now, extra_params=None, feed=None):
        self.ensure_one()
        params = {
            'AWSAccessKeyId': self.amz_access_id,
            'MarketplaceId.Id.1': self.amz_marketplace_id,
            'SellerId': self.amz_seller_id,
            'SignatureVersion': self.amz_signature_version,
            'SignatureMethod': self.amz_signature_method,
            'Timestamp': now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
        }
        if 'MarketplaceId' in extra_params:
            params.pop('MarketplaceId.Id.1', None)
        params.update(extra_params)
        _logger.debug('# PARAMS: %s', pprint.pformat(params))
        request_description = '&'.join(['%s=%s' % (k, urllib.quote(params[k], safe='-_.~').encode('utf-8')) for k in sorted(params)])
        logging.info('Amazon request: %s' % request_description)
        domain = self.amz_domain
        secret_key = self.amz_secret_key

        signature = self.calc_signature(verb, uri, domain, secret_key, request_description)

        url = '%s%s?%s&Signature=%s' % (domain, uri, request_description, urllib.quote(signature))
        headers = {
            'User-Agent': 'python-amazon-mws/0.0.1 (Language=Python)'
        }

        if params['Action'] == 'SubmitFeed':
            headers['Host'] = 'mws.amazonservices.com'
            headers['Content-Type'] = 'text/xml'
        elif params['Action'] == 'GetReport':
            headers['Host'] = 'mws.amazonservices.com'
            headers['Content-Type'] = 'x-www-form-urlencoded'
        try:
            logging.info('Amazon headers: %s' % headers)
            logging.info('Amazon url =: %s' % url)
            logging.info('Amazon feed =: %s' % feed)
            response = request(verb, url, data=feed, headers=headers)
            logging.info('Amazon response: %s' % response)
            response.raise_for_status()
            data = response.content
            try:
                parsed_response = DictWrapper(data, extra_params['Action'] + "Result")
                logging.info('Amazon parsed_response: %s' % parsed_response)
            except XMLError:
                parsed_response = DataWrapper(data, response.headers)
                logging.info('Amazon parsed_response: %s' % parsed_response)
                return data
        except HTTPError, e:
            error = MWSError(str(e.response.text))
            error.response = e.response
            raise error
        parsed_response.response = response
        return parsed_response._mydict

    @api.model
    def calc_signature(self, verb, uri, domain, secret_key, request_description):
        paramsObj = self.env['ir.config_parameter'].sudo()
        sig_data = verb + '\n' + domain.replace('https://', '').lower() + '\n' + uri + '\n' + request_description
        return base64.b64encode(hmac.new(str(secret_key), sig_data, hashlib.sha256).digest())

    @api.multi
    def amz_getorder(self, now, minutes_ago):
        self.ensure_one()
        orders_saved = 0
        listorders_params = {}
        listorders_params['Action'] = 'ListOrders'
        listorders_params['FulfillmentChannel.Channel.1'] = 'MFN'
        listorders_params['PaymentMethod.Method.1'] = 'Other'
        listorders_params['PaymentMethod.Method.2'] = 'COD'
        listorders_params['PaymentMethod.Method.3'] = 'CVS'
        listorders_params['OrderStatus.Status.1'] = 'Unshipped'
        listorders_params['OrderStatus.Status.2'] = 'PartiallyShipped'
        listorders_params['OrderStatus.Status.3'] = 'PendingAvailability'
        listorders_params['MaxResultsPerPage'] = '40'
        listorders_params['LastUpdatedAfter'] = (now - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
        response = self.process_amz_request('GET', '/Orders/2013-09-01', now, listorders_params)

        result = response['ListOrdersResponse']['ListOrdersResult']
        if 'Order' in result['Orders']:
            orders = result['Orders']['Order']
            # if there is only one item, what's returned is just a dictionary
            if not isinstance(orders, list):
                orders = [orders]
            saved_qty = self.save_orders(now, orders)  # -> amz_merchant_fulfillment
            orders_saved = saved_qty or 0
        if 'NextToken' in result:
            res = self.amz_getorder_by_next_token(now, result['NextToken']['value'])
            orders_saved += res or 0
        return orders_saved

    @api.multi
    def amz_get_order_by_order_id(self, order_id, now):
        self.ensure_one()
        get_order_params = {}
        get_order_params['Action'] = 'GetOrder'
        get_order_params['AmazonOrderId.Id.1'] = order_id

        print get_order_params

        response = self.process_amz_request('GET', '/Orders/2013-09-01', now, get_order_params)

        result = response['GetOrderResponse']['GetOrderResult']

        if 'Order' in result['Orders']:
            orders = [result['Orders']['Order']]
            self.save_orders(now, orders)
            return True
        else:
            return False

    @api.multi
    def amz_getorder_by_next_token(self, now, token, saved=0):
        self.ensure_one()
        orders_saved = saved if saved else 0
        params = {}
        params['Action'] = 'ListOrdersByNextToken'
        params['NextToken'] = token
        response = self.process_amz_request('GET', '/Orders/2013-09-01', now, params)
        result = response['ListOrdersByNextTokenResponse']['ListOrdersByNextTokenResult']
        if 'Order' in result['Orders']:
            orders = result['Orders']['Order']
            # if there is only one item, what's returned is just a dictionary
            if not isinstance(orders, list):
                orders = [orders]
            res = self.save_orders(now, orders)
            orders_saved += res or 0

        if 'NextToken' in result:
            return self.amz_getorder_by_next_token(now, result['NextToken']['value'], orders_saved)
        return orders_saved

    @api.multi
    def save_orders(self, now, orders):
        # WARNING ! THIS IS overridden BY amz_merchant_fulfillment without super call
        self.ensure_one()
        created_orders = 0

        PartnerObj = self.env['res.partner']
        SaleOrderObj = self.env['sale.order']
        SaleOrderLineObj = self.env['sale.order.line']
        ProductTemplateObj = self.env['product.template']
        ProductProductObj = self.env['product.product']
        ProductListingObj = self.env['product.listing']

        for order in orders:
            _logger.info('Processing %s' % order['AmazonOrderId']['value'])
            if self.code == 'sinister' and order['PurchaseDate']['value'] < "2017-03-17T07:24:08Z":
                continue
            amz_order_id = order['AmazonOrderId']['value']
            sale_order_id = SaleOrderObj.search([('web_order_id', '=', amz_order_id)])
            if sale_order_id:
                continue
            #CREATE PARTNER
            state = order['ShippingAddress']['StateOrRegion']['value']
            state_id = False
            country_id = self.env['res.country'].search([('code', '=', 'US')], limit=1)
            if len(state) == 2:
                state_id = self.env['res.country.state'].search([('code', '=', state.upper()), ('country_id', '=', country_id.id)], limit=1)
            else:
                state_id = self.env['res.country.state'].search([('name', '=', state.title()), ('country_id', '=', country_id.id)], limit=1)
            partner_values = {
                'name': order['ShippingAddress']['Name']['value'],
                'phone': order['ShippingAddress']['Phone']['value'] if 'Phone' in order['ShippingAddress'] else '',
                'street': order['ShippingAddress']['AddressLine1']['value'] if 'AddressLine1' in order['ShippingAddress'] else '',
                'street2': order['ShippingAddress']['AddressLine2']['value'] if 'AddressLine2' in order['ShippingAddress'] else '',
                'city': order['ShippingAddress']['City']['value'],
                'zip': order['ShippingAddress']['PostalCode']['value'].strip(' '),
                'country_id': country_id.id,
                'state_id': state_id.id,
                'customer': True,
                'store_id': self.id,
                'email': order['BuyerEmail']['value']
            }
            if not state_id:
                partner_values['amz_state'] = state
            partner_id = PartnerObj.search([('name', '=', partner_values['name'])])
            if not (len(partner_id) == 1 and partner_id.name == partner_values['name'] and partner_id.phone == partner_values['phone'] and partner_id.street == partner_values['street'] and partner_id.city == partner_values['city'] and partner_id.zip == partner_values['zip']):
                partner_id = PartnerObj.create(partner_values)

            sale_order_id = SaleOrderObj.create({
                'partner_id': partner_id.id,
                'web_order_id': amz_order_id,
                'store_id': self.id,
                'payment_term_id': self.env.ref('account.account_payment_term_immediate').id
            })
            created_orders += 1
            getorder_params = {'Action': 'ListOrderItems', 'AmazonOrderId': amz_order_id}
            order_details = self.process_amz_request('GET', '/Orders/2013-09-01', now, getorder_params)

            if 'OrderItem' in order_details['ListOrderItemsResponse']['ListOrderItemsResult']['OrderItems']:
                order_items = order_details['ListOrderItemsResponse']['ListOrderItemsResult']['OrderItems']['OrderItem']
                if not isinstance(order_items, list):
                    order_items = [order_items]
                for order_item in order_items:
                    if int(order_item['QuantityOrdered']['value']) == 0:
                        continue
                    product_tmpl_id = ProductTemplateObj
                    sku = ''
                    if 'SellerSKU' in order_item and order_item['SellerSKU']['value']:
                        sku = order_item['SellerSKU']['value']
                        product_listing = ProductListingObj.search([('name', '=', sku)])
                        if product_listing:
                            product_tmpl_id = product_listing.product_tmpl_id
                            if product_tmpl_id.mfg_code != 'ASE':
                                ase_alt = product_tmpl_id.alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')
                                if ase_alt:
                                    product_tmpl_id = ase_alt

                    # If product is not found in odoo, look for it in autoplus and save it to odoo
                    if not product_tmpl_id and sku:
                        product_row = ProductTemplateObj.get_product_from_autoplus_by_part_number(sku)
                        if product_row:
                            product_values = ProductTemplateObj.prepare_product_row_from_autoplus(product_row)
                            product_tmpl_id = ProductTemplateObj.create(product_values)

                    # If product is not found in odoo and autoplus, create the product
                    if not product_tmpl_id:
                        product_values = {
                            'name': '[NOT FOUND] ' + order_item['Title']['value'],
                            'part_number': sku,
                            'type': 'product',
                            'list_price': float(order_item['ItemPrice']['Amount']['value']) / float(order_item['ItemPrice']['Amount']['value'])
                        }
                        product_tmpl_id = ProductTemplateObj.create(product_values)
                    SaleOrderLineObj.create({
                        'product_id': product_tmpl_id.product_variant_id.id,
                        'order_id': sale_order_id.id,
                        'price_unit': float(order_item['ItemPrice']['Amount']['value']) / int(order_item['QuantityOrdered']['value']),
                        'product_uom_qty': int(order_item['QuantityOrdered']['value']),
                    })

            # Set shipping dimensions if sale order has single line
            if len(sale_order_id.order_line) == 1:
                product_id = sale_order_id.order_line.product_id
                sale_order_id.write({
                    'length': product_id.length,
                    'width': product_id.width,
                    'height': product_id.height,
                    'weight': product_id.weight
                })
            self.env.cr.commit()
        return created_orders

    @api.multi
    def amz_submit_tracking_number(self, now):
        self.ensure_one()
        # Do not create a new feed if there is an existing pending feed
        feed_ids = self.env['sale.store.feed'].search([('state', 'in', ['draft', 'submitted', 'in_progress']),
                                                       ('store_id.id', '=', self.id), ('job_type', '=', '_POST_ORDER_FULFILLMENT_DATA_')])
        if feed_ids:
            return

        picking_ids = self.env['stock.picking'].search([('store_notified', '=', False), ('sale_id.store_id.id', '=', self.id),
                                                        ('tracking_number', '!=', False), ('shipping_state', '!=', 'error')])
        vendor_shipment_ids = self.env['sale.shipment.from.vendor'].search([('store_notified', '=', False), ('sale_id.store_id.id', '=', self.id),
                                                                            ('tracking_number', '!=', False), ('shipping_state', '!=', 'error')])

        if not (vendor_shipment_ids or vendor_shipment_ids):
            return

        xml_body = ""
        string_ids = ""
        counter = 1
        for picking in picking_ids:
            so = picking.sale_id
            string_ids += str(picking.tracking_number) + ','
            xml_body += "<MessageID>{MessageID}</MessageID>".format(MessageID=str(counter))
            xml_body += "<OperationType>PartialUpdate</OperationType>"
            xml_body += "<OrderFulfillment>"
            xml_body += "<AmazonOrderID>{AmazonOrderID}</AmazonOrderID>".format(AmazonOrderID=so.web_order_id)
            xml_body += "<FulfillmentDate>{FulfillmentDate}</FulfillmentDate>".format(FulfillmentDate=now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z'))
            xml_body += "<FulfillmentData>"
            xml_body += "<CarrierName>{CarrierName}</CarrierName>".format(CarrierName=picking.carrier_id.name)
            xml_body += "<ShippingMethod>{ShippingMethod}</ShippingMethod>".format(ShippingMethod=picking.service_id.name)
            xml_body += "<ShipperTrackingNumber>{ShipperTrackingNumber}</ShipperTrackingNumber>".format(ShipperTrackingNumber=picking.tracking_number)
            xml_body += "</FulfillmentData>"
            xml_body += "</OrderFulfillment>"
            counter += 1

        for shipment in vendor_shipment_ids:
            so = shipment.sale_id
            string_ids += str(shipment.tracking_number) + ','
            xml_body += "<MessageID>{MessageID}</MessageID>".format(MessageID=str(counter))
            xml_body += "<OperationType>PartialUpdate</OperationType>"
            xml_body += "<OrderFulfillment>"
            xml_body += "<AmazonOrderID>{AmazonOrderID}</AmazonOrderID>".format(AmazonOrderID=so.web_order_id)
            xml_body += "<FulfillmentDate>{FulfillmentDate}</FulfillmentDate>".format(FulfillmentDate=now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z'))
            xml_body += "<FulfillmentData>"
            xml_body += "<CarrierName>{CarrierName}</CarrierName>".format(CarrierName=shipment.carrier_id.name)
            xml_body += "<ShippingMethod>{ShippingMethod}</ShippingMethod>".format(ShippingMethod=shipment.service_id.name)
            xml_body += "<ShipperTrackingNumber>{ShipperTrackingNumber}</ShipperTrackingNumber>".format(ShipperTrackingNumber=shipment.tracking_number)
            xml_body += "</FulfillmentData>"
            xml_body += "</OrderFulfillment>"
            counter += 1

        MerchantIdentifier = '%s-'% str(self.id) + now.strftime('Amz-%Y-%m-%d-%H-%M-%S')
        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<AmazonEnvelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='amzn-envelope.xsd'>"
        xml += "<Header>"
        xml += "<DocumentVersion>1.0</DocumentVersion>"
        xml += "<MerchantIdentifier>{MerchantIdentifier}</MerchantIdentifier>".format(MerchantIdentifier=MerchantIdentifier)
        xml += "</Header>"
        xml += "<MessageType>OrderFulfillment</MessageType>"
        xml += "<PurgeAndReplace>false</PurgeAndReplace>"
        xml += "<Message>"
        xml += xml_body
        xml += "</Message>"
        xml += "</AmazonEnvelope>"

        md5value = self.get_md5(xml)

        params = {
            'ContentMD5Value': md5value,
            'Action': 'SubmitFeed',
            'FeedType': '_POST_ORDER_FULFILLMENT_DATA_',
            'PurgeAndReplace': 'false'
        }

        response = self.process_amz_request('POST', '/Feeds/2009-01-01', now, params, xml)

        if 'FeedSubmissionInfo' in response['SubmitFeedResponse']['SubmitFeedResult']:
            feed_info = response['SubmitFeedResponse']['SubmitFeedResult']['FeedSubmissionInfo']
            feed_id = self.env['sale.store.feed'].create({
                'name':  MerchantIdentifier,
                'submission_id': feed_info['FeedSubmissionId'],
                'date_submitted': now.strftime('%Y-%m-%d %H:%M:%S'),
                'job_type': '_POST_ORDER_FULFILLMENT_DATA_',
                'store_id': self.id,
                'content': xml,
                'state': 'submitted',
                'related_ids': string_ids[:-1]
            })

    @api.multi
    def get_submission_result(self, now):
        self.ensure_one()
        feed_ids = self.env['sale.store.feed'].search([('store_id.id','=', self.id),('state', '=','submitted')])
        for feed_id in feed_ids:
            params = {
                'Action': 'GetFeedSubmissionResult',
                'FeedSubmissionId': feed_id.submission_id
            }
            response = self.process_amz_request('POST', '/Feeds/2009-01-01', now, params)
            result = response['AmazonEnvelope']['Message']['ProcessingReport']
            if result['StatusCode']['value'] == 'Complete':
                feed_id.write({'state': 'done'})
                string_ids = feed_id.related_ids.split(",")
                tracking_numbers = []
                for string_id in string_ids:
                    tracking_numbers.append(int(string_id))
                for picking in self.env['stock.picking'].search([('tracking_number', 'in', tracking_numbers)]):
                     picking.write({'store_notified': True})
                for shipment in self.env['sale.shipment.from.vendor'].search([('tracking_number', 'in', tracking_numbers)]):
                    shipment.write({'store_notified': True})
            elif result['StatusCode']['value'] == 'Error':
                feed_id.write({'state': 'error'})

    @api.model
    def cron_amz_get_submission_result(self):
        now = datetime.now()
        for cred in self.sudo().search([('enabled', '=', True)]):
            cred.get_submission_result(now)

    @api.model
    def amz_list_new_product(self, now, product_tmpl):
        self.ensure_one()


def remove_namespace(xml):
    regex = re.compile(' xmlns(:ns2)?="[^"]+"|(ns2:)|(xml:)')
    return regex.sub('', xml)
