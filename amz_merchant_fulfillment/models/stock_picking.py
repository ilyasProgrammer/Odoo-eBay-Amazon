# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta
import gzip
import pprint
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO as StringIO

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_fbm_prime = fields.Boolean('Prime - Fulfillment by Merchant')
    latest_ship_date = fields.Datetime('Latest Ship Date')
    shipping_service_id = fields.Char('Shipping Service ID')
    shipping_service_offer_id = fields.Char('Shipping Service Offer ID')

    @api.multi
    def amz_get_elligible_shipping_services(self):
        now = datetime.now()
        shipping_params = {}
        shipping_params['Action'] = 'GetEligibleShippingServices'
        shipping_params['ShipmentRequestDetails.AmazonOrderId'] = self.sale_id.web_order_id
        shipping_params['ShipmentRequestDetails.PackageDimensions.Length'] = str(int(self.length))
        shipping_params['ShipmentRequestDetails.PackageDimensions.Width'] = str(int(self.width))
        shipping_params['ShipmentRequestDetails.PackageDimensions.Height'] = str(int(self.height))
        shipping_params['ShipmentRequestDetails.PackageDimensions.Unit'] = 'inches'
        shipping_params['ShipmentRequestDetails.Weight.Value'] = str(int(self.weight * 16))
        shipping_params['ShipmentRequestDetails.Weight.Unit'] = 'oz'
        # shipping_params['ShipmentRequestDetails.ShipDate'] = (datetime.strptime(self.latest_ship_date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%dT%H:%M:%SZ')
        shipping_params['ShipmentRequestDetails.ShipFromAddress.Name'] = 'Fulfillment Warehouse'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.AddressLine1'] = '15004 3rd Ave'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.City'] = 'Highland Park'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.StateOrProvinceCode'] = 'MI'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.PostalCode'] = '48203-3718'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.CountryCode'] = 'US'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.Email'] = 'sinisterautoparts@gmail.com'
        shipping_params['ShipmentRequestDetails.ShipFromAddress.Phone'] = '+13136108402'
        shipping_params['ShipmentRequestDetails.ShippingServiceOptions.DeliveryExperience'] = 'DeliveryConfirmationWithoutSignature'
        shipping_params['ShipmentRequestDetails.ShippingServiceOptions.CarrierWillPickUp'] = 'false'
        # shipping_params['ShipmentRequestDetails.ShippingServiceOptions.LabelFormat'] = 'PNG'

        order_item_ids = set(self.sale_id.order_line.mapped('web_orderline_id'))
        counter = 1
        for order_item_id in order_item_ids:
            order_line = self.sale_id.order_line.filtered(lambda r: r.web_orderline_id == order_item_id)[0]
            # TODO: BOMS are not necessarily 1 of each component quantity
            shipping_params['ShipmentRequestDetails.ItemList.Item.%s.OrderItemId' % counter] = order_item_id
            shipping_params['ShipmentRequestDetails.ItemList.Item.%s.Quantity' % counter] = str(int(order_line.product_uom_qty))
            counter += 1
        response = self.store_id.process_amz_request('GET', '/MerchantFulfillment/2015-06-01', now, shipping_params)
        result = response['GetEligibleShippingServicesResponse']['GetEligibleShippingServicesResult']
        _logger.info('\n\nGet Eligible Service Result: %s\n\n' % pprint.pformat(result))
        cheapest = {'rate': 0.0, 'service_id': False, 'package_id': False}
        if 'ShippingService' in result['ShippingServiceList']:
            services = result['ShippingServiceList']['ShippingService']
            if not isinstance(services, list):
                services = [services]
            first_service = True
            for service in services:
                current_rate = float(service['Rate']['Amount']['value'])
                current_shipping_service_id = service['ShippingServiceId']['value']
                if first_service and (current_shipping_service_id.startswith('FEDEX')
                                      or (self.height <= 1 and current_shipping_service_id.startswith('USPS'))
                                      or (self.weight <= 4 and current_shipping_service_id == 'USPS_PTP_PRI')
                                      or (self.amz_order_type == 'fbm' and current_shipping_service_id.startswith('USPS'))):
                    rate = current_rate
                    shipping_service_id = current_shipping_service_id
                    service_name = service['ShippingServiceName']['value']
                    shipping_service_offer_id = service['ShippingServiceOfferId']['value']
                    first_service = False
                elif not first_service and current_rate < rate and (current_shipping_service_id.startswith('FEDEX')
                                                                    or (self.height <= 1 and current_shipping_service_id.startswith('USPS'))
                                                                    or (self.weight <= 4 and current_shipping_service_id == 'USPS_PTP_PRI')
                                                                    or (self.amz_order_type == 'fbm' and current_shipping_service_id.startswith('USPS'))):
                    rate = current_rate
                    shipping_service_id = current_shipping_service_id
                    service_name = service['ShippingServiceName']['value']
                    shipping_service_offer_id = service['ShippingServiceOfferId']['value']
            if not first_service:
                parsed_service_name = service_name.encode('ascii','ignore').lower().replace(' ','_')
                service_id = self.env['ship.carrier.service'].search([('ss_code', '=', parsed_service_name),
                                                                      ('oversized', '=', False)])
                cheapest = {
                    'rate': rate,
                    'service_id': service_id.id,
                    'package_id': service_id.package_id.id,
                    'shipping_service_id': shipping_service_id,
                    'shipping_service_offer_id': shipping_service_offer_id
                }
        return cheapest

    @api.multi
    def button_get_cheapest_service(self):
        for picking in self:
            service = picking.get_cheapest_service()
            service_id = self.env['ship.carrier.service'].browse(service['service_id'])
            picking.write({
                'rate': service.get('rate'),
                'service_id': service.get('service_id'),
                'carrier_id': service_id.carrier_id.id,
                'package_id': service.get('package_id'),
                'shipping_service_id': service.get('shipping_service_id', ''),
                'shipping_service_offer_id': service.get('shipping_service_offer_id', ''),
                'exceeds_limits': service['exceeds_limits'] if service.get('exceeds_limits') else False
            })

    @api.multi
    def get_cheapest_service(self):
        if self.length == 0 or self.width == 0 or self.height == 0 or self.weight == 0:
            return {'rate': 0.0, 'service_id': False, 'package_id': False}
        if self.amz_order_type == 'fbm':
            res = self.amz_get_elligible_shipping_services()
            if res['rate'] > 0:
                return res
        return super(StockPicking, self).get_cheapest_service()

    @api.multi
    def amz_fbm_get_label(self):
        if self.shipping_service_id and self.shipping_service_offer_id:
            now = datetime.now()
            shipping_params = {}
            shipping_params['Action'] = 'CreateShipment'
            shipping_params['ShippingServiceId'] = self.shipping_service_id
            #shipping_params['ShippingServiceOfferId'] = self.shipping_service_offer_id
            shipping_params['ShippingServiceOfferId'] = self.shipping_service_offer_id
            shipping_params['ShipmentRequestDetails.AmazonOrderId'] = self.sale_id.web_order_id
            shipping_params['ShipmentRequestDetails.PackageDimensions.Length'] = str(self.length)
            shipping_params['ShipmentRequestDetails.PackageDimensions.Width'] = str(self.width)
            shipping_params['ShipmentRequestDetails.PackageDimensions.Height'] = str(self.height)
            shipping_params['ShipmentRequestDetails.PackageDimensions.Unit'] = 'inches'
            shipping_params['ShipmentRequestDetails.Weight.Value'] = str(self.weight * 16)
            shipping_params['ShipmentRequestDetails.Weight.Unit'] = 'oz'
            shipping_params['ShipmentRequestDetails.ShipDate'] = datetime.strptime(self.latest_ship_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%SZ')
            shipping_params['ShipmentRequestDetails.ShipFromAddress.Name'] = 'Fulfillment Warehouse'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.AddressLine1'] = '15004 3rd Ave'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.City'] = 'Highland Park'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.StateOrProvinceCode'] = 'MI'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.PostalCode'] = '48203-3718'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.CountryCode'] = 'US'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.Email'] = 'sinisterautoparts@gmail.com'
            shipping_params['ShipmentRequestDetails.ShipFromAddress.Phone'] = '+13136108402'
            shipping_params['ShipmentRequestDetails.ShippingServiceOptions.DeliveryExperience'] = 'DeliveryConfirmationWithoutSignature'
            shipping_params['ShipmentRequestDetails.ShippingServiceOptions.LabelFormat'] = 'PNG'
            shipping_params['ShipmentRequestDetails.ShippingServiceOptions.CarrierWillPickUp'] = 'false'

            order_item_ids = set(self.sale_id.order_line.mapped('web_orderline_id'))
            counter = 1
            for order_item_id in order_item_ids:
                order_line = self.sale_id.order_line.filtered(lambda r: r.web_orderline_id == order_item_id)[0]
                # TODO: BOMS are not necessarily 1 of each component quantity
                shipping_params['ShipmentRequestDetails.ItemList.Item.%s.OrderItemId' %counter] = order_item_id
                shipping_params['ShipmentRequestDetails.ItemList.Item.%s.Quantity' %counter] = str(int(order_line.product_uom_qty))
                counter += 1
            response = self.store_id.process_amz_request('GET', '/MerchantFulfillment/2015-06-01', now, shipping_params)
            result = response['CreateShipmentResponse']['CreateShipmentResult']['Shipment']

            zipped_file_path = '/var/tmp/label_%s.gz' %self.id
            zipped_label_content = base64.b64decode(result['Label']['FileContents']['Contents']['value'])
            zipped_label = open(zipped_file_path, 'wb')
            zipped_label.write(zipped_label_content)
            zipped_label.close()
            # Get content
            f = gzip.open(zipped_file_path, 'rb')
            file_content = f.read()
            f.close()

            self.write({
                'tracking_number': result['TrackingId']['value'],
                'shipment_id': result['ShipmentId']['value'],
                'is_label_voided': False,
                'label': base64.b64encode(file_content)
            })

    @api.multi
    def button_lable_void(self):
        if self.tracking_number and self.label and self.shipment_id:
            if self.amz_order_type == 'fbm':
                now = datetime.now()
                shipping_params = {}
                shipping_params['Action'] = 'CancelShipment'
                shipping_params['ShipmentId'] = self.shipment_id
                response = self.store_id.process_amz_request('GET', '/MerchantFulfillment/2015-06-01', now, shipping_params)
                if response['CancelShipmentResponse']['CancelShipmentResult']['Shipment']['Status']['value'] != 'Purchased':
                    self.write({'is_label_voided': True})
            else:
                result = self.env['sale.order'].ss_execute_request('POST', '/shipments/voidlabel', {'shipmentId': self.shipment_id})
                if result.get('approved'):
                    self.write({'is_label_voided': True})

    @api.multi
    def _compute_file_name(self):
        for picking in self:
            if picking.amz_order_type == 'fbm':
                picking.file_name = (picking.tracking_number or 'blank') + '.png'
            else:
                picking.file_name = (picking.tracking_number or 'blank') + '.pdf'

    @api.multi
    def button_get_label(self):
        if self.amz_order_type == 'fbm':
            self.amz_fbm_get_label()
        else:
            super(StockPicking, self).button_get_label()
