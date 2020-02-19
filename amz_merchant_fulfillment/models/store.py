# -*- coding: utf-8 -*-

import math
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api
from distutils import util
from pytz import timezone

_logger = logging.getLogger(__name__)


class SaleStore(models.Model):
    _inherit = 'sale.store'

    default_shipping_template_id = fields.Many2one('sale.store.amz.shipping.template', 'Default Template')
    prime_shipping_template_id = fields.Many2one('sale.store.amz.shipping.template', 'Prime Template')

    @api.model
    def cron_amz_update_shipping_template(self):
        store_ids = self.search([('site', '=', 'amz')])
        for store_id in store_ids:
            listing_ids = self.env['product.listing'].search([('store_id', '=', store_id.id), ('title', '!=', False), ('amz_order_type' ,'=', 'fbm')])
            if listing_ids:
                data = []
                for listing_id in listing_ids:
                    shipping_template_name = store_id.default_shipping_template_id.name
                    wh_availability = listing_id.product_tmpl_id.get_wh_availability_for_kits_and_non_kits()
                    print wh_availability
                    quot_qty = 0
                    lines = self.env['sale.order.line'].search([('product_id', '=', listing_id.product_tmpl_id.product_variant_id.id), ('order_id.state', '=', 'draft')])
                    for l in lines:
                        quot_qty += l.product_uom_qty
                    if wh_availability - quot_qty > 0:
                        shipping_template_name = store_id.prime_shipping_template_id.name
                    data.append((listing_id.name, listing_id.title, shipping_template_name))
                store_id.update_shipping_template(data)

    @api.multi
    def update_shipping_template(self, data):
        '''
            data should be a list of tuple (sku, title, shipping_template)
        '''
        now = datetime.now()
        FulfillmentDate = now.strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
        MerchantIdentifier = '%s-'% str(self.id) + now.strftime('Amz-%Y-%m-%d-%H-%M-%S')

        counter = 1
        xml_body = ''
        for sku in data:
            title = sku[1].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
            t_norm = ''.join([i if ord(i) < 128 else '' for i in title])
            xml_body += "<Message>"
            xml_body += "<MessageID>{MessageID}</MessageID>".format(MessageID=str(counter))
            xml_body += "<OperationType>PartialUpdate</OperationType>"
            xml_body += "<Product>"
            xml_body += "<SKU>{SKU}</SKU>".format(SKU=sku[0])
            xml_body += "<DescriptionData>"
            xml_body += "<Title>{Title}</Title>".format(Title=t_norm)
            xml_body += "<MerchantShippingGroupName>{Template}</MerchantShippingGroupName>".format(Template=sku[2])
            xml_body += "</DescriptionData>"
            xml_body += "</Product>"
            xml_body += "</Message>"
            counter += 1

        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<AmazonEnvelope xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='amzn-envelope.xsd'>"
        xml += "<Header>"
        xml += "<DocumentVersion>1.0</DocumentVersion>"
        xml += "<MerchantIdentifier>{MerchantIdentifier}</MerchantIdentifier>".format(MerchantIdentifier=MerchantIdentifier)
        xml += "</Header>"
        xml += "<MessageType>Product</MessageType>"
        xml += "<PurgeAndReplace>false</PurgeAndReplace>"
        xml += xml_body
        xml += "</AmazonEnvelope>"

        md5value = self.get_md5(xml)

        params = {
            'ContentMD5Value': md5value,
            'Action': 'SubmitFeed',
            'FeedType': '_POST_PRODUCT_DATA_',
            'PurgeAndReplace': 'false'
        }
        _logger.info('Uploading shipping template: %s' %xml)
        response = self.process_amz_request('POST', '/Feeds/2009-01-01', now, params, xml)

    @api.multi
    def amz_get_order_by_buyer_email_address(self, buyer_email_address, now, send_feedback_request=True,
                                             created_before=7):
        listorders_params = {}
        listorders_params['Action'] = 'ListOrders'
        listorders_params['MaxResultsPerPage'] = '40'
        listorders_params['CreatedAfter'] = (now - timedelta(days=created_before)).strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'.000Z')
        listorders_params['BuyerEmail'] = buyer_email_address
        response = self.process_amz_request('GET', '/Orders/2013-09-01', now, listorders_params)
        result = response['ListOrdersResponse']['ListOrdersResult']
        if 'Order' in result['Orders']:
            orders = result['Orders']['Order']
            if not orders:
                return False
            # if there is only one item, what's returned is just a dictionary
            if not isinstance(orders, list):
                orders = [orders]
            self.save_orders(now, orders, send_feedback_request=send_feedback_request)
            # TODO: Ideally, we need to return whether or not a new order is created or not
            return True

    @api.multi
    def save_orders(self, now, orders, send_feedback_request=True):
        self.ensure_one()
        PartnerObj = self.env['res.partner']
        SaleOrderObj = self.env['sale.order']
        SaleOrderLineObj = self.env['sale.order.line']
        ProductTemplateObj = self.env['product.template']
        ProductListingObj = self.env['product.listing']
        created_orders = 0
        for order in orders:
            _logger.info('\n\nProcessing %s' % order['AmazonOrderId']['value'])
            if self.code == 'sinister' and order['PurchaseDate']['value'] < "2017-03-17T07:24:08Z":
                continue
            if order['OrderStatus']['value'] in ('Pending', 'Canceled'):
                continue
            if order['FulfillmentChannel']['value'] == 'AFN':
                amz_order_type = 'fba'
            elif order['FulfillmentChannel']['value'] == 'MFN' and order['IsPrime']['value'] == 'true':
                amz_order_type = 'fbm'
            else:
                amz_order_type = 'normal'
            amz_order_id = order['AmazonOrderId']['value']
            sale_order_id = SaleOrderObj.search([('web_order_id', '=', amz_order_id), ('state', '!=', 'cancel')])

            if sale_order_id:
                continue
            # CREATE PARTNER
            state = order['ShippingAddress']['StateOrRegion']['value'].replace('.', '')
            state_id = False
            country_id = self.env['res.country'].search([('code', '=', 'US')], limit=1)
            if len(state) == 2:
                state_id = self.env['res.country.state'].search([('code', '=', state.upper()), ('country_id', '=', country_id.id)], limit=1)
            else:
                state_id = self.env['res.country.state'].search([('name', '=', state.title()), ('country_id', '=', country_id.id)], limit=1)
            partner_values = {
                'name': order['ShippingAddress']['Name']['value'],
                'phone': order['ShippingAddress']['Phone']['value'] if 'Phone' in order['ShippingAddress'] else '',
                'street': order['ShippingAddress']['AddressLine1']['value'] if 'AddressLine1' in order['ShippingAddress'] else '',
                'street2': order['ShippingAddress']['AddressLine2']['value'] if 'AddressLine2' in order['ShippingAddress'] else '',
                'city': order['ShippingAddress']['City']['value'],
                'zip': order['ShippingAddress']['PostalCode']['value'].strip(' '),
                'country_id': country_id.id,
                'state_id': state_id.id,
                'customer': True,
                'store_id': self.id,
                'email': order['BuyerEmail']['value'] if 'BuyerEmail' in order else ''
            }
            if not state_id:
                partner_values['amz_state'] = state
            partner_id = PartnerObj.search([('name', '=', partner_values['name'])])
            if not (len(partner_id) == 1 and partner_id.name == partner_values['name'] and partner_id.phone == partner_values['phone'] and partner_id.street == partner_values['street'] and partner_id.city == partner_values['city'] and partner_id.zip == partner_values['zip']):
                partner_id = PartnerObj.create(partner_values)

            sale_order_id = SaleOrderObj.create({
                'partner_id': partner_id.id,
                'web_order_id': amz_order_id,
                'store_id': self.id,
                'amz_order_type': amz_order_type,
                'payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
                'latest_ship_date': order['LatestShipDate']['value'].replace('T', ' ').replace('Z', ''),
                'date_order': convert_amz_date(dv(order, ('PurchaseDate', 'value'))),
                'amz_earliest_delivery_date': convert_amz_date(dv(order, ('EarliestDeliveryDate', 'value'))),
                'amz_earliest_ship_date': convert_amz_date(dv(order, ('EarliestShipDate', 'value'))),
                'amz_last_update_date': convert_amz_date(dv(order, ('LastUpdateDate', 'value'))),
                'amz_latest_delivery_date': convert_amz_date(dv(order, ('LatestDeliveryDate', 'value'))),
                'amz_purchase_date': convert_amz_date(dv(order, ('PurchaseDate', 'value'))),
                'is_premium_order': util.strtobool(order['IsPremiumOrder']['value'])
            })
            _logger.info('Amazon order created: %s', amz_order_id)
            created_orders += 1

            getorder_params = {'Action': 'ListOrderItems', 'AmazonOrderId': amz_order_id}
            order_details = self.process_amz_request('GET', '/Orders/2013-09-01', now, getorder_params)
            delivery_price = 0
            if 'OrderItem' in order_details['ListOrderItemsResponse']['ListOrderItemsResult']['OrderItems']:
                order_items = order_details['ListOrderItemsResponse']['ListOrderItemsResult']['OrderItems']['OrderItem']
                if not isinstance(order_items, list):
                    order_items = [order_items]
                for order_item in order_items:
                    if int(order_item['QuantityOrdered']['value']) == 0:
                        continue
                    product_tmpl_id = ProductTemplateObj
                    sku = ''
                    if 'SellerSKU' in order_item and order_item['SellerSKU']['value']:
                        sku = order_item['SellerSKU']['value']
                        product_listing = ProductListingObj.search([('name', '=', sku)])
                        if product_listing:
                            product_tmpl_id = product_listing.product_tmpl_id
                            if product_tmpl_id.mfg_code != 'ASE':
                                ase_alt = product_tmpl_id.alternate_ids.filtered(lambda p: p.mfg_code == 'ASE')
                                if ase_alt:
                                    product_tmpl_id = ase_alt

                    # If product is not found in odoo, look for it in autoplus and save it to odoo
                    if not product_tmpl_id and sku:
                        product_row = ProductTemplateObj.get_product_from_autoplus_by_part_number(sku)
                        if product_row:
                            product_values = ProductTemplateObj.prepare_product_row_from_autoplus(product_row)
                            product_tmpl_id = ProductTemplateObj.create(product_values)

                    # If product is not found in odoo and autoplus, create the product
                    if not product_tmpl_id:
                        product_values = {
                            'name': '[NOT FOUND] ' + order_item['Title']['value'],
                            'part_number': sku,
                            'type': 'product',
                            'list_price': float(order_item['ItemPrice']['Amount']['value']) / float(order_item['ItemPrice']['Amount']['value'])
                        }
                        product_tmpl_id = ProductTemplateObj.create(product_values)
                    # Try to find tax by state and calculated percent
                    tax = self.env['account.tax']
                    if order_item.get('ItemTax') and partner_id.state_id.code not in ['WA', 'PA']:   # Amazon handling this taxes. We dont have to collect it
                        tax_val = order_item['ItemTax']['Amount']['value']
                        if tax_val:
                            tax_percent = 100 * float(order_item['ItemTax']['Amount']['value'])/float(order_item['ItemPrice']['Amount']['value'])
                            tax_percent = truncate(tax_percent, 2)  # Because rounding might cause inaccuracy
                            tax = self.env['account.tax'].search([('state_id', '=', partner_id.state_id.id)])  # One state one tax
                            if len(tax) == 1:
                                if abs(tax.amount - tax_percent) >= 0.04:  # Difference to high. Skip tax.
                                    if tax_percent > 0:
                                        _logger.warning('Tax difference to high %s %s %s %s', sale_order_id.id, tax.name, tax.amount, tax_percent)
                                    tax = False
                    if 'ShippingPrice' in order_item and 'Amount' in order_item['ShippingPrice']:
                        delivery_price += float(order_item['ShippingPrice']['Amount']['value'])
                    SaleOrderLineObj.create({
                        'product_id': product_tmpl_id.product_variant_id.id,
                        'order_id': sale_order_id.id,
                        'price_unit': float(order_item['ItemPrice']['Amount']['value']) / int(order_item['QuantityOrdered']['value']),
                        'product_uom_qty': int(order_item['QuantityOrdered']['value']),
                        'title': order_item['Title']['value'],
                        'item_id': order_item['SellerSKU']['value'],
                        'asin': order_item['ASIN']['value'],
                        'web_orderline_id': order_item['OrderItemId']['value'],
                        'tax_id':  [(6, 0, [tax.id])] if tax else False
                    })
            if send_feedback_request:
                sale_order_id.amz_send_thank_you_mail()
            else:
                sale_order_id.write({'message_state': 'feedback'})

            # Set shipping dimensions if sale order has single line
            if len(sale_order_id.order_line) == 1:
                product_id = sale_order_id.order_line.product_id
                sale_order_id.write({
                    'length': product_id.length,
                    'width': product_id.width,
                    'height': product_id.height,
                    'weight': product_id.weight
                })

            if sale_order_id.stop_on_rfq(sale_order_id):  # sale_dropship
                continue
            if sale_order_id.amz_order_type == 'fbm':
                sale_order_id.delivery_price = delivery_price
                sale_order_id.button_set_dimension_from_first_order_line()
                sale_order_id.button_split_kits()
                sale_order_id.button_set_routes()

                if not sale_order_id.has_exception:
                    for line in sale_order_id.order_line:
                        if line.route_id.id == sale_order_id.warehouse_id.delivery_route_id.id:
                            if not sale_order_id.has_zero_dimension:
                                sale_order_id.button_get_cheapest_service()
                    sale_order_id.action_confirm()
            self.env.cr.commit()
        return created_orders


