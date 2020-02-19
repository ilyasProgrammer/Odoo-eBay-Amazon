# -*- coding: utf-8 -*-

from odoo import models, fields, api
from fedex_request import FedexRequest
import binascii
from datetime import datetime
import sys
import os
import logging
from fedex.services.address_validation_service import FedexAddressValidationRequest
from fedex.tools.conversion import sobject_to_dict
from fedex.services.rate_service import FedexRateServiceRequest
from fedex.config import FedexConfig
from fedex.services.ship_service import FedexProcessShipmentRequest
logging.getLogger('suds.client').setLevel(logging.WARNING)
logging.getLogger('suds.transport').setLevel(logging.WARNING)
logging.getLogger('suds.xsd.schema').setLevel(logging.WARNING)
logging.getLogger('suds.wsdl').setLevel(logging.WARNING)
logging.getLogger('suds.resolver').setLevel(logging.WARNING)
logging.getLogger('suds.xsd.query').setLevel(logging.WARNING)
logging.getLogger('suds.xsd.basic').setLevel(logging.WARNING)
logging.getLogger('suds.binding.marshaller').setLevel(logging.WARNING)
logging.getLogger('fedex.request').setLevel(logging.WARNING)
logging.getLogger('fedex.response').setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.INFO)


class CarrierFedex(models.Model):
    _inherit = 'ship.carrier'

    fedex_developer_key = fields.Char(string="Developer Key", required_if_name='fedex')
    fedex_developer_password = fields.Char(string="Password", required_if_name='fedex')
    fedex_account_number = fields.Char(string="Account Number", required_if_name='fedex')
    fedex_meter_number = fields.Char(string="Meter Number", required_if_name='fedex')
    fedex_environment = fields.Selection([('test', 'Test'), ('production', 'Production')], string="Environment", required_if_name='fedex')
    max_girth = fields.Float('Maximum Girth', default=130)

    def fedex_get_status_of_tracking_number(self, shipment):
        if shipment:
            # Authentication stuff
            srm = FedexRequest(request_type="track", environment=self.fedex_environment)
            srm.web_authentication_detail(self.fedex_developer_key, self.fedex_developer_password)
            srm.client_detail(self.fedex_account_number, self.fedex_meter_number)
            # Build tracking status request
            srm.selection_details(shipment.tracking_number)
            response = srm.send_track_request()
            if response.get('tracking_details') and response.get('status') == 'failed':
                shipment.shipping_state = 'failed'
                return str(response.get('tracking_details'))
            if response.get('tracking_details') and response['tracking_details'].Notification.Severity == 'ERROR':
                shipment.shipping_state = 'failed'
                return str(response.get('tracking_details').Notification.Message)
            if response.get('tracking_details') and response['tracking_details'].Notification.Severity == 'SUCCESS':
                if response.get('tracking_details').StatusDetail.Code in ['DE', 'CA', 'SE']:
                    shipment.shipping_state = 'failed'
                    return str(response.get('tracking_details').StatusDetail.AncillaryDetails[0].ReasonDescription) + ' [' + fields.Datetime.to_string((response.get('tracking_details').StatusDetail.CreationTime)) + ']'
                if response.get('tracking_details').StatusDetail.Code == 'DL':
                    shipment.shipping_state = 'done'
                    return (str(response.get('tracking_details').StatusDetail.Description)) + ' [' + fields.Datetime.to_string((response.get('tracking_details').StatusDetail.CreationTime)) + ']'
                if response.get('tracking_details').StatusDetail.Code in ['IN', 'AA', 'AR', 'AD', 'AF', 'CH', 'DP', 'EO', 'EP', 'FD', 'HL', 'LO', 'OD', 'PF', 'DR', 'DS', 'DY', 'EA', 'ED', 'EO', 'EP', 'PL', 'PU', 'RS', 'SF', 'SP', 'TR']:
                    shipment.shipping_state = 'in_transit'
                    return (str(response.get('tracking_details').StatusDetail.Description)) + ' [' + fields.Datetime.to_string((response.get('tracking_details').StatusDetail.CreationTime)) + ']'
                if response.get('tracking_details').StatusDetail.Code in ['AP', 'OC']:
                    shipment.shipping_state = 'waiting_shipment'
                    return (str(response.get('tracking_details').StatusDetail.Description)) + ' [' + fields.Datetime.to_string((response.get('tracking_details').StatusDetail.CreationTime)) + ']'

    def fedex_get_rates(self, picking, data):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Change these values to match your testing account/meter number.
        CONFIG_OBJ = FedexConfig(key=self.fedex_developer_key,
                                 password=self.fedex_developer_password,
                                 account_number=self.fedex_account_number,
                                 meter_number=self.fedex_meter_number,
                                 use_test_server=True if self.fedex_environment == 'test' else False)
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        rr = FedexRateServiceRequest(CONFIG_OBJ, customer_transaction_id=picking.name)
        rr.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
        # rr.RequestedShipment.ServiceType = 'GROUND_HOME_DELIVERY'
        rr.RequestedShipment.PackagingType = 'YOUR_PACKAGING'
        rr.RequestedShipment.RateRequestTypes = 'LIST'
        # Shipper's address
        rr.RequestedShipment.Shipper.Address.StreetLines = '15004 3rd Ave'
        rr.RequestedShipment.Shipper.Address.City = 'Highland Park'
        rr.RequestedShipment.Shipper.Address.PostalCode = '48203-3718'
        rr.RequestedShipment.Shipper.Address.StateOrProvinceCode = 'MI'
        rr.RequestedShipment.Shipper.Address.CountryCode = 'US'

        # Recipient address
        rr.RequestedShipment.Recipient.Address.StreetLines = picking.partner_id.street
        rr.RequestedShipment.Recipient.Address.City = data['toCity']
        rr.RequestedShipment.Recipient.Address.PostalCode = data['toPostalCode']
        rr.RequestedShipment.Recipient.Address.StateOrProvinceCode = data['toState']
        rr.RequestedShipment.Recipient.Address.CountryCode = data['toCountry']
        rr.RequestedShipment.Recipient.Address.Residential = picking.residential


        # rr.RequestedShipment.EdtRequestType = 'NONE'
        rr.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER'

        package1_weight = rr.create_wsdl_object_of_type('Weight')
        package1_weight.Value = int(data['weight']['value'])
        package1_weight.Units = "LB"

        package1_dimensions = rr.create_wsdl_object_of_type('Dimensions')
        package1_dimensions.Length = int(data['dimensions']['length'])
        package1_dimensions.Width = int(data['dimensions']['width'])
        package1_dimensions.Height = int(data['dimensions']['height'])
        package1_dimensions.Units = 'IN'

        package1 = rr.create_wsdl_object_of_type('RequestedPackageLineItem')
        package1.Weight = package1_weight
        package1.Dimensions = package1_dimensions
        package1.PhysicalPackaging = 'BOX'
        package1.GroupPackageCount = 1

        rr.add_package(package1)

        rr.send_request()
        return rr

    def fedex_get_label(self, picking, data):
        GENERATE_IMAGE_TYPE = 'PDF'
        CONFIG_OBJ = FedexConfig(key=self.fedex_developer_key,
                                 password=self.fedex_developer_password,
                                 account_number=self.fedex_account_number,
                                 meter_number=self.fedex_meter_number,
                                 use_test_server=True if self.fedex_environment == 'test' else False)
        shipment = FedexProcessShipmentRequest(CONFIG_OBJ, customer_transaction_id="Label for %s" % picking.name)
        # REGULAR_PICKUP, REQUEST_COURIER, DROP_BOX, BUSINESS_SERVICE_CENTER or STATION
        shipment.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
        # See page 355 in WS_ShipService.pdf for a full list. Here are the common ones:
        # STANDARD_OVERNIGHT, PRIORITY_OVERNIGHT, FEDEX_GROUND, FEDEX_EXPRESS_SAVER,
        # FEDEX_2_DAY, INTERNATIONAL_PRIORITY, SAME_DAY, INTERNATIONAL_ECONOMY
        # shipment.RequestedShipment.ServiceType = data['serviceCode'].upper()  # TODO mapping SS and FedEx
        shipment.RequestedShipment.ServiceType = data['fedex_code']
        # FEDEX_BOX, FEDEX_PAK, FEDEX_TUBE, YOUR_PACKAGING, FEDEX_ENVELOPE
        shipment.RequestedShipment.PackagingType = 'YOUR_PACKAGING'
        # Shipper contact info.
        # shipment.RequestedShipment.Shipper.Contact.PersonName = 'Sender Name'
        shipment.RequestedShipment.Shipper.Contact.CompanyName = 'Vertical4'
        shipment.RequestedShipment.Shipper.Contact.PhoneNumber = '3136408402'
        # Shipper address.
        shipment.RequestedShipment.Shipper.Address.StreetLines = '15004 3rd Ave'
        shipment.RequestedShipment.Shipper.Address.City = 'Highland Park'
        shipment.RequestedShipment.Shipper.Address.PostalCode = '48203-3718'
        shipment.RequestedShipment.Shipper.Address.StateOrProvinceCode = 'MI'
        shipment.RequestedShipment.Shipper.Address.CountryCode = 'US'
        # Recipient contact info.
        shipment.RequestedShipment.Recipient.Contact.PersonName = data['shipTo']['name']
        # shipment.RequestedShipment.Recipient.Contact.CompanyName =
        shipment.RequestedShipment.Recipient.Contact.PhoneNumber = data['shipTo']['phone']
        # Recipient address
        shipment.RequestedShipment.Recipient.Address.StreetLines = picking.partner_id.street
        shipment.RequestedShipment.Recipient.Address.City = data['shipTo']['city']
        shipment.RequestedShipment.Recipient.Address.PostalCode = data['shipTo']['postalCode']
        shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = data['shipTo']['state']
        shipment.RequestedShipment.Recipient.Address.CountryCode = data['shipTo']['country']
        shipment.RequestedShipment.Recipient.Address.Residential = picking.residential
        # shipment.RequestedShipment.Recipient.Address.Residential = False
        # This is needed to ensure an accurate rate quote with the response. Use AddressValidation to get ResidentialStatus
        # shipment.RequestedShipment.Recipient.Address.Residential = True
        shipment.RequestedShipment.EdtRequestType = 'NONE'

        # Senders account information
        shipment.RequestedShipment.ShippingChargesPayment.Payor.ResponsibleParty.AccountNumber = CONFIG_OBJ.account_number

        # Who pays for the shipment?
        # RECIPIENT, SENDER or THIRD_PARTY
        shipment.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER'

        # Specifies the label type to be returned.
        # LABEL_DATA_ONLY or COMMON2D
        shipment.RequestedShipment.LabelSpecification.LabelFormatType = 'COMMON2D'

        # Specifies which format the label file will be sent to you in.
        # DPL, EPL2, PDF, PNG, ZPLII
        shipment.RequestedShipment.LabelSpecification.ImageType = GENERATE_IMAGE_TYPE

        # To use doctab stocks, you must change ImageType above to one of the
        # label printer formats (ZPLII, EPL2, DPL).
        # See documentation for paper types, there quite a few.
        shipment.RequestedShipment.LabelSpecification.LabelStockType = 'STOCK_4X6'
        # This indicates if the top or bottom of the label comes out of the
        # printer first.
        # BOTTOM_EDGE_OF_TEXT_FIRST or TOP_EDGE_OF_TEXT_FIRST
        # Timestamp in YYYY-MM-DDThh:mm:ss format, e.g. 2002-05-30T09:00:00
        shipment.RequestedShipment.ShipTimestamp = datetime.now().replace(microsecond=0).isoformat()

        # BOTTOM_EDGE_OF_TEXT_FIRST, TOP_EDGE_OF_TEXT_FIRST
        shipment.RequestedShipment.LabelSpecification.LabelPrintingOrientation = 'TOP_EDGE_OF_TEXT_FIRST'

        # Delete the flags we don't want.
        # Can be SHIPPING_LABEL_FIRST, SHIPPING_LABEL_LAST or delete
        if hasattr(shipment.RequestedShipment.LabelSpecification, 'LabelOrder'):
            del shipment.RequestedShipment.LabelSpecification.LabelOrder  # Delete, not using.

        package1_weight = shipment.create_wsdl_object_of_type('Weight')
        package1_weight.Value = int(data['weight']['value'])
        package1_weight.Units = "LB"

        package1_dimensions = shipment.create_wsdl_object_of_type('Dimensions')
        package1_dimensions.Length = int(data['dimensions']['length'])
        package1_dimensions.Width = int(data['dimensions']['width'])
        package1_dimensions.Height = int(data['dimensions']['height'])
        package1_dimensions.Units = 'IN'

        package1 = shipment.create_wsdl_object_of_type('RequestedPackageLineItem')
        package1.Weight = package1_weight
        package1.Dimensions = package1_dimensions
        package1.PhysicalPackaging = 'BOX'
        package1.GroupPackageCount = 1
        customer_reference = shipment.create_wsdl_object_of_type('CustomerReference')
        customer_reference.CustomerReferenceType = 'CUSTOMER_REFERENCE'
        customer_reference.Value = picking.origin
        package1.CustomerReferences.append(customer_reference)

        # Add a signature option for the package using SpecialServicesRequested or comment out.
        # SpecialServiceTypes can be APPOINTMENT_DELIVERY, COD, DANGEROUS_GOODS, DRY_ICE, SIGNATURE_OPTION etc..
        # package1.SpecialServicesRequested.SpecialServiceTypes = 'SIGNATURE_OPTION'
        # SignatureOptionType can be ADULT, DIRECT, INDIRECT, NO_SIGNATURE_REQUIRED, SERVICE_DEFAULT
        # package1.SpecialServicesRequested.SignatureOptionDetail.OptionType = 'SERVICE_DEFAULT'
        shipment.add_package(package1)
        shipment.send_request()
        # This will convert the response to a python dict object. To
        # make it easier to work with. Also see basic_sobject_to_dict, it's faster but lacks options.
        response_dict = sobject_to_dict(shipment.response)
        response_dict['CompletedShipmentDetail']['CompletedPackageDetails'][0]['Label']['Parts'][0]['Image'] = ''
        print(response_dict)  # Image is empty string for display purposes.
        # Here is the overall end result of the query.
        print("HighestSeverity: {}".format(shipment.response.HighestSeverity))
        # Getting the tracking number from the new shipment.
        print("Tracking #: {}"
              "".format(shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].TrackingIds[0].TrackingNumber))
        # Net shipping costs. Only show if available. Sometimes sandbox will not include this in the response.
        CompletedPackageDetails = shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0]
        if hasattr(CompletedPackageDetails, 'PackageRating'):
            print("Net Shipping Cost (US$): {}"
                  "".format(CompletedPackageDetails.PackageRating.PackageRateDetails[0].NetCharge.Amount))
        else:
            print('WARNING: Unable to get shipping rate.')
        ascii_label_data = shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].Label.Parts[0].Image
        label_binary_data = binascii.a2b_base64(ascii_label_data)
        out_path = '/var/tmp/example_shipment_label.%s' % GENERATE_IMAGE_TYPE.lower()
        print("Writing to file {}".format(out_path))
        out_file = open(out_path, 'wb')
        out_file.write(label_binary_data)
        out_file.close()
        result = {'trackingNumber': shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].TrackingIds[0].TrackingNumber,
                  'voided': False,
                  'shipmentId': '',
                  'labelData': ascii_label_data}
        return result

    def fedex_validate_address(self, picking, data):
        # NOTE: TO USE ADDRESS VALIDATION SERVICES, YOU NEED TO REQUEST FEDEX TO ENABLE THIS SERVICE FOR YOUR ACCOUNT.
        # BY DEFAULT, THE SERVICE IS DISABLED AND YOU WILL RECEIVE AUTHENTICATION FAILED, 1000 RESPONSE.
        client_language_code = 'EN'
        client_locale_code = 'US'
        CONFIG_OBJ = FedexConfig(key=self.fedex_developer_key,
                                 password=self.fedex_developer_password,
                                 account_number=self.fedex_account_number,
                                 meter_number=self.fedex_meter_number,
                                 use_test_server=True if self.fedex_environment == 'test' else False)
        customer_transaction_id = 'Address validation for %s' % picking.name
        avs_request = FedexAddressValidationRequest(CONFIG_OBJ, customer_transaction_id=customer_transaction_id,
                                                    client_locale_code=client_locale_code,
                                                    client_language_code=client_language_code)

        # Create some addresses to validate
        address1 = avs_request.create_wsdl_object_of_type('AddressToValidate')
        address1.ClientReferenceId = picking.partner_id
        address1.Address.StreetLines = picking.partner_id.street
        address1.Address.City = data['toCity']
        address1.Address.StateOrProvinceCode = data['toState']
        address1.Address.PostalCode = data['toPostalCode']
        address1.Address.CountryCode = data['toCountry']
        avs_request.add_address(address1)

        avs_request.send_request()

        if len(avs_request.response.AddressResults):
            is_resident = avs_request.response.AddressResults[0].Classification != 'BUSINESS'  # Non BUSINESS means residential address
            return is_resident
        else:
            return False  # by default consider it false


class CarrierService(models.Model):
    _inherit = 'ship.carrier.service'

    fedex_code = fields.Char('FedExCode')
    oversized = fields.Boolean('Oversized Service', default=False)
