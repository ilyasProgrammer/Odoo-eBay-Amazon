# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import binascii
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
from PIL import Image
import logging
import os
import re
from urllib2 import URLError

import suds
from suds.client import Client
from suds.plugin import MessagePlugin
from suds.sax.element import Element

SUDS_VERSION = suds.__version__

from odoo import _
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)
# uncomment to enable logging of SOAP requests and responses
# logging.getLogger('suds.client').setLevel(logging.DEBUG)


UPS_ERROR_MAP = {
    '110002': "Please provide at least one item to ship.",
    '110208': "Please set a valid country in the recipient address.",
    '110308': "Please set a valid country in the warehouse address.",
    '110548': "A shipment cannot have a KGS/IN or LBS/CM as its unit of measurements. Configure it from the delivery method.",
    '111057': "This measurement system is not valid for the selected country. Please switch from LBS/IN to KGS/CM (or vice versa). Configure it from the delivery method.",
    '111091': "The selected service is not possible from your warehouse to the recipient address, please choose another service.",
    '111100': "The service is invalid from the requested warehouse.",
    '111107': "Please provide a valid zip code in the warehouse address.",
    '111210': "The selected service is not possible to the recipient address, please choose available service.",
    '111212': "Please provide a valid package type available for service and selected locations.",
    '111500': "The selected service is not valid with the selected packaging.",
    '112111': "Please provide a valid shipper number.",
    '113020': "Please provide a valid zip code in the warehouse address.",
    '113021': "Please provide a valid zip code in the recipient address.",
    '120031': "Exceeds Total Number of allowed pieces per World Wide Express Shipment.",
    '120100': "Please provide a valid shipper number.",
    '120102': "Please provide a valid street in shipper's address.",
    '120105': "Please provide a valid city in the shipper's address.",
    '120106': "Please provide a valid state in the shipper's address.",
    '120107': "Please provide a valid zip code in the shipper's address.",
    '120108': "Please provide a valid country in the shipper's address.",
    '120109': "Please provide a valid shipper phone number.",
    '120113': "Shipper number must contain alphanumeric characters only.",
    '120114': "Shipper phone extension cannot exceed the length of 4.",
    '120115': "Shipper Phone must be at least 10 alphanumeric characters.",
    '120116': "Shipper phone extension must contain only numbers.",
    '120122': "Please provide a valid shipper Number.",
    '120124': "The requested service is unavailable between the selected locations.",
    '120202': "Please provide a valid street in the recipient address.",
    '120205': "Please provide a valid city in the recipient address.",
    '120206': "Please provide a valid state in the recipient address.",
    '120207': "Please provide a valid zipcode in the recipient address.",
    '120208': "Please provide a valid Country in recipient's address.",
    '120209': "Please provide a valid phone number for the recipient.",
    '120212': "Recipient PhoneExtension cannot exceed the length of 4.",
    '120213': "Recipient Phone must be at least 10 alphanumeric characters.",
    '120214': "Recipient PhoneExtension must contain only numbers.",
    '120302': "Please provide a valid street in the warehouse address.",
    '120305': "Please provide a valid City in the warehouse address.",
    '120306': "Please provide a valid State in the warehouse address.",
    '120307': "Please provide a valid Zip in the warehouse address.",
    '120308': "Please provide a valid Country in the warehouse address.",
    '120309': "Please provide a valid warehouse Phone Number",
    '120312': "Warehouse PhoneExtension cannot exceed the length of 4.",
    '120313': "Warehouse Phone must be at least 10 alphanumeric characters.",
    '120314': "Warehouse Phone must contain only numbers.",
    '120412': "Please provide a valid shipper Number.",
    '121057': "This measurement system is not valid for the selected country. Please switch from LBS/IN to KGS/CM (or vice versa). Configure it from delivery method",
    '121210': "The requested service is unavailable between the selected locations.",
    '128089': "Access License number is Invalid. Provide a valid number (Length sholuld be 0-35 alphanumeric characters)",
    '190001': "Cancel shipment not available at this time , Please try again Later.",
    '190100': "Provided Tracking Ref. Number is invalid.",
    '190109': "Provided Tracking Ref. Number is invalid.",
    '250001': "Access License number is invalid for this provider.Please re-license.",
    '250002': "Username/Password is invalid for this delivery provider.",
    '250003': "Access License number is invalid for this delivery provider.",
    '250004': "Username/Password is invalid for this delivery provider.",
    '250006': "The maximum number of user access attempts was exceeded. So please try again later",
    '250007': "The UserId is currently locked out; please try again in 24 hours.",
    '250009': "Provided Access License Number not found in the UPS database",
    '250038': "Please provide a valid shipper number.",
    '250047': "Access License number is revoked contact UPS to get access.",
    '250052': "Authorization system is currently unavailable , try again later.",
    '250053': "UPS Server Not Found",
    '9120200': "Please provide at least one item to ship"
}


