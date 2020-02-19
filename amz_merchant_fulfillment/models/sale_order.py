# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api
import logging
import pprint
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_fbm_prime = fields.Boolean('Prime - Fulfillment by Merchant')
    latest_ship_date = fields.Datetime('Latest Ship Date')
    shipping_service_id = fields.Char('Shipping Service ID')
    shipping_service_offer_id = fields.Char('Shipping Service Offer ID')
    is_premium_order = fields.Boolean('Premium Shipping', help='Premium shipping')  # premium order means only specific shipping option. It's not Prime order. For prime orders they have IsPrime field.

    @api.multi
    def amz_get_elligible_shipping_services(self):
        now = datetime.now()
        shipping_params = {}
        shipping_params['Action'] = 'GetEligibleShippingServices'
        shipping_params['ShipmentRequestDetails.AmazonOrderId'] = self.web_order_id
        shipping_params['ShipmentRequestDetails.PackageDimensions.Length'] = str(self.length)
        shipping_params['ShipmentRequestDetails.PackageDimensions.Width'] = str(self.width)
        shipping_params['ShipmentRequestDetails.PackageDimensions.Height'] = str(self.height)
        shipping_params['ShipmentRequestDetails.PackageDimensions.Unit'] = 'inches'
        shipping_params['ShipmentRequestDetails.Weight.Value'] = str(self.weight * 16)
        shipping_params['ShipmentRequestDetails.Weight.Unit'] = 'oz'
        shipping_params['ShipmentRequestDetails.ShipDate'] = (datetime.strptime(self.latest_ship_date, '%Y-%m-%d %H:%M:%S')).strftime('%Y-%m-%dT%H:%M:%SZ')
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

        order_item_ids = set(self.order_line.mapped('web_orderline_id'))
        counter = 1
        for order_item_id in order_item_ids:
            order_line = self.order_line.filtered(lambda r: r.web_orderline_id == order_item_id)[0]
            # TODO: BOMS are not necessarily 1 of each component quantity
            shipping_params['ShipmentRequestDetails.ItemList.Item.%s.OrderItemId' % counter] = order_item_id
            shipping_params['ShipmentRequestDetails.ItemList.Item.%s.Quantity' % counter] = str(int(order_line.product_uom_qty))
            counter += 1
        response = self.store_id.process_amz_request('GET', '/MerchantFulfillment/2015-06-01', now, shipping_params)

        result = response['GetEligibleShippingServicesResponse']['GetEligibleShippingServicesResult']
        _logger.info('Get Eligible Response: %s' % result)
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
            _logger.info('\n\nAMAZON CERVICES: %s\n\n', pprint.pformat(services))
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
        for so in self:
            service = so.get_cheapest_service()
            so.write({
                'rate': service.get('rate'),
                'service_id': service.get('service_id'),
                'package_id': service.get('package_id'),
                'shipping_service_id': service.get('shipping_service_id', ''),
                'shipping_service_offer_id': service.get('shipping_service_offer_id', ''),
                'exceeds_limits': service['exceeds_limits'] if service.get('exceeds_limits') else False,
                'residential': service['residential'] if service.get('residential') else False,
            })
            if len(self):
                return service['services_prices_log'] if service.get('services_prices_log') else ''

    @api.multi
    def get_cheapest_service(self):
        if self.length == 0 or self.width == 0 or self.height == 0 or self.weight == 0:
            return {'rate': 0.0, 'service_id': False, 'package_id': False}
        if self.amz_order_type == 'fbm':
            res = self.amz_get_elligible_shipping_services()
            return res
        return super(SaleOrder, self).get_cheapest_service()
