# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import xml.etree.ElementTree as ET
from urllib2 import Request, urlopen, URLError, quote
from odoo.http import request

from odoo import models, fields, api


class CarrierFedex(models.Model):
    _inherit = 'ship.carrier'

    usps_username = fields.Char(string='USPS Username', required_if_code='stamps_com', groups="base.group_system")
    carrier_environment = fields.Selection([('test', 'Test'), ('production', 'Production')], string=' USPS Environment', default='test')

    def stamps_com_get_status_of_tracking_number(self, shipment):
        if shipment:
            if self.carrier_environment == 'production':
                url = 'http://production.shippingapis.com/ShippingAPI.dll?API=TrackV2'
            else:
                url = 'http://testing.shippingapis.com/ShippingAPI.dll?API=TrackV2'

            user_name = shipment.partner_id.name
            user_zip = shipment.partner_id.zip
            tracking_number = shipment.tracking_number
            client_ip = request.httprequest.environ.get('SERVER_NAME')
            request_text = '''
            <TrackFieldRequest USERID="%s"><TrackID ID="%s"></TrackID></TrackFieldRequest>
            ''' % (self.usps_username, shipment.tracking_number)
            
            xml = '&XML=%s' % (quote(request_text))
            full_url = '%s%s' % (url, xml)
            res = ET.fromstring(urlopen(Request(full_url)).read())
            for data in res:
                if data.find('Error') is not None:
                    shipment.shipping_state = 'failed'
                    return data.find('Error')[1].text
                if data.find('Error') == None and (data.find('TrackSummary').find('Event').text).find('Delivered') != -1:
                    shipment.shipping_state = 'done'
                    return data.find('TrackSummary').find('Event').text + ' [' + data.find('TrackSummary').find('EventDate').text + ']'
                if data.find('Error') == None and (data.find('TrackSummary').find('Event').text).find('Acceptance') != -1:
                    shipment.shipping_state = 'waiting_shipment'
                    return data.find('TrackSummary').find('Event').text + ' [' + data.find('TrackSummary').find('EventDate').text + ']'
                else:
                    shipment.shipping_state = 'in_transit'
                    return data.find('TrackSummary').find('Event').text + ' [' + data.find('TrackSummary').find('EventDate').text + ']'
        return False