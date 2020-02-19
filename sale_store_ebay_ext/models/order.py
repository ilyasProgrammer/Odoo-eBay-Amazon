# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time
from datetime import datetime, timedelta
import logging
from pytz import timezone

_log = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dropship_cost = fields.Float('temporary field', default=0.0)
    dropship_total_cost = fields.Float('temp')
    paypal_fee = fields.Float('PayPal Fee', default=0.0)
    paypal_transaction = fields.Char('PayPal Transaction')
    ebay_created_time = fields.Datetime('CreatedTime')
    ebay_paid_time = fields.Datetime('PaidTime')
    ebay_shipped_time = fields.Datetime('ShippedTime')

    def cron_activated_method(self):
        ebay_stores = self.env['sale.store'].search([('site', '=', 'ebay'), ('enabled', '=', True)])
        for st in ebay_stores:
            self.update_paypal_transaction_ids(st)
        # self.update_dates_of_amazon_orders()

    @api.multi
    def update_paypal_transaction_ids(self, st):
        orders = self.env['sale.order'].search([('store_id', '=', st.id),
                                                ('date_order', '>', '2018-12-31'),
                                                ('paypal_transaction', '=', ''),
                                                ('web_order_id', '!=', ''),
                                                ('state', 'in', ['done', 'sale'])])
        cnt = 0
        for order in orders:
            cnt += 1
            transaction_data_dict = ''
            try:
                transaction_data = st.ebay_execute('GetOrderTransactions', {'OrderIDArray': [{'OrderID': order.web_order_id}], 'DetailLevel': 'ReturnAll'})
                transaction_data_dict = transaction_data.dict()
                paypal_transaction = dv(transaction_data_dict, ('OrderArray', 'Order', 'ExternalTransaction', 'ExternalTransactionID'), '')
                order.paypal_transaction = paypal_transaction
                _log.info("%s %s", order.id, paypal_transaction)
            except Exception as e:
                _log.error(e)
                _log.error(transaction_data_dict)
                time.sleep(5)
            if cnt % 10 == 0:
                self.env.cr.commit()
            elif cnt % 19 == 0:
                time.sleep(2)

    @api.multi
    def update_dates_of_amazon_orders(self):
        amz_store = self.env['sale.store'].browse(7)
        now = datetime.now()
        orders_saved = 0
        listorders_params = {}
        listorders_params['Action'] = 'ListOrders'
        listorders_params['PaymentMethod.Method.1'] = 'Other'
        listorders_params['PaymentMethod.Method.2'] = 'COD'
        listorders_params['PaymentMethod.Method.3'] = 'CVS'
        listorders_params['MaxResultsPerPage'] = '40'
        listorders_params['CreatedAfter'] = '2019-06-01T00:00:00.000Z'
        response = amz_store.process_amz_request('GET', '/Orders/2013-09-01', now, listorders_params)

        result = response['ListOrdersResponse']['ListOrdersResult']
        if 'Order' in result['Orders']:
            orders = result['Orders']['Order']
            # if there is only one item, what's returned is just a dictionary
            if not isinstance(orders, list):
                orders = [orders]
            saved_qty = self.save_ordersz(now, orders)  # -> amz_merchant_fulfillment
            orders_saved = saved_qty or 0
        if 'NextToken' in result:
            res = self.amz_getorder_by_next_tokenz(now, result['NextToken']['value'])
            orders_saved += res or 0

    @api.multi
    def amz_getorder_by_next_tokenz(self, now, token, saved=0):
        amz_store = self.env['sale.store'].browse(7)
        orders_saved = saved if saved else 0
        params = {}
        params['Action'] = 'ListOrdersByNextToken'
        params['NextToken'] = token
        response = amz_store.process_amz_request('GET', '/Orders/2013-09-01', now, params)
        result = response['ListOrdersByNextTokenResponse']['ListOrdersByNextTokenResult']
        if 'Order' in result['Orders']:
            orders = result['Orders']['Order']
            # if there is only one item, what's returned is just a dictionary
            if not isinstance(orders, list):
                orders = [orders]
            res = self.save_ordersz(now, orders)
            orders_saved += res or 0

        if 'NextToken' in result:
            self.env.cr.commit()
            time.sleep(30)
            return self.amz_getorder_by_next_tokenz(now, result['NextToken']['value'], orders_saved)
        return orders_saved

    @api.multi
    def save_ordersz(self, now, orders):
        for order in orders:
            data = {'date_order': convert_amz_date(dv(order, ('PurchaseDate', 'value'))),
                    'amz_earliest_delivery_date': convert_amz_date(dv(order, ('EarliestDeliveryDate', 'value'))),
                    'amz_earliest_ship_date': convert_amz_date(dv(order, ('EarliestShipDate', 'value'))),
                    'amz_last_update_date': convert_amz_date(dv(order, ('LastUpdateDate', 'value'))),
                    'amz_latest_delivery_date': convert_amz_date(dv(order, ('LatestDeliveryDate', 'value'))),
                    'amz_purchase_date': convert_amz_date(dv(order, ('PurchaseDate', 'value')))}
            opsyst_amz_order = self.env['sale.order'].search([('web_order_id', '=', order['AmazonOrderId']['value'])], limit=1)
            if opsyst_amz_order:
                opsyst_amz_order.write(data)
                _log.info(opsyst_amz_order)
                _log.info(data)

    @api.multi
    def update_dates_of_ebay_orders(self, st, page=1):
        mod_time_from = '2019-01-01T00:00:00.000Z'
        mod_time_to = '2019-06-01T23:59:59.999Z'
        orders = st.ebay_execute('GetOrders', {'CreateTimeFrom': mod_time_from,
                                               'CreateTimeTo': mod_time_to,
                                               'OrderStatus': 'Completed',
                                               'Pagination': {'EntriesPerPage': 10, 'PageNumber': page}}).dict()
        if orders['OrderArray']:
            for order in orders['OrderArray']['Order']:
                data = {
                    'date_order': convert_ebay_date(order.get('CreatedTime')),
                    'ebay_created_time': convert_ebay_date(order.get('CreatedTime')),
                    'ebay_paid_time': convert_ebay_date(order.get('PaidTime')),
                    'ebay_shipped_time': convert_ebay_date(order.get('ShippedTime'))}
                try:
                    opsyst_ebay_order = self.env['sale.order'].search([('web_order_id', '=', order['OrderID'])], limit=1)
                    if opsyst_ebay_order:
                        opsyst_ebay_order.write(data)
                        _log.info(opsyst_ebay_order)
                        _log.info(data)
                except:
                    pass
        if orders['HasMoreOrders'] == 'true':
            self.env.cr.commit()
            return self.update_dates_of_ebay_orders(st, page + 1)


def dv(data, path, ret_type=None):
    # Deep value of nested dict. Return ret_type if cant find it
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:])
        else:
            return ret_type
    return data


def convert_amz_date(raw_amz_time_str):
    try:
        t = raw_amz_time_str.replace('T', ' ').replace('Z', '')
        # res = (datetime.strptime(t, '%Y-%m-%d %H:%M:%S.%f') - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        return t
    except:
        return False


def convert_ebay_date(raw_ebay_time_str):
    try:
        t = raw_ebay_time_str.replace('T', ' ').replace('Z', '')
        return t
    except:
        return False


