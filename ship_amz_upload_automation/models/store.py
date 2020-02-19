# -*- coding: utf-8 -*-

import logging
import pprint
from datetime import datetime, timedelta
from odoo import models, fields, api
import uuid
import time

_logger = logging.getLogger(__name__)


class Store(models.Model):
    _inherit = 'sale.store'

    @api.model
    def cron_amz_submit_tracking_numbers(self):
        now = datetime.utcnow()
        store_ids = self.search([('site', '=', 'amz'), ('enabled', '=', True)])
        for store_id in store_ids:
            pick_ids = self.env['stock.picking'].search([('create_date', '>=', '2018-01-01 00:00:00'), ('sale_id', '!=', False),
                                                         ('shipping_state', 'in', ('in_transit', 'done')),
                                                         ('tracking_number', '!=', False),
                                                         ('store_id', '=', store_id.id),
                                                         ('amz_order_type', '=', 'normal'),  # FBA handled by Amazon. FBM (Prime) cant be handled thru API
                                                         ('store_notified', '=', False)
                                                         ])
            if pick_ids:
                FulfillmentDate = now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
                MerchantIdentifier = uuid.uuid4().hex
                counter = 1
                xml_body = ''
                for pick_id in pick_ids:
                    amazon_order_id = pick_id.sale_id.web_order_id
                    tracking = pick_id.tracking_number
                    getorder_params = {'Action': 'ListOrderItems', 'AmazonOrderId': amazon_order_id}
                    order_details = store_ids.process_amz_request('GET', '/Orders/2013-09-01', now, getorder_params)
                    try:
                        orders_data = order_details['ListOrderItemsResponse']['ListOrderItemsResult']['OrderItems']
                    except Exception as e:
                        pick_ids -= pick_id
                        _logger.warning("Issue with getting order from Amazon: %s %s", amazon_order_id, e)
                        continue
                    if type(orders_data) == list:
                        pick_ids -= pick_id
                        continue  # TODO !!!  combined order
                    amz_item_id = orders_data['OrderItem']['OrderItemId']['value']
                    ordered_qty = orders_data['OrderItem']['QuantityOrdered']['value']
                    xml_body += "<Message>"
                    xml_body += "<MessageID>{MessageID}</MessageID>".format(MessageID=str(counter))
                    xml_body += "<OperationType>PartialUpdate</OperationType>"
                    xml_body += "<OrderFulfillment>"
                    xml_body += "<AmazonOrderID>%s</AmazonOrderID>" % amazon_order_id
                    xml_body += "<FulfillmentDate>{FulfillmentDate}</FulfillmentDate>".format(FulfillmentDate=FulfillmentDate)
                    xml_body += "<FulfillmentData>"
                    xml_body += "<CarrierName>{CarrierName}</CarrierName>".format(CarrierName=pick_id.carrier_id.name)
                    if pick_id.service_id:
                        xml_body += "<ShippingMethod>{ShippingMethod}</ShippingMethod>".format(ShippingMethod=pick_id.service_id.name)
                    xml_body += "<ShipperTrackingNumber>{ShipperTrackingNumber}</ShipperTrackingNumber>".format(ShipperTrackingNumber=tracking)
                    xml_body += "</FulfillmentData>"
                    xml_body += "<Item>"
                    xml_body += "<AmazonOrderItemCode>"
                    xml_body += amz_item_id
                    xml_body += "</AmazonOrderItemCode>"
                    xml_body += "<Quantity>"
                    xml_body += ordered_qty
                    xml_body += "</Quantity>"
                    xml_body += "</Item>"
                    xml_body += "</OrderFulfillment>"
                    xml_body += "</Message>"
                    counter += 1
                    if counter == 4:
                        break
                xml = "<?xml version='1.0' encoding='utf-8'?>"
                xml += "<AmazonEnvelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='amzn-envelope.xsd'>"
                xml += "<Header>"
                xml += "<DocumentVersion>1.0</DocumentVersion>"
                xml += "<MerchantIdentifier>{MerchantIdentifier}</MerchantIdentifier>".format(MerchantIdentifier=MerchantIdentifier)
                xml += "</Header>"
                xml += "<MessageType>OrderFulfillment</MessageType>"
                xml += "<PurgeAndReplace>false</PurgeAndReplace>"
                xml += xml_body
                xml += "</AmazonEnvelope>"
                md5value = store_id.get_md5(xml)
                params = {
                    'ContentMD5Value': md5value,
                    'Action': 'SubmitFeed',
                    'FeedType': '_POST_ORDER_FULFILLMENT_DATA_',
                    'PurgeAndReplace': 'false'
                }
                _logger.info('Uploading shipping info: %s' % pprint.pformat(xml))
                response = store_id.process_amz_request('POST', '/Feeds/2009-01-01', now, params, xml)
                _logger.info('Response: %s' % pprint.pformat(response))
                feed_id = response['SubmitFeedResponse']['SubmitFeedResult']['FeedSubmissionInfo']['FeedSubmissionId']['value']
                params = {'Action': 'GetFeedSubmissionResult', 'FeedSubmissionId': feed_id}
                time.sleep(15)
                max_attempts = 15
                while max_attempts > 1:
                    now = datetime.utcnow()
                    try:
                        response = store_id.process_amz_request('POST', '/Feeds/2009-01-01', now, params)
                        status = response['AmazonEnvelope']['Message']['ProcessingReport']['StatusCode']['value']
                        if status == 'Complete':
                            for el in response['AmazonEnvelope']['Message']['ProcessingReport']['Result']:  # exclude orders with errors
                                if el['ResultCode']['value'] == 'Error':
                                    pick_id = filter(lambda x: x.sale_id.web_order_id == el['AdditionalInfo']['AmazonOrderID']['value'], pick_ids)
                                    pick_ids -= pick_id[0]
                                    _logger.warning('Picking excluded %s', pick_id[0])
                            break
                        time.sleep(60)
                    except Exception as e:
                        _logger.warning('Something wrong: %s', e)
                        time.sleep(60)
                    max_attempts -= 1
                if max_attempts < 1:
                    _logger.error('Serious problem with pushing tracking numbers to Amazon')
                else:
                    pick_ids.write({'store_notified': True})
                    _logger.info('Amazon tracking numbers pushed successfully')
