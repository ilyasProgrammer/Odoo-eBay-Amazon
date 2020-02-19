# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import pprint
from random import randint
import hashlib
import base64
import logging

_logger = logging.getLogger(__name__)


class eBayReviseItem(models.TransientModel):
    _inherit = 'sale.store.ebay.revise.item'

    revise_compatibility = fields.Boolean('Revise Compatibility')
    revise_item_specifics = fields.Boolean('Revise Item Specifics')
    revise_title = fields.Boolean('Revise Title')
    item_specific_line_ids = fields.One2many('sale.store.ebay.revise.item.specific.line', 'wizard_id', 'Item Specifics')
    new_title = fields.Char("New Title")
    site = fields.Selection(related="listing_id.site", readonly=True)

    @api.model
    def default_get(self, fields):
        result = super(eBayReviseItem, self).default_get(fields)
        listing_id = self._context.get('active_model') == 'product.listing' and self._context.get('active_ids')[0]
        listing_id = self.env['product.listing'].browse([listing_id])
        store_id = listing_id.store_id
        result['new_title'] = listing_id.title
        result['listing_id'] = listing_id.id
        result['site'] = listing_id.site
        if store_id.site == 'amz':
            return result
        elif store_id.site == 'ebay':
            if listing_id:
                item = listing_id.store_id.ebay_execute('GetItem', {
                    'ItemID': listing_id.name,
                    'IncludeItemSpecifics': True,
                }).dict()
                item_specific_list = item['Item']['ItemSpecifics']['NameValueList']
                item_specific_vals = []
                att_ids_from_listing = []
                for i in item_specific_list:
                    attribute_id = self.env['product.item.specific.attribute'].search([('name', '=', i['Name'])], limit=1)
                    if not attribute_id:
                        attribute_id = self.env['product.item.specific.attribute'].create({'name': i['Name']})
                    value_id = self.env['product.item.specific.value'].search([('name', '=', i['Value']), ('item_specific_attribute_id', '=', attribute_id.id)], limit=1)
                    if not value_id:
                        value_id = self.env['product.item.specific.value'].create({'name': i['Value'], 'item_specific_attribute_id': attribute_id.id})
                    item_specific_vals.append({'value_id': value_id.id, 'item_specific_attribute_id': attribute_id.id})
                    att_ids_from_listing.append(attribute_id.id)
                for line in listing_id.product_tmpl_id.item_specific_line_ids:
                    if line.item_specific_attribute_id.id not in att_ids_from_listing:
                        item_specific_vals.append({'value_id': line.value_id.id, 'item_specific_attribute_id': line.item_specific_attribute_id.id})
                result['item_specific_line_ids'] = [(0, 0, v) for v in item_specific_vals]
            return result

    @api.multi
    def button_revise_item(self):
        self.ensure_one()
        store_id = self.listing_id.store_id
        item_dict = {'ItemID': self.listing_id.name}
        product_tmpl_id = self.listing_id.product_tmpl_id
        if store_id.site == 'ebay':
            if self.revise_compatibility:
                vehicles = []
                vehicles = store_id.get_vehicles(product_tmpl_id.inventory_id)
                if not (vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']):
                    if product_tmpl_id.bom_ids:
                        for line in product_tmpl_id.bom_ids[0].bom_line_ids:
                            vehicles = store_id.get_vehicles(line.product_id.product_tmpl_id.inventory_id)
                            if vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']:
                                break
                if not vehicles or not (vehicles[0]['MakeName'] and vehicles[0]['ModelName'] and vehicles[0]['YearID']):
                    raise UserError('No fitment data found.')
                else:
                    ItemCompatibilityList = {'Compatibility': [], 'ReplaceAll': True}
                    v_counter = 1
                    for c in vehicles:
                        v_counter += 1
                        if v_counter > 2000:
                            break
                        Note = ''
                        row = {'CompatibilityNotes': Note,
                            'NameValueList': [
                                {'Name': 'Make', 'Value': c['MakeName'].replace("&", "&amp;") if c['MakeName'] else '' },
                                {'Name': 'Model', 'Value': c['ModelName'].replace("&", "&amp;") if c['ModelName'] else ''},
                                {'Name': 'Year', 'Value': str(c['YearID'])},
                            ]}
                        if c['Trim']:
                            row['NameValueList'].append(
                                {'Name': 'Trim', 'Value': c['Trim'].replace("&", "&amp;")}
                            )
                        if c['EngineID']:
                            Engine = store_id.compute_engine(c)
                            row['NameValueList'].append(
                                {'Name': 'Engine', 'Value': Engine.replace("&", "&amp;") }
                            )
                        ItemCompatibilityList['Compatibility'].append(row)
                    if ItemCompatibilityList['Compatibility']:
                        item_dict['ItemCompatibilityList'] = ItemCompatibilityList
            if self.revise_item_specifics:
                item_specifics = {'NameValueList': []}
                product_tmpl_id = self.listing_id.product_tmpl_id
                for line in self.item_specific_line_ids:
                    item_specifics['NameValueList'].append({
                        'Name': line.item_specific_attribute_id.name,
                        'Value': line.value_id.name
                    })
                    if not line.item_specific_attribute_id.listing_specific:
                        item_specific_line_id = self.env['product.item.specific.line'].search([('product_tmpl_id', '=', product_tmpl_id.id), ('item_specific_attribute_id', '=', line.item_specific_attribute_id.id)])
                        if item_specific_line_id:
                            item_specific_line_id.write({'value_id': line.value_id.id })
                        else:
                            self.env['product.item.specific.line'].create({
                                'product_tmpl_id': product_tmpl_id.id,
                                'item_specific_attribute_id': line.item_specific_attribute_id.id,
                                'value_id': line.value_id.id
                            })
                item_dict['ItemSpecifics'] = item_specifics
            if self.revise_title and self.new_title:
                item_dict['Title'] = self.new_title
            _logger.info('Revising in eBay: %s', self.listing_id.name)
            store_id.ebay_execute('ReviseItem', {'Item': item_dict}, raise_exception=True)
        elif store_id.site == 'amz':
            _logger.info('Revising in Amazon: %s', self.listing_id.name)
            title = self.new_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
            xml_body = "<Message>"
            xml_body += "<MessageID>{MessageID}</MessageID>".format(MessageID=str(randint(10, 100)))
            xml_body += "<OperationType>PartialUpdate</OperationType>"
            xml_body += "<Product>"
            xml_body += "<SKU>{SKU}</SKU>".format(SKU=self.listing_id.name)
            xml_body += "<DescriptionData>"
            xml_body += "<Title>{Title}</Title>".format(Title=title)
            xml_body += "</DescriptionData>"
            xml_body += "</Product>"
            xml_body += "</Message>"
            MerchantIdentifier = '%s-' % datetime.now().strftime('TitleRevision-%Y-%m-%d-%H-%M-%S')
            xml = "<?xml version='1.0' encoding='utf-8'?>"
            xml += "<AmazonEnvelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='amzn-envelope.xsd'>"
            xml += "<Header>"
            xml += "<DocumentVersion>1.0</DocumentVersion>"
            xml += "<MerchantIdentifier>{MerchantIdentifier}</MerchantIdentifier>".format(MerchantIdentifier=MerchantIdentifier)
            xml += "</Header>"
            xml += "<MessageType>Product</MessageType>"
            xml += "<PurgeAndReplace>false</PurgeAndReplace>\n"
            xml += xml_body
            xml += "</AmazonEnvelope>"
            md5value = self.get_md5(xml)
            params = {
                'ContentMD5Value': md5value,
                'Action': 'SubmitFeed',
                'FeedType': '_POST_PRODUCT_DATA_',
                'PurgeAndReplace': 'false'
            }
            now = datetime.now()
            response = store_id.process_amz_request('POST', '/Feeds/2009-01-01', now, params, xml)
            _logger.info('Revising in Amazon response: %s', pprint.pformat(response))
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def get_md5(self, string):
        base64md5 = base64.b64encode(hashlib.md5(string).digest())
        if base64md5[-1] == '\n':
            base64md5 = self.base64md5[0:-1]
        return base64md5


class eBayReviseItemSpecificLine(models.TransientModel):
    _name = 'sale.store.ebay.revise.item.specific.line'

    wizard_id = fields.Many2one('sale.store.ebay.revise.item', 'Wizard', required=True)
    item_specific_attribute_id = fields.Many2one('product.item.specific.attribute', 'Name')
    value_id = fields.Many2one('product.item.specific.value', 'Value')
