# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
import logging
import os
import suds  # should work with suds or its fork suds-jurko

from datetime import datetime
from suds.client import Client
from urllib2 import URLError

_logger = logging.getLogger(__name__)
# uncomment to enable logging of SOAP requests and responses
logging.getLogger('suds.client').setLevel(logging.DEBUG)

class FedexRequest():
    """ Low-level object intended to interface Odoo recordsets with FedEx,
        through appropriate SOAP requests """

    def __init__(self, request_type="", environment='test'):
        if request_type == "track":
            if environment == 'test':
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/test/TrackService_v12.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/prod/TrackService_v12.wsdl')
            self.track(wsdl_path)
        if request_type == "rates":
            if environment == 'test':
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/test/RateService_v20.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/prod/RateService_v20.wsdl')
            self.rates(wsdl_path)

    # Authentification stuff

    def web_authentication_detail(self, key, password):
        WebAuthenticationCredential = self.client.factory.create('WebAuthenticationCredential')
        WebAuthenticationCredential.Key = key
        WebAuthenticationCredential.Password = password
        self.WebAuthenticationDetail = self.client.factory.create('WebAuthenticationDetail')
        self.WebAuthenticationDetail.UserCredential = WebAuthenticationCredential

    def transaction_detail(self, transaction_id):
        self.TransactionDetail = self.client.factory.create('TransactionDetail')
        self.TransactionDetail.CustomerTransactionId = transaction_id

    def client_detail(self, account_number, meter_number):
        self.ClientDetail = self.client.factory.create('ClientDetail')
        self.ClientDetail.AccountNumber = account_number
        self.ClientDetail.MeterNumber = meter_number

    # Versioning

    def track(self, wsdl_path):
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'))
        self.VersionId = self.client.factory.create('VersionId')
        self.VersionId.ServiceId = 'trck'
        self.VersionId.Major = '12'
        self.VersionId.Intermediate = '0'
        self.VersionId.Minor = '0'

    def rates(self, wsdl_path):
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'))
        self.VersionId = self.client.factory.create('VersionId')
        self.VersionId.ServiceId = 'crs'
        self.VersionId.Major = '20'
        self.VersionId.Intermediate = '0'
        self.VersionId.Minor = '0'

    # Common stuff

    def set_shipper(self, warehouse_partner):
        Contact = self.client.factory.create('Contact')
        Contact.PersonName = warehouse_partner.name if not warehouse_partner.is_company else 'NONE'
        Contact.CompanyName = warehouse_partner.name if warehouse_partner.is_company else ''
        Contact.PhoneNumber = warehouse_partner.phone or ''
        # TODO fedex documentation asks for TIN number, but it seems to work without

        Address = self.client.factory.create('Address')
        Address.StreetLines = ('%s %s') % (warehouse_partner.street or '', warehouse_partner.street2 or '')
        Address.City = warehouse_partner.city or ''
        Address.StateOrProvinceCode = warehouse_partner.state_id.code or ''
        Address.PostalCode = warehouse_partner.zip or ''
        Address.CountryCode = warehouse_partner.country_id.code or ''

        self.RequestedShipment.Shipper.Contact = Contact
        self.RequestedShipment.Shipper.Address = Address

    def set_recipient(self, recipient_partner):
        Contact = self.client.factory.create('Contact')
        Contact.PersonName = recipient_partner.name if not recipient_partner.is_company else 'NONE'
        Contact.CompanyName = recipient_partner.name if recipient_partner.is_company else 'NONE'
        Contact.PhoneNumber = recipient_partner.phone or ''

        Address = self.client.factory.create('Address')
        Address.StreetLines = ('%s %s') % (recipient_partner.street or '', recipient_partner.street2 or '')
        Address.City = recipient_partner.city or ''
        Address.StateOrProvinceCode = recipient_partner.state_id.code or ''
        Address.PostalCode = recipient_partner.zip or ''
        Address.CountryCode = recipient_partner.country_id.code or ''

        self.RequestedShipment.Recipient.Contact = Contact
        self.RequestedShipment.Recipient.Address = Address

    def set_shipment(self, shipment, account_number):
        self.RequestedShipment = self.client.factory.create('RequestedShipment')
        self.RequestedShipment.ShipTimestamp = datetime.now()
        self.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
        self.RequestedShipment.PackagingType = 'YOUR_PACKAGE'
        self.RequestedShipment.ServiceType = 'FEDEX_GROUND'
        self.RequestedShipment.EdtRequestType = 'NONE'
        self.RequestedShipment.RateRequestTypes = 'LIST'
        self.RequestedShipment.PackageCount = 1
        self.RequestedShipment.TotalWeight.Units = 'LB'
        self.RequestedShipment.TotalWeight.Value = 20.0
        
        Payment = self.client.factory.create('Payment')
        Payment.PaymentType = 'SENDER'
        Payment.Payor = self.client.factory.create('Payor')
        Payment.Payor.ResponsibleParty = self.client.factory.create('Party')
        Payment.Payor.ResponsibleParty.AccountNumber = account_number
        self.RequestedShipment.ShippingChargesPayment = Payment

        RequestedPackageLineItems = []

        RequestedPackageLineItem = self.client.factory.create('RequestedPackageLineItem')
        RequestedPackageLineItem.SequenceNumber = 1
        RequestedPackageLineItem.GroupNumber = 1
        RequestedPackageLineItem.GroupPackageCount = 1
        RequestedPackageLineItem.Weight.Units = 'LB'
        RequestedPackageLineItem.Weight.Value = 20.0
        RequestedPackageLineItem.Dimensions.Units = 'IN'
        RequestedPackageLineItem.Dimensions.Length = 12
        RequestedPackageLineItem.Dimensions.Width = 12
        RequestedPackageLineItem.Dimensions.Height = 12
        RequestedPackageLineItem.ContentRecords = []
        ContentRecord = self.client.factory.create('ContentRecord')
        ContentRecord.PartNumber = '123455'
        ContentRecord.ItemNumber = '123455'
        ContentRecord.ReceivedQuantity = 12
        ContentRecord.Description = 'ContentDescription'
        RequestedPackageLineItem.ContentRecords.append(ContentRecord)
        RequestedPackageLineItem.PhysicalPackaging = 'BOX'
        RequestedPackageLineItems.append(RequestedPackageLineItem)

        self.RequestedShipment.RequestedPackageLineItems = RequestedPackageLineItems

    def set_currency(self, currency):
        self.RequestedShipment.PreferredCurrency = currency
        # self.RequestedShipment.RateRequestTypes = 'PREFERRED'

    def shipment_request(self, dropoff_type, service_type, packaging_type, overall_weight_unit):
        self.RequestedShipment = self.client.factory.create('RequestedShipment')
        self.RequestedShipment.ShipTimestamp = datetime.now()
        self.RequestedShipment.DropoffType = dropoff_type
        self.RequestedShipment.ServiceType = service_type
        self.RequestedShipment.PackagingType = packaging_type
        # Resuest estimation of duties and taxes for international shipping
        if service_type in ['INTERNATIONAL_ECONOMY', 'INTERNATIONAL_PRIORITY']:
            self.RequestedShipment.EdtRequestType = 'ALL'
        else:
            self.RequestedShipment.EdtRequestType = 'NONE'
        self.RequestedShipment.PackageCount = 0
        self.RequestedShipment.TotalWeight.Units = 'LB'
        self.RequestedShipment.TotalWeight.Value = 0
        self.listCommodities = []

    def set_master_package(self, total_weight, package_count, master_tracking_id=False):
        self.RequestedShipment.TotalWeight.Value = total_weight
        self.RequestedShipment.PackageCount = package_count
        if master_tracking_id:
            self.RequestedShipment.MasterTrackingId = self.client.factory.create('TrackingId')
            self.RequestedShipment.MasterTrackingId.TrackingIdType = 'FEDEX'
            self.RequestedShipment.MasterTrackingId.TrackingNumber = master_tracking_id

    def add_package(self, weight_value, sequence_number=False, mode='shipping'):
        package = self.client.factory.create('RequestedPackageLineItem')
        package_weight = self.client.factory.create('Weight')
        package_weight.Value = weight_value
        package_weight.Units = self.RequestedShipment.TotalWeight.Units

        package.PhysicalPackaging = 'BOX'
        package.Weight = package_weight
        if mode == 'rating':
            package.GroupPackageCount = 1
        if sequence_number:
            package.SequenceNumber = sequence_number
        else:
            self.hasOnePackage = True

        if mode == 'rating':
            self.RequestedShipment.RequestedPackageLineItems.append(package)
        else:
            self.RequestedShipment.RequestedPackageLineItems = package

    def selection_details(self, tracking_number):
        self.SelectionDetails = self.client.factory.create('TrackSelectionDetail')
        self.SelectionDetails.CarrierCode = 'FDXG'
        self.SelectionDetails.OperatingCompany = 'FEDEX_GROUND'
        self.SelectionDetails.PackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
        self.SelectionDetails.PackageIdentifier.Value = tracking_number
    # Requests

    def request_rates(self):
        formatted_response = {}
        self.response = self.client.service.getRates(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                                     ClientDetail=self.ClientDetail,
                                                     Version=self.VersionId,
                                                     RequestedShipment=self.RequestedShipment)
        return formatted_response

    def send_track_request(self):
        self.response = self.client.service.track(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                                  ClientDetail=self.ClientDetail,
                                                  Version=self.VersionId,
                                                  SelectionDetails=[self.SelectionDetails])
        try:
            formatted_response = {}
            self.response = self.client.service.track(WebAuthenticationDetail=self.WebAuthenticationDetail,
                                                      ClientDetail=self.ClientDetail,
                                                      Version=self.VersionId,
                                                      SelectionDetails=[self.SelectionDetails])

            if self.response.HighestSeverity == 'FAILURE' or self.response.HighestSeverity == 'ERROR':
                formatted_response['status'] = 'failed'
                formatted_response['tracking_details'] = 'Service is currently unavailable'
            if self.response.HighestSeverity != 'ERROR' and self.response.HighestSeverity == 'SUCCESS':
                formatted_response['tracking_details'] = self.response.CompletedTrackDetails[0].TrackDetails[0]

            # if (self.response.HighestSeverity != 'ERROR' and self.response.HighestSeverity != 'FAILURE'):
            #     print '===============RESPOSNN %s' %self.response
            #     for rating in self.response.RateReplyDetails[0].RatedShipmentDetails:
            #         formatted_response['price'][rating.ShipmentRateDetail.TotalNetFedExCharge.Currency] = rating.ShipmentRateDetail.TotalNetFedExCharge.Amount
            #     if len(self.response.RateReplyDetails[0].RatedShipmentDetails) == 1:
            #         if 'CurrencyExchangeRate' in self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail:
            #             formatted_response['price'][self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail.CurrencyExchangeRate.FromCurrency] = self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail.TotalNetFedExCharge.Amount / self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail.CurrencyExchangeRate.Rate
            # else:
            #     errors_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if (n.Severity == 'ERROR' or n.Severity == 'FAILURE')])
            #     formatted_response['errors_message'] = errors_message

            # if any([n.Severity == 'WARNING' for n in self.response.Notifications]):
            #     warnings_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if n.Severity == 'WARNING'])
            #     formatted_response['warnings_message'] = warnings_message

        except suds.WebFault as fault:
            print '--------------------------  %s' %suds
            formatted_response['errors_message'] = fault
        except URLError:
            formatted_response['errors_message'] = "Fedex Server Not Found"

        return formatted_response