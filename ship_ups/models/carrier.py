# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import urllib
import xml.etree.ElementTree as ET

from odoo import models, fields, api


class CarrierUPS(models.Model):
    _inherit = 'ship.carrier'

    ups_access_license_number = fields.Char(string='UPS Access License Number', required_if_code='ups', groups="base.group_system")
    ups_user_id = fields.Char(string='UPS User ID', required_if_code='ups', groups="base.group_system")
    ups_password = fields.Char(string='UPS Password', required_if_code='ups', groups="base.group_system")
    ups_shipper_number = fields.Char(string='UPS Shipper Number', required_if_code='ups', groups="base.group_system")
    ups_environment = fields.Selection([('test', 'Test'), ('production', 'Production')], string='UPS Environment', default='test', groups="base.group_system")

    def ups_get_status_of_tracking_number(self, shipment):
        if shipment:
            if self.carrier_environment == 'production':
                url = 'https://onlinetools.ups.com/ups.app/xml/Track'
            else:
                url = 'https://wwwcie.ups.com/ups.app/xml/Track'

            access_request = '''
            <AccessRequest>
                <AccessLicenseNumber>%s</AccessLicenseNumber>
                <Password>%s</Password>
                <UserId>%s</UserId>
            </AccessRequest>
            ''' % (self.ups_access_license_number, self.ups_password, self.ups_user_id)

            tracking_request = '''
            <TrackRequest>
                <Request>
                    <RequestAction>Track</RequestAction>
                    <RequestOption>activity</RequestOption>
                    <TransactionReference>
                        <CustomerContext>Get tracking status</CustomerContext>
                        <XpciVersion>1.0</XpciVersion>
                    </TransactionReference>
                </Request>
                <TrackingNumber>%s</TrackingNumber>
            </TrackRequest>
            ''' % shipment.tracking_number  # test_tracking_number = '1Z12345E0291980793'

            xml = u'''
            <?xml version="1.0"?>
            {access_request_xml}

            <?xml version="1.0"?>
            {api_xml}
            '''.format(
                request_type=url,
                access_request_xml=access_request,
                api_xml=tracking_request,
            )

            res = ET.fromstring(urllib.urlopen(url, xml.encode('ascii', 'xmlcharrefreplace')).read())
            activity = res.find('Shipment').find('Package').findall('Activity')[0]
            status_code = activity.find('Status').find('StatusType').find('Code').text

            if status_code == 'M':
                shipment.shipping_state = 'waiting_shipment'
                return activity.find('Status').find('StatusType').find('Description').text

            if status_code == 'I':
                shipment.shipping_state = 'in_transit'
                return activity.find('Status').find('StatusType').find('Description').text

            if status_code == 'D':
                shipment.shipping_state = 'done'
                return activity.find('Status').find('StatusType').find('Description').text

            if res.find('Response').find('Error') or status_code == 'X':
                shipment.shipping_state = 'failed'
                return "No tracking information available"
        return False
