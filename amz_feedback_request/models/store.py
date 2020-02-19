# -*- coding: utf-8 -*-

import csv
import logging
import time
import pprint
import json

from datetime import datetime, timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleStore(models.Model):
    _inherit = 'sale.store'

    @api.model
    def cron_amz_request_feedback(self):
        amz_store_ids = self.search([('site', '=', 'amz')])
        for amz_store_id in amz_store_ids:
            days_9_ago = (datetime.now() + timedelta(days=-9)).strftime('%Y-%m-%d %H:%M:%S')
            so_ids = self.env['sale.order'].search([('ship_date', '<', days_9_ago), ('ship_date', '!=', False), ('message_state', '!=', 'feedback'), ('create_date', '>=', '2017-10-04 00:00:00')])
            for so_id in so_ids:
                so_id.amz_send_feedback_request_mail()
                self.env.cr.commit()

    @api.multi
    def amz_request_report(self, now, report_type, requestreport_params):
        requestreport_params['Action'] = 'RequestReport'
        requestreport_params['ReportType'] = report_type
        response = self.process_amz_request('GET', '/Reports/2009-01-01', now, requestreport_params)
        _logger.info('Request report response: %s' %json.dumps(response))
        report_request_id = response['RequestReportResponse']['RequestReportResult']['ReportRequestInfo']['ReportRequestId']['value']
        return report_request_id

    @api.multi
    def amz_get_status_of_report_request(self, now, report_request_id):
        reportrequest_list_params = {}
        reportrequest_list_params['Action'] = 'GetReportRequestList'
        reportrequest_list_params['ReportRequestIdList.Id.1'] = report_request_id
        while True:
            response = self.process_amz_request('GET', '/Reports/2009-01-01', now, reportrequest_list_params)
            status = response['GetReportRequestListResponse']['GetReportRequestListResult']['ReportRequestInfo']['ReportProcessingStatus']['value']
            if status == '_DONE_':
                _logger.info('Report request status response: %s' % json.dumps(response))
                generated_report_id = response['GetReportRequestListResponse']['GetReportRequestListResult']['ReportRequestInfo']['GeneratedReportId']['value']
                return generated_report_id
            elif status == '_CANCELLED_':
                _logger.warning('Report request was cancelled: %s' % pprint.pformat(json.dumps(response)))
                return False
            elif status == '_DONE_NO_DATA_':
                _logger.info('Report has no data: %s' % json.dumps(response))
                return False
            _logger.info('Current Status is %s. Trying again...' % status)
            time.sleep(30)

    def amz_get_report(self, now, report_request_id, file_path):
        getreport_params = {}
        getreport_params['Action'] = 'GetReport'
        getreport_params['ReportId'] = report_request_id
        response = self.process_amz_request('POST', '/Reports/2009-01-01', now, getreport_params)
        if file_path:
            inv_report_file = open(file_path, 'wb')
            inv_report_file.write(response)
            inv_report_file.close()
            _logger.info('Report downloaded!')
        else:
            return response

    @api.model
    def cron_mark_sales_orders_as_shipped(self):
        now = datetime.now()
        amz_store_ids = self.search([('site', '=', 'amz')])
        for amz_store_id in amz_store_ids:
            report_type = '_GET_FLAT_FILE_ACTIONABLE_ORDER_DATA_'
            file_path = '/var/tmp/amazon/unshipped_orders' + now.strftime('%Y-%m-%d') + '.tsv'
            report_request_id = amz_store_id.amz_request_report(now, report_type, {})
            generated_report_id = amz_store_id.amz_get_status_of_report_request(now, report_request_id)
            if generated_report_id:
                amz_store_id.amz_get_report(now, generated_report_id, file_path)
                counter = 1
                unshipped_orders = []
                with open(file_path) as tsv:
                    for line in csv.reader(tsv, dialect="excel-tab"):
                        if counter == 1:
                            counter += 1
                            continue
                        unshipped_orders.append(line[0])
                    counter += 1
            shipped_orders = amz_store_id.env['sale.order'].search([('web_order_id', 'not in', unshipped_orders), ('store_id', '=', amz_store_id.id), ('create_date', '>=', '2017-10-04 00:00:00'), ('ship_date', '=', False)])
            shipped_orders.write({'ship_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    @api.multi
    def save_orders(self, now, orders):
        self.ensure_one()

        PartnerObj = self.env['res.partner']
        SaleOrderObj = self.env['sale.order']
        SaleOrderLineObj = self.env['sale.order.line']
        ProductTemplateObj = self.env['product.template']
        ProductProductObj = self.env['product.product']
        ProductListingObj = self.env['product.listing']

        for order in orders:
            _logger.info('Processing %s' %order['AmazonOrderId']['value'])
            if self.code == 'sinister' and order['PurchaseDate']['value'] < "2017-03-17T07:24:08Z":
                continue

            amz_order_id = order['AmazonOrderId']['value']
            sale_order_id = SaleOrderObj.search([('web_order_id', '=', amz_order_id)])

            if sale_order_id:
                continue

            #CREATE PARTNER
            state = order['ShippingAddress']['StateOrRegion']['value'].replace('.', '')
            state_id = False
            country_id = self.env['res.country'].search([('code', '=', 'US')], limit=1)
            if len(state) == 2:
                state_id = self.env['res.country.state'].search([('code', '=', state.upper()), ('country_id', '=', country_id.id)], limit=1)
            else:
                state_id = self.env['res.country.state'].search([('name', '=', state.title()), ('country_id', '=', country_id.id)], limit=1)
            partner_values = {
                'name' : order['ShippingAddress']['Name']['value'],
                'phone': order['ShippingAddress']['Phone']['value'] if 'Phone' in order['ShippingAddress'] else '',
                'street': order['ShippingAddress']['AddressLine1']['value'] if 'AddressLine1' in order['ShippingAddress'] else '',
                'street2': order['ShippingAddress']['AddressLine2']['value'] if 'AddressLine2' in order['ShippingAddress'] else '',
                'city': order['ShippingAddress']['City']['value'],
                'zip': order['ShippingAddress']['PostalCode']['value'].strip(' '),
                'country_id': country_id.id,
                'state_id' : state_id.id,
                'customer': True,
                'store_id': self.id,
                'email': order['BuyerEmail']['value']
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
                'payment_term_id': self.env.ref('account.account_payment_term_immediate').id
            })

            getorder_params = {'Action': 'ListOrderItems', 'AmazonOrderId':amz_order_id}
            order_details = self.process_amz_request('GET', '/Orders/2013-09-01', now, getorder_params)

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

                    SaleOrderLineObj.create({
                        'product_id': product_tmpl_id.product_variant_id.id,
                        'order_id': sale_order_id.id,
                        'price_unit': float(order_item['ItemPrice']['Amount']['value']) / int(order_item['QuantityOrdered']['value']),
                        'product_uom_qty': int(order_item['QuantityOrdered']['value']),
                        'title': order_item['Title']['value'],
                        'item_id': order_item['SellerSKU']['value'],
                        'asin': order_item['ASIN']['value']
                    })

            # sale_order_id.amz_send_thank_you_mail()

            # Set shipping dimensions if sale order has single line
            if len(sale_order_id.order_line) == 1:
                product_id = sale_order_id.order_line.product_id
                sale_order_id.write({
                    'length': product_id.length,
                    'width': product_id.width,
                    'height': product_id.height,
                    'weight': product_id.weight
                })
            self.env.cr.commit()
