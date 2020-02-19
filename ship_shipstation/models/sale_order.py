# -*- coding: utf-8 -*-

import base64
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from requests import request
from requests.exceptions import HTTPError
import logging

_logger = logging.getLogger(__name__)


class SSError(Exception):
    response = None


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipstation_id = fields.Char(string="Shipstation ID")

    @api.model
    def convert_to_pst(self, dt):
        return (datetime.strptime(dt, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%Y-%m-%dT%H:%M:%S')

    @api.model
    def ss_execute_request(self, verb, endpoint, data=None):
        """
            verb - 'POST', 'GET'
            endpoint - should start with /
            data - dictionary
        """
        params = self.env['ir.config_parameter'].sudo()
        token = base64.b64encode(params.get_param('ss_api_key') +':' + params.get_param('ss_api_secret'))
        headers = {
            'Authorization': 'Basic ' + token,
        }
        url = 'https://ssapi.shipstation.com' + endpoint
        _logger.info('\n\nSS url: %s', url)
        _logger.info('\n\nSS data: %s', data)
        _logger.info('\n\nSS headers: %s', headers)
        try:
            if verb == 'POST':
                headers['Content-Type'] = 'application/json'
                response = request(verb, url, data=json.dumps(data), headers=headers)
            else:
                response = request(verb, url, headers=headers)
            response.raise_for_status()
        except HTTPError, e:
            if response._content:
                content = json.loads(response._content)
                if content and content.get('ExceptionMessage'):
                    _logger.warning('SS Error: %s %s\nURL: %s\n DATA: %s\n HEADERS: %s', content['ExceptionMessage'], e, url, data, headers)
                    raise UserError('Error SS Error: %s %s' % (content['ExceptionMessage'], e))
            _logger.error('Error: %s %s', self[0].name, e)
            raise UserError('Error on %s %s \nURL: %s\n DATA: %s\n HEADERS: %s' % (self[0].name, e, url, data, headers))
            # error = json.loads(e.response.text)
            # if 'ModelState' in error and ('request.advancedOptions.warehouseId' in error['ModelState'] or 'apiOrder.advancedOptions.warehouseId' in error['ModelState']):
            #     raise UserError(_('Store is not specified or store is not configured with a Shipstation warehouse ID.'))
            # elif 'ExceptionMessage' in error:
            #     raise UserError(_('%s' %error['ExceptionMessage']))
            # else:
            #     raise UserError(_('%s' %(e.response.text,)))
        return json.loads(response.content)

    @api.multi
    def ss_send_order(self, name):
        self.ensure_one()
        items = []
        returns = self.return_ids.filtered(lambda r: r.state != 'cancel' and r.state != 'done')
        #is_replacement = returns and returns.replacement_picking_ids.filtered(lambda p: p.state == 'assigned' and r.out_type)
        # The existing repalcements pickings don't have out_type so I check that the pick and delivery order are assigned
        is_replacement = returns and len(returns.replacement_picking_ids.filtered(lambda p: p.state == 'assigned')) == 2
        if is_replacement:
            for r in returns:
                for line in r.return_line_ids:
                    item = {
                        'name': line.product_id.name,
                        'quantity': int(line.product_uom_qty),
                        'unitPrice': line.sale_line_id.price_unit,
                    }
                    items.append(item)
        else:
            for line in self.order_line:
                item = {
                    'name': line.product_id.name,
                    'quantity': int(line.product_uom_qty),
                    'unitPrice': line.price_unit,
                }
            items.append(item)
        fedex_carrier = self.env['ship.carrier'].browse(1)
        data = {
            'orderNumber': name,
            'orderKey': self.id if not is_replacement else returns[0].name,
            'orderDate': self.convert_to_pst(self.date_order) if not is_replacement 
                else self.convert_to_pst(returns[0].create_date),
            'orderStatus': 'awaiting_shipment',
            'paymentDate': self.convert_to_pst(self.date_order),
            'shipByDate': self.convert_to_pst(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'billTo': {
                'name': self.partner_id.name,
                'street1': self.partner_id.street,
                'street2': self.partner_id.street2 or '',
                'city': self.partner_id.city,
                'state': self.partner_id.state_id.code,
                'postalCode': self.partner_id.zip,
                'country': self.partner_id.country_id.code
            },
            'shipTo': {
                'name': self.partner_id.name,
                'street1': self.partner_id.street,
                'street2': self.partner_id.street2 or '',
                'city': self.partner_id.city,
                'state': self.partner_id.state_id.code,
                'phone': self.partner_id.phone or '3136108402',
                'postalCode': self.partner_id.zip,
                'country': self.partner_id.country_id.code,
            },
            'items': items,
            'advancedOptions': {
                'warehouseId': self.store_id.ss_warehouse_id
            }
        }
        residential = fedex_carrier.fedex_validate_address(self, {'toCity': self.partner_id.city,
                                                                  'toState': self.partner_id.state_id.code,
                                                                  'toPostalCode': self.partner_id.zip,
                                                                  'toCountry': self.partner_id.country_id.code})
        data['shipTo']['residential'] = residential

        logging.debug('\n\nShip Station request data: %s', data)
        result = self.ss_execute_request('POST', '/orders/createorder', data)
        return result

    @api.multi
    def get_cheapest_service(self):
        self.ensure_one()
        if self.length == 0 or self.width == 0 or self.height == 0 or self.weight == 0:
            return {'rate': 0.0, 'service_id': False, 'package_id': False}
        log = ''
        replace_log = ''
        ServiceObj = self.env['ship.carrier.service']
        girth = self.length + (2 * self.width) + 2 * (self.height)
        allowed_service_ids = ServiceObj.search([('enabled', '=', True),
                                                 ('max_weight', '>=', self.weight),
                                                 ('max_length', '>=', self.length),
                                                 ('max_length_plus_girth', '>=', girth),
                                                 ('oversized', '=', True if girth > 136 else False)])
        if not allowed_service_ids:
            return {'rate': 0.0, 'service_id': False, 'package_id': False, 'exceeds_limits': True}
        if girth > 136:
            # carrier_ids = allowed_service_ids.mapped('carrier_id').filtered(lambda x: x.enabled and x.max_girth > 130)
            carrier_ids = [self.env.ref('ship_fedex.carrier_fedex_oversized')]
            # carrier_ids.append(self.env.ref('sale_store.carrier_fedex'))
        else:
            carrier_ids = allowed_service_ids.mapped('carrier_id').filtered(lambda x: x.enabled)
        first_result = True
        cheapest_rate = 0.0
        cheapest_service_id = ServiceObj
        fedex_carrier = self.env.ref('sale_store.carrier_fedex')
        for c in carrier_ids:
            replace_log = ''
            data = {
                'carrierCode': c.ss_code,
                'packageCode': 'package',
                'fromPostalCode': self.warehouse_id.partner_id.zip or '48035',
                'toPostalCode': self.partner_id.zip,
                'toState': self.partner_id.state_id.code,
                'toCountry': self.partner_id.country_id.code,
                'toCity': self.partner_id.city,
                'weight': {
                    'value': self.weight,
                    'units': 'pounds'
                },
                'dimensions': {
                    'units': 'inches',
                    'length': self.length,
                    'width': self.width,
                    'height': self.height
                },
                'confirmation': 'delivery'
            }
            self.residential = fedex_carrier.fedex_validate_address(self, data)
            data['residential'] = self.residential
            _logger.info('%s' % data)
            result = []
            if girth < 136:
                result = self.env['sale.order'].ss_execute_request('POST', '/shipments/getrates', data)
                for r_ss in result:
                    r_ss['src'] = 'SS'
                    log += 'Src: SS  Service: %s  Rate: %s' % (r_ss['serviceCode'], r_ss['shipmentCost'] + r_ss['otherCost']) + '\n'
            else:
                if c.ss_code == 'fedex':
                    try:
                        rr = c.fedex_get_rates(picking=self, data=data)  # rate request
                        # try:
                        #     self.residential = rr.RequestedShipment.Shipper.Address.Residential
                        # except Exception as e:
                        #     logging.error(e)
                        fedex_result = []
                        logging.info("HighestSeverity: %s", rr.response.HighestSeverity)
                        # RateReplyDetails can contain rates for multiple ServiceTypes if ServiceType was set to None
                        for service in rr.response.RateReplyDetails:
                            for detail in service.RatedShipmentDetails:
                                for surcharge in detail.ShipmentRateDetail.Surcharges:
                                    if surcharge.SurchargeType == 'OUT_OF_DELIVERY_AREA':
                                        logging.info("%s: ODA rr charge %s", service.ServiceType, surcharge.Amount.Amount)
                            for rate_detail in service.RatedShipmentDetails:
                                logging.info("%s: %s Net FedEx Charge %s %s", service.ServiceType, rate_detail.ShipmentRateDetail.RateType, rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Currency, rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount)
                                fedex_result.append({'src': 'Direct FedEx',
                                                     'otherCost': 0,
                                                     'RateType': rate_detail.ShipmentRateDetail.RateType,
                                                     'serviceName': service.ServiceType,
                                                     'serviceCode': 'fedex_' + service.ServiceType.lower() if 'fedex' not in service.ServiceType.lower() else service.ServiceType.lower(),
                                                     'fedex_code': service.ServiceType,
                                                     'shipmentCost': rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount})
                        # Check for warnings, this is also logged by the base class.
                        if rr.response.HighestSeverity == 'NOTE':
                            for notification in rr.response.Notifications:
                                if notification.Severity == 'NOTE':
                                    logging.info(notification)
                        log += '\nResidential: %s\n' % rr.RequestedShipment.Shipper.Address.Residential
                        for fr in fedex_result:
                            log += 'Src: FX  Service: %s  Rate: %s  Rate Type: %s' % (fr['serviceCode'], fr['shipmentCost'], fr['RateType']) + '\n'
                        # for ssr in result:
                        #     if fr['serviceCode'].replace('_', '') == ssr['serviceCode'].replace('_', '') and (ssr.get('RateType') is None or ssr.get('RateType') and ssr['RateType'] != 'PAYOR_ACCOUNT_PACKAGE'):
                        #         msg = 'FedEx SS rate %s %s replaced with %s' % (ssr['serviceCode'], ssr['otherCost'] + ssr['shipmentCost'], fr['shipmentCost'])
                        #         logging.info(msg)
                        #         replace_log += msg + '\n'
                        #         ssr['otherCost'] = 0
                        #         ssr['shipmentCost'] = fr['shipmentCost']
                        #         ssr['RateType'] = fr['RateType']
                        #         break
                        result = fedex_result
                    except Exception as e:
                        logging.error(e)
            for rate in result:
                total_rate = rate['shipmentCost'] + rate['otherCost']
                if rate.get('fedex_code'):
                    service_id = allowed_service_ids.filtered(lambda x: x.fedex_code == rate['fedex_code'] and x.carrier_id.id == c.id)
                else:
                    service_id = allowed_service_ids.filtered(lambda x: x.ss_code == rate['serviceCode'] and x.carrier_id.id == c.id)
                if first_result:
                    if service_id:
                        cheapest_rate = total_rate
                        cheapest_service_id = service_id[0]
                        first_result = False
                if not first_result and total_rate < cheapest_rate and service_id:
                    cheapest_rate = total_rate
                    cheapest_service_id = service_id[0]
        # self.services_prices_log = log + '\n' + replace_log
        if cheapest_service_id:
            return {'rate': cheapest_rate, 'service_id': cheapest_service_id.id, 'package_id': cheapest_service_id.package_id.id, 'exceeds_limits': False}
        else:
            return {'rate': 0.0, 'service_id': False, 'package_id': False, 'exceeds_limits': False}

    @api.multi
    def button_get_cheapest_service(self):
        for so in self:
            service = so.get_cheapest_service()
            so.write({
                'rate': service.get('rate'),
                'service_id': service.get('service_id'),
                'package_id': service.get('package_id'),
                'exceeds_limits': service['exceeds_limits'] if service.get('exceeds_limits') else False
            })

    @api.multi
    def get_update_shipment_rate(self):
        self.ensure_one()
        data = {
            'carrierCode': self.carrier_id.ss_code,
            'serviceCode': self.service_id.ss_code,
            'packageCode': self.package_id.ss_code,
            'fromPostalCode': self.warehouse_id.partner_id.zip,
            'toPostalCode': self.partner_id.zip,
            'toState': self.partner_id.state_id.code,
            'toCountry': self.partner_id.country_id.code,
            'toCity': self.partner_id.city,
            'weight': {
                'value': self.weight,
                'units': 'pounds'
            },
            'dimensions': {
                'units': 'inches',
                'length': self.length,
                'width': self.width,
                'height': self.height
            },
            'confirmation': 'delivery'
        }
        fedex_carrier = self.env['ship.carrier'].browse(1)
        residential = fedex_carrier.fedex_validate_address(self, data)
        data['residential'] = residential
        result = self.ss_execute_request('POST', '/shipments/getrates', data)
        for rate in result:
            return rate['shipmentCost'] + rate['otherCost']

    @api.multi
    def button_update_shipment_rate(self):
        for so in self:
            rate = so.get_update_shipment_rate()
            self.write({'rate': rate})