class Package():
    def __init__(self, service_code, api_code, weight, length, width, height):
        self.code = api_code
        self.length = length
        self.width = width
        self.height = height
        self.dimension_unit = 'IN'

        # SurePost Less than 1 lb should use ounces as weight unit of measure
        if service_code == '92':
            self.weight = round(weight * 16, 1)
            self.weight_unit = 'OZS'
        else:
            self.weight = weight
            self.weight_unit = 'LBS'

class FixRequestNamespacePlug(MessagePlugin):
    def __init__(self, root):
        self.root = root

    def marshalled(self, context):
        context.envelope.getChild('Body').getChild(self.root).getChild('Request').prefix = 'ns0'
        context.envelope = context.envelope.prune()


class UPSRequest():
    def __init__(self, username, password, shipper_number, access_number, prod_environment):
        # Product and Testing url
        self.endurl = "https://onlinetools.ups.com/webservices/"
        if not prod_environment:
            self.endurl = "https://wwwcie.ups.com/webservices/"

        # Basic detail require to authenticate
        self.username = username
        self.password = password
        self.shipper_number = shipper_number
        self.access_number = access_number

        self.rate_wsdl = '../api/RateWS.wsdl'
        self.ship_wsdl = '../api/Ship.wsdl'
        self.void_wsdl = '../api/Void.wsdl'

    def _add_security_header(self, client):
        # set the detail which require to authenticate
        security_ns = ('upss', 'http://www.ups.com/XMLSchema/XOLTWS/UPSS/v1.0')
        security = Element('UPSSecurity', ns=security_ns)

        username_token = Element('UsernameToken', ns=security_ns)
        username = Element('Username', ns=security_ns).setText(self.username)
        password = Element('Password', ns=security_ns).setText(self.password)
        username_token.append(username)
        username_token.append(password)

        service_token = Element('ServiceAccessToken', ns=security_ns)
        license = Element('AccessLicenseNumber', ns=security_ns).setText(self.access_number)
        service_token.append(license)

        security.append(username_token)
        security.append(service_token)

        client.set_options(soapheaders=security)

    def _set_client(self, wsdl, api, root):
        wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), wsdl)
        client = Client('file:///%s' % wsdl_path.lstrip('/'), plugins=[FixRequestNamespacePlug(root)])
        self._add_security_header(client)
        client.set_options(location='%s%s' % (self.endurl, api))
        return client

    def _clean_phone_number(self, phone):
        return re.sub('[^0-9]','', phone)

    def check_required_value(self, shipper, ship_from, ship_to, order=False, picking=False):
        required_field = {'city': 'City', 'zip': 'ZIP code', 'country_id': 'Country', 'phone': 'Phone'}
        # Check required field for shipper
        res = [required_field[field] for field in required_field if not shipper[field]]
        if shipper.country_id.code in ('US', 'CA', 'IE') and not shipper.state_id.code:
            res.append('State')
        if not shipper.street and not shipper.street2:
            res.append('Street')
        if res:
            raise ValidationError(_("The address of your company is missing or wrong.\n(Missing field(s) : %s)") % ",".join(res))
        if len(self._clean_phone_number(shipper.phone)) < 10:
            raise ValidationError(_(UPS_ERROR_MAP.get('120115')))
        # Check required field for warehouse address
        res = [required_field[field] for field in required_field if not ship_from[field]]
        if ship_from.country_id.code in ('US', 'CA', 'IE') and not ship_from.state_id.code:
            res.append('State')
        if not ship_from.street and not ship_from.street2:
            res.append('Street')
        if res:
            raise ValidationError(_("The address of your warehouse is missing or wrong.\n(Missing field(s) : %s)") % ",".join(res))
        if len(self._clean_phone_number(ship_from.phone)) < 10:
            raise ValidationError(_(UPS_ERROR_MAP.get('120313')))
        # Check required field for recipient address
        res = [required_field[field] for field in required_field if not ship_to[field]]
        if ship_to.country_id.code in ('US', 'CA', 'IE') and not ship_to.state_id.code:
            res.append('State')
        if not ship_to.street and not ship_to.street2:
            res.append('Street')
        if res:
            raise ValidationError(_("The recipient address is missing or wrong.\n(Missing field(s) : %s)") % ",".join(res))
        if len(self._clean_phone_number(ship_to.phone)) < 10:
            raise ValidationError(_(UPS_ERROR_MAP.get('120213')))
        if order:
            if not order.order_line:
                raise ValidationError(_("Please provide at least one item to ship."))
            for line in order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and not line.product_id.type in ['service', 'digital']):
                raise ValidationError(_("The estimated price cannot be computed because the weight of your product is missing."))
        if picking:
            for move in picking.move_lines.filtered(lambda move: not move.product_id.weight):
                raise ValidationError(_("The delivery cannot be done because the weight of your product is missing."))
        return True

    def get_error_message(self, error_code, description):
        result = {}
        result['error_message'] = UPS_ERROR_MAP.get(error_code)
        if not result['error_message']:
            result['error_message'] = description
        return result

    def save_label(self, image64, label_file_type='GIF'):
        if label_file_type == 'GIF':
            # Label format is GIF, so need to rotate and convert as PDF
            img_decoded = base64.decodestring(image64)
            image_string = StringIO.StringIO(img_decoded)
            im = Image.open(image_string)
            label_result = StringIO.StringIO()
            im.save(label_result, 'pdf')
            return binascii.a2b_base64(label_result.getvalue().encode('base64'))
        else:
            return binascii.a2b_base64(image64)

    def set_package_detail(self, client, packages, packaging_type, namespace, ship_from, ship_to):
        Packages = []
        for i, p in enumerate(packages):
            package = client.factory.create('{}:PackageType'.format(namespace))
            if hasattr(package, 'Packaging'):
                package.Packaging.Code = packaging_type or ''
            elif hasattr(package, 'PackagingType'):
                package.PackagingType.Code = packaging_type or ''

            if p.dimension_unit:
                package.Dimensions.UnitOfMeasurement.Code = p.dimension_unit or ''
                package.Dimensions.Length = p.length or ''
                package.Dimensions.Width = p.width or ''
                package.Dimensions.Height = p.height or ''

            package.PackageWeight.UnitOfMeasurement.Code = p.weight_unit or ''
            package.PackageWeight.Weight = p.weight or ''

            # Package and shipment reference text is only allowed for shipments within
            # the USA and within Puerto Rico. This is a UPS limitation.
            # if (p.name and ship_from.country_id.code in ('US') and ship_to.country_id.code in ('US')):
            #     reference_number = client.factory.create('ns3:ReferenceNumberType')
            #     reference_number.Code = 'PM'
            #     reference_number.Value =
            #     reference_number.BarCodeIndicator = p.name
            #     package.ReferenceNumber = reference_number

            Packages.append(package)
        return Packages

    def get_shipping_price(self, shipment_info, packages, shipper, ship_from, ship_to, packaging_type, service_type):
        client = self._set_client(self.rate_wsdl, 'Rate', 'RateRequest')

        request = client.factory.create('ns0:RequestType')
        request.RequestOption = 'Rate'

        classification = client.factory.create('ns2:CodeDescriptionType')
        classification.Code = '00'  # Get rates for the shipper account
        classification.Description = 'Get rates for the shipper account'

        namespace = 'ns2'
        shipment = client.factory.create('{}:ShipmentType'.format(namespace))

        for package in self.set_package_detail(client, packages, packaging_type, namespace, ship_from, ship_to):
            shipment.Package.append(package)

        shipment.Shipper.Name = shipper.name or ''
        shipment.Shipper.Address.AddressLine = [shipper.street or '', shipper.street2 or '']
        shipment.Shipper.Address.City = shipper.city or ''
        shipment.Shipper.Address.PostalCode = shipper.zip or ''
        shipment.Shipper.Address.CountryCode = shipper.country_id.code or ''
        if shipper.country_id.code in ('US', 'CA', 'IE'):
            shipment.Shipper.Address.StateProvinceCode = shipper.state_id.code or ''
        shipment.Shipper.ShipperNumber = self.shipper_number or ''
        # shipment.Shipper.Phone.Number = shipper.phone or ''

        shipment.ShipFrom.Name = ship_from.name or ''
        shipment.ShipFrom.Address.AddressLine = [ship_from.street or '', ship_from.street2 or '']
        shipment.ShipFrom.Address.City = ship_from.city or ''
        shipment.ShipFrom.Address.PostalCode = ship_from.zip or ''
        shipment.ShipFrom.Address.CountryCode = ship_from.country_id.code or ''
        if ship_from.country_id.code in ('US', 'CA', 'IE'):
            shipment.ShipFrom.Address.StateProvinceCode = ship_from.state_id.code or ''
        # shipment.ShipFrom.Phone.Number = ship_from.phone or ''

        shipment.ShipTo.Name = ship_to.name or ''
        shipment.ShipTo.Address.AddressLine = [ship_to.street or '', ship_to.street2 or '']
        shipment.ShipTo.Address.City = ship_to.city or ''
        shipment.ShipTo.Address.PostalCode = ship_to.zip or ''
        shipment.ShipTo.Address.CountryCode = ship_to.country_id.code or ''
        if ship_to.country_id.code in ('US', 'CA', 'IE'):
            shipment.ShipTo.Address.StateProvinceCode = ship_to.state_id.code or ''
        # shipment.ShipTo.Phone.Number = ship_to.phone or ''
        if not ship_to.commercial_partner_id.is_company:
            shipment.ShipTo.Address.ResidentialAddressIndicator = suds.null()

        shipment.Service.Code = service_type or ''
        shipment.Service.Description = 'Service Code'
        if service_type == "96":
            shipment.NumOfPieces = int(shipment_info.get('total_qty'))
        shipment.ShipmentServiceOptions = ''
        shipment.ShipmentRatingOptions.NegotiatedRatesIndicator = suds.null()

        # try:
            # Get rate using for provided detail
        print "=====SENT ======"
        print client.last_sent()
        print "=====REC ======"
        print client.last_received()
        response = client.service.ProcessRate(Request=request, CustomerClassification=classification, Shipment=shipment)
        print "=====SENT ======"
        print client.last_sent()
        print "=====REC ======"
        print client.last_received()
        # Check if ProcessRate is not success then return reason for that
        if response.Response.ResponseStatus.Code != "1":
            return self.get_error_message(response.Response.ResponseStatus.Code, response.Response.ResponseStatus.Description)

        result = {}
        result['currency_code'] = response.RatedShipment[0].TotalCharges.CurrencyCode

        # Some users are qualified to receive negotiated rates
        negotiated_rate = 'NegotiatedRateCharges' in response.RatedShipment[0] and response.RatedShipment[0].NegotiatedRateCharges.TotalCharge.MonetaryValue or None

        result['price'] = negotiated_rate or response.RatedShipment[0].TotalCharges.MonetaryValue
        return result

        # except suds.WebFault as e:
        #     # childAtPath behaviour is changing at version 0.6
        #     prefix = ''
        #     if SUDS_VERSION >= "0.6":
        #         prefix = '/Envelope/Body/Fault'
        #     return self.get_error_message(e.document.childAtPath(prefix + '/detail/Errors/ErrorDetail/PrimaryErrorCode/Code').getText(),
        #                                   e.document.childAtPath(prefix + '/detail/Errors/ErrorDetail/PrimaryErrorCode/Description').getText())
        # except URLError as e:
        #     return self.get_error_message('0', 'UPS Server Not Found:\n%s' % e)

    def send_shipping(self, shipment_info, packages, shipper, ship_from, ship_to, packaging_type, service_type, label_file_type='GIF'):

        client = self._set_client(self.ship_wsdl, 'Ship', 'ShipmentRequest')

        request = client.factory.create('ns0:RequestType')
        request.RequestOption = 'nonvalidate'

        namespace = 'ns3'
        label = client.factory.create('{}:LabelSpecificationType'.format(namespace))

        print client

        label.LabelImageFormat.Code = label_file_type
        label.LabelImageFormat.Description = label_file_type
        if label_file_type != 'GIF':
            label.LabelStockSize.Height = '6'
            label.LabelStockSize.Width = '4'

        shipment = client.factory.create('{}:ShipmentType'.format(namespace))
        shipment.Description = shipment_info.get('description')

        for package in self.set_package_detail(client, packages, packaging_type, namespace, ship_from, ship_to):
            shipment.Package.append(package)

        shipment.Shipper.AttentionName = shipper.name or ''
        shipment.Shipper.Name = shipper.parent_id.name or shipper.name or ''
        shipment.Shipper.Address.AddressLine = [l for l in [shipper.street or '', shipper.street2 or ''] if l]
        shipment.Shipper.Address.City = shipper.city or ''
        shipment.Shipper.Address.PostalCode = shipper.zip or ''
        shipment.Shipper.Address.CountryCode = shipper.country_id.code or ''
        if shipper.country_id.code in ('US', 'CA', 'IE'):
            shipment.Shipper.Address.StateProvinceCode = shipper.state_id.code or ''
        shipment.Shipper.ShipperNumber = self.shipper_number or ''
        shipment.Shipper.Phone.Number = self._clean_phone_number(shipper.phone)

        shipment.ShipFrom.AttentionName = ship_from.name or ''
        shipment.ShipFrom.Name = ship_from.parent_id.name or ship_from.name or ''
        shipment.ShipFrom.Address.AddressLine = [l for l in [ship_from.street or '', ship_from.street2 or ''] if l]
        shipment.ShipFrom.Address.City = ship_from.city or ''
        shipment.ShipFrom.Address.PostalCode = ship_from.zip or ''
        shipment.ShipFrom.Address.CountryCode = ship_from.country_id.code or ''
        if ship_from.country_id.code in ('US', 'CA', 'IE'):
            shipment.ShipFrom.Address.StateProvinceCode = ship_from.state_id.code or ''
        shipment.ShipFrom.Phone.Number = self._clean_phone_number(ship_from.phone)

        shipment.ShipTo.AttentionName = ship_to.name or ''
        shipment.ShipTo.Name = ship_to.parent_id.name or ship_to.name or ''
        shipment.ShipTo.Address.AddressLine = [l for l in [ship_to.street or '', ship_to.street2 or ''] if l]
        shipment.ShipTo.Address.City = ship_to.city or ''
        shipment.ShipTo.Address.PostalCode = ship_to.zip or ''
        shipment.ShipTo.Address.CountryCode = ship_to.country_id.code or ''
        if ship_to.country_id.code in ('US', 'CA', 'IE'):
            shipment.ShipTo.Address.StateProvinceCode = ship_to.state_id.code or ''
        shipment.ShipTo.Phone.Number = self._clean_phone_number(ship_to.phone)
        if not ship_to.commercial_partner_id.is_company:
            shipment.ShipTo.Address.ResidentialAddressIndicator = suds.null()

        shipment.Service.Code = service_type or ''
        shipment.Service.Description = 'Service Code'
        if service_type == "96":
            shipment.NumOfPiecesInShipment = int(shipment_info.get('total_qty'))
        shipment.ShipmentServiceOptions = ''
        shipment.ShipmentRatingOptions.NegotiatedRatesIndicator = suds.null()

        # Shipments from US to CA or PR require extra info
        if ship_from.country_id.code == 'US' and ship_to.country_id.code in ['CA', 'PR']:
            shipment.InvoiceLineTotal.CurrencyCode = shipment_info.get('itl_currency_code')
            shipment.InvoiceLineTotal.MonetaryValue = shipment_info.get('ilt_monetary_value')

        # set the default method for payment using shipper account
        payment_info = client.factory.create('ns3:PaymentInformation')
        shipcharge = client.factory.create('ns3:ShipmentCharge')
        shipcharge.Type = '01'
        shipcharge.BillShipper.AccountNumber = self.shipper_number or ''
        payment_info.ShipmentCharge = shipcharge
        shipment.PaymentInformation = payment_info


        print "=====SENT ======"
        print client.last_sent()
        print "=====REC ======"
        print client.last_received()
        response = client.service.ProcessShipment(
            Request=request, Shipment=shipment,
            LabelSpecification=label)
        print "=====SENT ======"
        print client.last_sent()
        print "=====REC ======"
        print client.last_received()
        # Check if shipment is not success then return reason for that
        if response.Response.ResponseStatus.Code != "1":
            return self.get_error_message(response.Response.ResponseStatus.Code, response.Response.ResponseStatus.Description)

        result = {}
        result['label_binary_data'] = {}
        for package in response.ShipmentResults.PackageResults:
            result['label_binary_data'][package.TrackingNumber] = self.save_label(package.ShippingLabel.GraphicImage, label_file_type=label_file_type)
        result['tracking_ref'] = response.ShipmentResults.ShipmentIdentificationNumber
        result['currency_code'] = response.ShipmentResults.ShipmentCharges.TotalCharges.CurrencyCode

        # Some users are qualified to receive negotiated rates
        negotiated_rate = 'NegotiatedRateCharges' in response.ShipmentResults and response.ShipmentResults.NegotiatedRateCharges.TotalCharge.MonetaryValue or None

        result['price'] = negotiated_rate or response.ShipmentResults.ShipmentCharges.TotalCharges.MonetaryValue
        return result

        # except suds.WebFault as e:
        #     # childAtPath behaviour is changing at version 0.6
        #     prefix = ''
        #     if SUDS_VERSION >= "0.6":
        #         prefix = '/Envelope/Body/Fault'
        #     return self.get_error_message(e.document.childAtPath(prefix + '/detail/Errors/ErrorDetail/PrimaryErrorCode/Code').getText(),
        #                                   e.document.childAtPath(prefix + '/detail/Errors/ErrorDetail/PrimaryErrorCode/Description').getText())
        # except URLError as e:
        #     return self.get_error_message('0', 'UPS Server Not Found:\n%s' % e)

    def cancel_shipment(self, tracking_number):
        client = self._set_client(self.void_wsdl, 'Void', 'VoidShipmentRequest')

        request = client.factory.create('ns0:RequestType')
        request.TransactionReference.CustomerContext = "Cancle shipment"
        voidshipment = client.factory.create('ns2:VoidShipment')
        voidshipment.ShipmentIdentificationNumber = tracking_number or ''

        result = {}
        try:
            response = client.service.ProcessVoid(
                Request=request, VoidShipment=voidshipment
            )
            if response.Response.ResponseStatus.Code == "1":
                return result
            return self.get_error_message(response.Response.ResponseStatus.Code, response.Response.ResponseStatus.Description)

        except suds.WebFault as e:
            # childAtPath behaviour is changing at version 0.6
            prefix = ''
            if SUDS_VERSION >= "0.6":
                prefix = '/Envelope/Body/Fault'
            return self.get_error_message(e.document.childAtPath(prefix + '/detail/Errors/ErrorDetail/PrimaryErrorCode/Code').getText(),
                                          e.document.childAtPath(prefix + '/detail/Errors/ErrorDetail/PrimaryErrorCode/Description').getText())
        except URLError as e:
            return self.get_error_message('0', 'UPS Server Not Found:\n%s' % e)