class StoreShippingTemplate(models.Model):
    _name = 'sale.store.amz.shipping.template'
    _description = 'Amazon Shipping Templates'
    _order = 'store_id, name'

    name = fields.Char('Name', required=True, help="This should exactly match template name in Amazon")
    store_id = fields.Many2one('sale.store', 'Store', required=True, domain="[('site', '=', 'amz')]")


def truncate(f, n):
    return math.floor(f * 10 ** n) / 10 ** n


def dv(data, path, ret_type=None):
    # Deep value of nested dict. Return ret_type if cant find it
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:])
        else:
            return ret_type
    return data


def dt_to_utc(sdt):
    try:
        res = timezone('US/Eastern').localize(datetime.strptime(sdt, '%Y-%m-%d %H:%M:%S')).astimezone(timezone('utc')).strftime('%Y-%m-%d %H:%M:%S')
        return res
    except:
        return False


def convert_amz_date(raw_amz_time_str):
    try:
        t = raw_amz_time_str.replace('T', ' ').replace('Z', '')
        # if len(raw_amz_time_str) < 21:
        #     date_format = '%Y-%m-%d %H:%M:%S'
        # else:
        date_format = '%Y-%m-%d %H:%M:%S.%f'
        # res = (datetime.strptime(t, date_format) - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        # res = (datetime.strptime(t, date_format) - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        return t
    except:
        return False
