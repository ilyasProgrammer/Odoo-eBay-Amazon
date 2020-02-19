# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from datetime import timedelta


class SaleStore(models.Model):
    _inherit = 'sale.store'

    @api.model
    def cron_fba_getorder(self, minutes_ago):
        self.env['slack.calls'].notify_slack('[STORE] Get Amazon FBA Orders Scheduler', 'Started at %s' % datetime.utcnow())
        opsyst_info_channel = self.env['ir.config_parameter'].get_param('slack_odoo_opsyst_info_channel_id')
        now = datetime.now()
        orders_qty = []
        total = 0
        for cred in self.search([('site', '=', 'amz'), ('enabled', '=', True)]):
            res = cred.amz_get_shipped_fba_orders(now, minutes_ago)
            if type(res) == int:
                orders_qty.append({'site': cred.site, 'qty': res})
                total += res
        if len(orders_qty):
            attachment = {
                'color': '#7CD197',
                'fallback': 'Pulled FBA orders report',
                'title': 'Total FBA orders received: %s' % total,
            }
            text = ''
            for r in orders_qty:
                if r['site'] == 'amz':
                    text += 'Received FBA Amazon orders: %s' % r['qty']
            attachment['text'] = text
            self.env['slack.calls'].notify_slack('[STORE] Get Amazon FBA Orders Scheduler', 'Pulled FBA orders report', opsyst_info_channel, attachment)
        self.env['slack.calls'].notify_slack('[STORE] Get Amazon FBA Orders Scheduler', 'Ended at %s' % datetime.utcnow())

    @api.multi
    def amz_get_shipped_fba_orders(self, now, minutes_ago):
        self.ensure_one()
        orders_saved = 0
        listorders_params = {}
        listorders_params['Action'] = 'ListOrders'
        listorders_params['FulfillmentChannel.Channel.1'] = 'AFN'
        listorders_params['PaymentMethod.Method.1'] = 'Other'
        listorders_params['PaymentMethod.Method.2'] = 'COD'
        listorders_params['PaymentMethod.Method.3'] = 'CVS'
        listorders_params['OrderStatus.Status.1'] = 'Shipped'
        listorders_params['MaxResultsPerPage'] = '40'
        listorders_params['LastUpdatedAfter'] = (now - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%d' + 'T' + '%H:%M:%S' + '.000Z')
        # listorders_params['LastUpdatedAfter'] = '2017-09-01' + 'T' + '00:00:00' + '.000Z'
        response = self.process_amz_request('GET', '/Orders/2013-09-01', now, listorders_params)
        result = response['ListOrdersResponse']['ListOrdersResult']
        if 'Order' in result['Orders']:
            orders = result['Orders']['Order']
            # if there is only one item, what's returned is just a dictionary
            if not isinstance(orders, list):
                orders = [orders]
                orders_saved = len(orders)
            self.save_orders(now, orders)
        if 'NextToken' in result:
            orders_saved += self.amz_getorder_by_next_token(now, result['NextToken']['value'])
        return orders_saved
