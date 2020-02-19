# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amz_order_type = fields.Selection([('ebay', 'eBay'),  # pour le eBay
                                       ('normal', 'Normal'),  # pour le Amazon
                                       ('fbm', 'FBM (Prime)'),  # pour le Amazon  Prime
                                       ('fba', 'FBA')  # pour le Amazon
                                       ], string='Order type')
    fba_commission = fields.Float('FBA Commission')
    fba_fulfillment_fee = fields.Float('FBA Fulfillment Fee')
    amz_earliest_delivery_date = fields.Datetime('Earliest Delivery Date')
    amz_earliest_ship_date = fields.Datetime('Earliest Ship Date')
    amz_last_update_date = fields.Datetime('Last Update Date')
    amz_latest_delivery_date = fields.Datetime('Latest Delivery Date')
    amz_purchase_date = fields.Datetime('Purchase Date')

    @api.multi
    def get_fba_fees(self):
        now = datetime.now()
        for so in self:
            if so.amz_order_type != 'fba':
                continue
            _logger.info('Order: %s', so.web_order_id)
            fee_params = {'Action': 'ListFinancialEvents', 'AmazonOrderId': so.web_order_id}
            fee_details = self.store_id.process_amz_request('GET', '/Finances/2015-05-01', now, fee_params)
            fba_fulfillment_fee = 0.0
            fba_commission = 0.0
            try:
                if type(fee_details['ListFinancialEventsResponse']['ListFinancialEventsResult']['FinancialEvents']['ShipmentEventList']['ShipmentEvent']) == list:
                    for el in fee_details['ListFinancialEventsResponse']['ListFinancialEventsResult']['FinancialEvents']['ShipmentEventList']['ShipmentEvent']:
                        fees = el['ShipmentItemList']['ShipmentItem']
                        if not isinstance(fees, list):
                            fees = [fees]
                        for fee in fees:
                            fee_items = fee['ItemFeeList']['FeeComponent']
                            for fee_item in fee_items:
                                if fee_item['FeeType']['value'] == 'FBAPerUnitFulfillmentFee':
                                    fba_fulfillment_fee += -float(fee_item['FeeAmount']['CurrencyAmount']['value'])
                                elif fee_item['FeeType']['value'] == 'Commission':
                                    fba_commission += -float(fee_item['FeeAmount']['CurrencyAmount']['value'])
                else:
                    fees = fee_details['ListFinancialEventsResponse']['ListFinancialEventsResult']['FinancialEvents']['ShipmentEventList']['ShipmentEvent']['ShipmentItemList']['ShipmentItem']
                    if not isinstance(fees, list):
                        fees = [fees]
                    for fee in fees:
                        fee_items = fee['ItemFeeList']['FeeComponent']
                        for fee_item in fee_items:
                            if fee_item['FeeType']['value'] == 'FBAPerUnitFulfillmentFee':
                                fba_fulfillment_fee += -float(fee_item['FeeAmount']['CurrencyAmount']['value'])
                            elif fee_item['FeeType']['value'] == 'Commission':
                                fba_commission += -float(fee_item['FeeAmount']['CurrencyAmount']['value'])
                so.write({
                    'fba_fulfillment_fee': fba_fulfillment_fee,
                    'fba_commission': fba_commission
                })
            except Exception as e:
                _logger.error('No FBA fee details found for %s \n %s' % (so.web_order_id, (e.message or repr(e))))

    @api.multi
    def cron_get_amz_fba_fees(self):
        self.env['slack.calls'].notify_slack('[STORE] Get Amazon FBA Fees', 'Started at %s' % datetime.utcnow())
        so_ids = self.search([('state', '!=', 'cancel'), ('amz_order_type', '=', 'fba'), ('fba_commission', '=', False)], limit=40)
        for so in so_ids:
            so.get_fba_fees()
            self.env.cr.commit()
        self.env['slack.calls'].notify_slack('[STORE] Get Amazon FBA Fees', 'Ended at %s' % datetime.utcnow())

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if not res.amz_order_type:
            if res.store_id.site == 'ebay':
                res.amz_order_type = 'ebay'
            elif res.store_id.site == 'amz':
                res.amz_order_type = 'normal'
        return res
