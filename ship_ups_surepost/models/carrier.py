# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urllib
import xml.etree.ElementTree as ET

from odoo import models, fields, api
from ups_request import UPSRequest, Package

class CarrierPackage(models.Model):
    _inherit = 'ship.carrier.package'

    api_code = fields.Char('API Package Code', help="Code of the package as provided by carrier.")

class CarrierService(models.Model):
    _inherit = 'ship.carrier.service'

    api_code = fields.Char('API Service Code', help="Code of the package as provided by carrier.")

class Carrier(models.Model):
    _inherit = 'ship.carrier'

    @api.multi
    def get_environment(self):
        return True if self.ups_environment == 'production' else False

    @api.multi
    def ups_get_rates(self, so_id):
        """Handle SurePost services for now, extend later for other services. Use shipstation API for getting rates of other services

        Parameters
        ----------
        so_id : recordset, a sales order recordsey
        """
        self.ensure_one()

        if self.ups_environment == 'production':
            url = 'https://onlinetools.ups.com/ups.app/xml/Rate'
        else:
            url = 'https://wwwcie.ups.com/ups.app/xml/Rate'
        url = 'https://onlinetools.ups.com/ups.app/xml/Rate'
        url = 'https://wwwcie.ups.com/ups.app/xml/Rate'

        service_id = self.env.ref('ship_ups_surepost.service_ups_surepost_less_1_lb')
        if so_id.weight > 1:
            service_id = self.env.ref('ship_ups_surepost.service_ups_surepost_1_lb_or_greater')

        weight = so_id.weight
        weight_unit = 'LBS'

        # SurePost Less than 1 lb should use ounces as weight unit of measure
        if service_id.api_code == '92':
            weight = round(so_id.weight * 16, 1)
            weight_unit = 'OZS'

        ship_from_partner_id = so_id.warehouse_id.partner_id
        ship_to_partner_id = so_id.partner_id

        request_dict = {
            'user_id': self.ups_user_id,
            'password': self.ups_password,
            'access_license_number': self.ups_access_license_number,
            'shipper_number': self.ups_shipper_number,
            'ship_from_name': ship_from_partner_id.name,
            'ship_from_street': ship_from_partner_id.street,
            'ship_from_street2': ship_from_partner_id.street2 or '',
            'ship_from_city': ship_from_partner_id.city,
            'ship_from_state': ship_from_partner_id.state_id.code,
            'ship_from_country': ship_from_partner_id.country_id.code,
            'ship_from_zip': ship_from_partner_id.zip,
            'ship_to_name': ship_to_partner_id.name,
            'ship_to_street': ship_to_partner_id.street,
            'ship_to_street2': ship_to_partner_id.street2 or '',
            'ship_to_city': ship_to_partner_id.city,
            'ship_to_state': ship_to_partner_id.state_id.code,
            'ship_to_country': ship_to_partner_id.country_id.code,
            'ship_to_zip': ship_to_partner_id.zip,
            'service_code': service_id.api_code,
            'package_code': service_id.package_id.api_code,
            'length': so_id.length,
            'width': so_id.width,
            'height': so_id.height,
            'dim_unit': 'IN',
            'weight': weight,
            'weight_unit': weight_unit
        }
        request_xml = """<?xml version="1.0"?>
            <AccessRequest xml:lang="en-US">
                <AccessLicenseNumber>%(access_license_number)s</AccessLicenseNumber>
                <UserId>%(user_id)s</UserId>
                <Password>%(password)s</Password>
            </AccessRequest>
            <?xml version="1.0"?>
            <RatingServiceSelectionRequest xml:lang="en-US">
                <Request>
                    <TransactionReference>
                        <CustomerContext>Rate</CustomerContext>
                    </TransactionReference>
                    <RequestAction>Rate</RequestAction>
                    <RequestOption>Rate</RequestOption>
                </Request>
                <Shipment>
                    <RateInformation>
                        <NegotiatedRatesIndicator/>
                    </RateInformation>
                    <Shipper>
                        <Name>%(ship_from_name)s</Name>
                        <ShipperNumber>%(shipper_number)s</ShipperNumber>
                        <Address>
                            <AddressLine1>%(ship_from_street)s</AddressLine1>
                            <AddressLine2>%(ship_from_street2)s</AddressLine2>
                            <City>%(ship_from_city)s</City>
                            <StateProvinceCode>%(ship_from_state)s</StateProvinceCode>
                            <PostalCode>%(ship_from_zip)s</PostalCode>
                            <CountryCode>%(ship_from_country)s</CountryCode>
                        </Address>
                    </Shipper>
                    <ShipTo>
                        <Name>%(ship_to_name)s</Name>r>
                        <Address>
                            <AddressLine1>%(ship_to_street)s</AddressLine1>
                            <AddressLine2>%(ship_to_street2)s</AddressLine2>
                            <City>%(ship_to_city)s</City>
                            <StateProvinceCode>%(ship_to_state)s</StateProvinceCode>
                            <PostalCode>%(ship_to_zip)s</PostalCode>
                            <CountryCode>%(ship_to_country)s</CountryCode>
                        </Address>
                    </ShipTo>
                    <ShipFrom>
                        <Name>%(ship_from_name)s</Name>r>
                        <Address>
                            <AddressLine1>%(ship_from_street)s</AddressLine1>
                            <AddressLine2>%(ship_from_street2)s</AddressLine2>
                            <City>%(ship_from_city)s</City>
                            <StateProvinceCode>%(ship_from_state)s</StateProvinceCode>
                            <PostalCode>%(ship_from_zip)s</PostalCode>
                            <CountryCode>%(ship_from_country)s</CountryCode>
                        </Address>
                    </ShipFrom>
                    <Service>
                        <Code>%(service_code)s</Code>
                    </Service>
                    <Package>
                        <PackagingType>
                            <Code>%(package_code)s</Code>
                        </PackagingType>
                        <PackageWeight>
                            <UnitOfMeasurement>
                                <Code>%(weight_unit)s</Code>
                            </UnitOfMeasurement>
                            <Weight>%(weight)s</Weight>
                        </PackageWeight>
                        <Dimensions>
                            <Length>%(length)s</Length>
                            <Width>%(width)s</Width>
                            <Height>%(height)s</Height>
                        </Dimensions>
                    </Package>
                </Shipment>
            </RatingServiceSelectionRequest>
        """ %(request_dict)

        # try:
        res = ET.fromstring(urllib.urlopen(url, request_xml.encode('ascii', 'xmlcharrefreplace')).read())
        print ET.tostring(res, encoding='utf8', method='xml')
        amount = float(res.find('RatedShipment').find('TotalCharges').find('MonetaryValue').text)
        print amount
        return amount

        # print amount
