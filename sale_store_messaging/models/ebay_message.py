# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import urllib2
import base64
from BeautifulSoup import BeautifulSoup as BS
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

class StoreMessage(models.Model):
    _name = 'sale.store.ebay.message'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Subject', required=True)
    store_id = fields.Many2one('sale.store', 'Store')
    message_type = fields.Selection([('AskSellerQuestion', 'AskSellerQuestion'),
        ('ResponseToASQQuestion', 'ResponseToASQQuestion'),
        ('ContactTransactionPartner', 'ContactTransactionPartner'),
        ('ContactEbayMember', 'ContactEbayMember'),
        ('Others', 'Others')], 'Message Type')
    message_id = fields.Char('Message ID')
    date_received = fields.Datetime('Date Received')
    item_id = fields.Char('Item ID')
    sender = fields.Char('Sender')
    folder = fields.Selection([('inbox', 'Inbox')], 'Folder')
    content = fields.Text('Content')
    response_enabled = fields.Boolean('Response Enabled')
    image_1 = fields.Binary('Image', readonly=True)
    image_2 = fields.Binary('Image', readonly=True)
    image_3 = fields.Binary('Image', readonly=True)
    image_4 = fields.Binary('Image', readonly=True)
    image_5 = fields.Binary('Image', readonly=True)
    image_1_src = fields.Char('Image URL', readonly=True)
    image_2_src = fields.Char('Image URL',readonly=True)
    image_3_src = fields.Char('Image URL', readonly=True)
    image_4_src = fields.Char('Image URL', readonly=True)
    image_5_src = fields.Char('Image URL', readonly=True)
    response_content = fields.Text('Response')
    response_image_1 = fields.Binary('Image')
    response_image_2 = fields.Binary('Image')
    response_image_3 = fields.Binary('Image')
    response_image_4 = fields.Binary('Image')
    response_image_5 = fields.Binary('Image')
    response_image_1_src = fields.Char('Image URL', readonly=True)
    response_image_2_src = fields.Char('Image URL', readonly=True)
    response_image_3_src = fields.Char('Image URL', readonly=True)
    response_image_4_src = fields.Char('Image URL', readonly=True)
    response_image_5_src = fields.Char('Image URL', readonly=True)
    display_to_public = fields.Boolean('Display to Public?')
    email_copy = fields.Boolean('Send Copy to Email?')
    state = fields.Selection([('received', 'Received'), ('replied', 'Replied')], 'Status', default='received')

    @api.model
    def cron_ebay_get_my_messages(self, minutes_ago):
        store_ids = self.env['sale.store'].search([('ebay_get_messages_enabled', '=', True)])
        now = datetime.utcnow()
        for store_id in store_ids:
            StartTime = (now - timedelta(hours=24)).strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
            EndTime = now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
            message_headers_response = store_id.ebay_execute('GetMyMessages', {'StartTime': StartTime, 'EndTime': EndTime, 'DetailLevel': 'ReturnHeaders'})
            message_headers_response_dict = message_headers_response.dict()

            if not message_headers_response_dict['Messages']:
                continue

            message_ids = message_headers_response_dict['Messages']['Message']
            if isinstance(message_ids, dict):
                message_ids = [message_ids]
            for message_id in message_ids:
                existing = self.search([('message_id', '=', message_id['MessageID'])])
                if existing:
                    continue

                message_response = store_id.ebay_execute('GetMyMessages', {'MessageIDs': [{'MessageID': message_id['MessageID']}], 'DetailLevel': 'ReturnMessages'})

                message_response_dict = message_response.dict()

                message = message_response_dict['Messages']['Message']

                message_type = message['MessageType'] if 'MessageType' in message else 'Others'
                response_enabled = True if message['ResponseDetails']['ResponseEnabled'] == 'true' else False
                state = 'replied' if message['Replied'] == 'true' else 'received'

                values = {
                    'name': message['Subject'],
                    'message_id': message_id['ExternalMessageID'] if 'ExternalMessageID' in message_id else message_id['MessageID'],
                    'sender': message['Sender'],
                    'date_received': (datetime.strptime(message['ReceiveDate'], '%Y-%m-%dT%H:%M:%S.000Z')).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'item_id': message['ItemID'] if 'ItemID' in message else '',
                    'message_type': message_type,
                    'store_id': store_id.id,
                    'response_enabled': response_enabled,
                    'state': state
                }
                content = BS(message['Text'])
                if message_type in ['AskSellerQuestion', 'ResponseToASQQuestion','ContactTransactionPartner']:
                    user_input = content.find("div", {"id": "UserInputtedText"})
                    if user_input:
                        values['content'] = user_input.text
                    for i in range(0,5):
                        image_node = content.find("img", {'id': 'previewimage%s' %i})
                        if image_node:
                            key_src = 'image_%s_src' %(i + 1)
                            key_image = 'image_%s' %(i + 1)
                            values[key_src] = image_node['src']
                            values[key_image] = base64.encodestring(urllib2.urlopen(image_node['src']).read())
                        else:
                            break
                elif message_type == 'Others':
                    user_input = content.find("div", {"id": "para-link"})
                    if user_input:
                        values['content'] = user_input.text
                new_message = self.create(values)
                new_message.message_post(body=message['Text'])
                print message_type

                # if message_type == 'Others':
                file = open('/Users/ajporlante/auto/ebay/messages/%s.txt' %values['message_id'], 'wb')
                file.write('%s' %json.dumps(message))

                self.env.cr.commit()

    @api.multi
    def upload_images(self):
        self.ensure_one()
        images = {
            'response_image_1': self.response_image_1,
            'response_image_2': self.response_image_2,
            'response_image_3': self.response_image_3,
            'response_image_4': self.response_image_4,
            'response_image_5': self.response_image_5
        }
        images_src = {}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for i in range(0,5):
            key_image = 'response_image_%s' %(i+1)
            key_src = 'response_image_%s_src' %(i+1)
            if images[key_image]:
                # upload_image_response = self.store_id.ebay_execute('UploadSiteHostedPictures', {
                #     'ExternalPictureURL': 'http://shushi168.com/data/out/193/37281782-random-image.png',
                #     'PictureName': self.message_id + '_' + key
                # })

                # upload_image_response = self.store_id.ebay_execute('UploadSiteHostedPictures', {
                #     'ExternalPictureURL': '%s/web/image?model=sale.store.message&id=%s&field=%s' %(base_url, self.id, key),
                #     'PictureName': self.message_id + '_' + key
                # })

                upload_image_response_dict = json.loads("""
                    {"Errors": {"SeverityCode": "Warning", "ErrorClassification": "RequestError", "ErrorCode": "21916790", "LongMessage": "To reduce possible issues with picture display quality, eBay recommends that pictures you upload are 1000 pixels or larger on the longest side.", "ErrorParameters": {"_ParamID": "0", "Value": "1000"}, "ShortMessage": "Dimensions of the picture you uploaded are smaller than recommended."}, "Ack": "Warning", "Timestamp": "2016-12-27T04:55:47.806Z", "PictureSystemVersion": "2", "Version": "989", "SiteHostedPictureDetails": {"PictureSetMember": [{"MemberURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_0.JPG", "PictureHeight": "96", "PictureWidth": "88"}, {"MemberURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_1.JPG", "PictureHeight": "297", "PictureWidth": "273"}, {"MemberURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_2.JPG", "PictureHeight": "200", "PictureWidth": "183"}, {"MemberURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_14.JPG", "PictureHeight": "64", "PictureWidth": "58"}, {"MemberURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_35.JPG", "PictureHeight": "297", "PictureWidth": "273"}, {"MemberURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_39.JPG", "PictureHeight": "32", "PictureWidth": "32"}], "ExternalPictureURL": "http://shushi168.com/data/out/193/37281782-random-image.png", "PictureSet": "Standard", "BaseURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_", "PictureFormat": "JPG", "UseByDate": "2017-01-26T04:55:47.634Z", "PictureName": "1435231974011_response_image_1", "FullURL": "http://i.ebayimg.com/00/s/Mjk3WDI3Mw==/z/VGUAAOSwa~BYYfRT/$_1.JPG?set_id=8800004005"}, "Build": "E989_CORE_MSA_18148975_R1"}
                """)
                # upload_image_response_dict = upload_image_response.dict()
                images_src[key_src] = upload_image_response_dict['SiteHostedPictureDetails']['FullURL']
                break
        self.write(images_src)

    @api.multi
    def action_reply(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        # try:
        #     template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        # except ValueError:
        #     template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.store.ebay.message',
            'default_res_id': self.ids[0],
            'default_composition_mode': 'comment',
            'mark_ebay_message_as_replied': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
        # self.ensure_one()
        # # self.upload_images()
        # message_dict =  {
        #     'ItemID': int(self.item_id),
        #     'MemberMessage': {
        #         'Body': self.response_content,
        #         'DisplayToPublic': self.display_to_public,
        #         'EmailCopyToSender': self.email_copy,
        #         'ParentMessageID': int(self.message_id),
        #     }
        # }
        # MessageMedia = []
        # images_src = {
        #     'response_image_1_src': self.response_image_1_src,
        #     'response_image_2_src': self.response_image_2_src,
        #     'response_image_3_src': self.response_image_3_src,
        #     'response_image_4_src': self.response_image_4_src,
        #     'response_image_5_src': self.response_image_5_src
        # }
        # for i in range(0,5):
        #     key_src = 'response_image_%s_src' %(i + 1)
        #     if images_src[key_src]:
        #         MessageMedia.append({
        #             'MediaURL': images_src[key_src],
        #             'MediaName': 'Image from %s' %self.store_id.name
        #         })
        # if MessageMedia:
        #     message_dict['MemberMessage']['MessageMedia'] = MessageMedia
        # add_message_response = self.store_id.ebay_execute('AddMemberMessageRTQ', message_dict)
        # print json.dumps(add_message_response.dict())
        # self.write({'state': 'replied'})

# {'body': u'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\r\n<html xmlns="http://www.w3.org/1999/xhtml" style="font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 0">\r\n  <head>\r\n    <meta name="viewport" content="width=device-width">\r\n    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\r\n    <title>Live webinar tomorrow | Streamline Team Collaboration \u200bwith...',
# 'from': u'Bitnami <howdy@bitnami.com>',
# 'attachments': [],
# 'cc': u'',
# 'email_from': u'Bitnami <howdy@bitnami.com>',
# 'to': u'ajporlante@gmail.com',
# 'date': '2017-01-24 14:47:38',
# 'author_id': False,
# 'message_type':
# 'email',
# 'message_id': '<20170124144738.6866.44386.850F5948@bitnami.com>',
# 'subject': u'Live webinar tomorrow | Streamline Team Collaboration \u200bwith eXo Platform\u200b and Bitnami'}
