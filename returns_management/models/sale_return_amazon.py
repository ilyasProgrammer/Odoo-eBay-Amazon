# -*- coding: utf-8 -*-

import sys
import logging
import time
from datetime import datetime, timedelta
from odoo import models, fields, api, tools

_logger = logging.getLogger(__name__)


class SaleReturnsAmazon(models.Model):
    _inherit = 'sale.return'

    amz_related_message_id = fields.Many2one('sale.store.amz.return.message', 'Message')
    amz_return_type = fields.Char('Return type', track_visibility='onchange')
    amz_return_request_status = fields.Char('Return status', track_visibility='onchange')
    amz_return_request_date = fields.Datetime('Request date', track_visibility='onchange')
    amz_label_to_be_paid_by = fields.Char('Label paid by', track_visibility='onchange')
    amz_rma_id = fields.Char('Amazon rma id', track_visibility='onchange')
    amz_label_cost = fields.Float('Label cost', track_visibility='onchange')
    amz_label_type = fields.Char('Label type', track_visibility='onchange')
    amz_return_carrier = fields.Char('Return carrier', track_visibility='onchange')
    amz_tracking_id = fields.Char('Amazon tracking', track_visibility='onchange')
    amz_refund_date = fields.Datetime('Refund date', track_visibility='onchange')
    amz_refund_amount = fields.Float('Amazon Refund', track_visibility='onchange')
    amz_adjusted_fee = fields.Float('Adjusted Fee', track_visibility='onchange')
    amz_resolution = fields.Char('Resolution')
    amz_return_request_details = fields.Char('Return Link')

    missed = fields.Boolean('True if was created from the year check')

    @api.model
    def amazon_get_returns(self, from_date=None, to_date=None):
        now = datetime.now()
        from_date = now + timedelta(days=-10) if not from_date else from_date
        to_date = now if not to_date else to_date
        amz_store_ids = self.env['sale.store'].search([('site', '=', 'amz')])
        for store in amz_store_ids:
            report_type = '_GET_XML_RETURNS_DATA_BY_RETURN_DATE_'
            params = {'StartDate': from_date.strftime('%Y-%m-%d' + 'T' + '%H:%M:%S'),
                      'EndDate': to_date.strftime('%Y-%m-%d' + 'T' + '%H:%M:%S')
                      }
            _logger.info('AMZ returns report requested ...')
            report_request_id = store.amz_request_report(now, report_type, params)
            _logger.info('AMZ getting status of requested report ...')
            generated_report_id = store.amz_get_status_of_report_request(now, report_request_id)
            if generated_report_id:
                _logger.info('AMZ returns report is ready. Downloading report ...')
                data = store.amz_get_report(now, generated_report_id, None)
                t = len(data['AmazonEnvelope']['Message']['return_details'])
                i = 0
                for ret in data['AmazonEnvelope']['Message']['return_details']:
                    amz_order = ''
                    _logger.info("\n\nAmazon return %s/%s", i, t)
                    i += 1
                    try:
                        old_return, new_ret_id = self._amz_prepare_return_data(ret, store)
                        # self._cr.commit()
                        # self.amazon_process_return(old_return or new_ret_id)
                        time.sleep(10)  # Cuz too much of throttles
                    except Exception as e:
                        _logger.error('Error in: %s' % amz_order)
                        _logger.error('Error in: %s' % ret['order_id']['value'])
                        _logger.error('Error: %s' % sys.exc_info()[0])
                        _logger.error('Error: %s' % sys.exc_info()[1])
                        _logger.error('Error: %s' % tools.ustr(e))
                        if type(ret['item_details']) != list:
                            msg = 'Error in returns: %s Store:%s ASIN:%s Web_order_id:%s' % (e, store.code, ret['item_details']['asin']['value'], ret['order_id']['value'])
                        else:
                            msg = 'Error in returns: %s Store:%s Web_order_id:%s' % (e, store.code, ret['order_id']['value'])
                        title = 'Error in returns'
                        text = 'Error in returns. %s Store: %s Order data: %s' % (e, store.name, ret['order_id']['value'])
                        self.slack_error(msg, title, text)
                        time.sleep(10)

    @api.model
    def _amz_prepare_return_data(self, ret, store):
        new_ret_id = self.env['sale.return']
        order_id = self.env['sale.order'].search([('web_order_id', '=', ret['order_id']['value']), ('state', '!=', 'cancel')])
        if len(order_id) < 1:
            msg = 'Trying to create return but sale order does not exists: %s %s' % (store.code, ret)
            self.slack_error(msg, 'Cant find order for return', 'Cant find order for return. Store: %s Order data: %s' % (store.name, ret['order_id']['value']))
        elif len(order_id) > 1:
            msg = 'Trying to create return but few sales orders with same web id: Store:%s ASIN:%s Web_order_id:%s' % (store.code, ret['item_details']['asin']['value'], ret['order_id']['value'])
            self.slack_error(msg, 'Duplication', 'Duplication. Store: %s Order data: %s' % (store.name, ret['order_id']['value']))
        refund_data = self.amz_get_refund_data(store, order_id)
        ret_vals = self.amz_collect_values(ret, refund_data, order_id)
        if order_id:
            old_return = self.env['sale.return'].search([('sale_order_id', '=', order_id.id)])
        else:
            old_return = self.env['sale.return'].search([('amz_rma_id', '=', ret_vals['amz_rma_id'])])
        if len(old_return) > 1:
            self.slack_error('Too many old returns: Store:%s %s' % (store.code, ret), 'Duplication', 'Duplication. Store: %s Order data: %s' % (store.name, ret['order_id']['value']))
            return False, False
        elif len(old_return) == 1:
            self._amz_old_return(old_return, ret, ret_vals, order_id)
        else:
            new_ret_id = self._amz_new_return(ret, ret_vals, order_id)
        return old_return, new_ret_id

    @api.model
    def amz_get_refund_data(self, store, order_id):
        refund_date = None
        total_refund = 0.0
        amz_adjusted_fee = 0.0
        if not order_id:
            return {'refund_date': refund_date, 'total_refund': total_refund, 'amz_adjusted_fee': amz_adjusted_fee}
        refund_params = {'Action': 'ListFinancialEvents', 'AmazonOrderId': order_id.web_order_id}
        now = datetime.now()
        _logger.info('Getting refund data ...')
        refund_details = store.process_amz_request('GET', '/Finances/2015-05-01', now, refund_params)
        try:
            if dv(refund_details, ('ListFinancialEventsResponse', 'ListFinancialEventsResult', 'FinancialEvents', 'RefundEventList', 'ShipmentEvent')):
                fd = to_list(refund_details['ListFinancialEventsResponse']['ListFinancialEventsResult']['FinancialEvents']['RefundEventList']['ShipmentEvent'])
                refund_date = amazon_date_from_string(fd[0]['PostedDate']['value'])
                for shipment_event in fd:
                    for shipment_item in to_list(shipment_event['ShipmentItemAdjustmentList']['ShipmentItem']):
                        for cc in shipment_item['ItemChargeAdjustmentList']['ChargeComponent']:
                            total_refund += float(cc['ChargeAmount']['CurrencyAmount']['value'])
                        for fc in shipment_item['ItemFeeAdjustmentList']['FeeComponent']:
                            amz_adjusted_fee += float(fc['FeeAmount']['CurrencyAmount']['value'])
        except Exception as e:
            _logger.warning(e)
        return {'refund_date': refund_date, 'total_refund': total_refund, 'amz_adjusted_fee': amz_adjusted_fee}

    @api.model
    def _amz_new_return(self, ret, ret_vals, order_id):
        time.sleep(12)
        return_model = self.env['sale.return']
        new_ret_id = return_model.create(ret_vals)
        _logger.info('New amazon return created: %s', new_ret_id.id)
        # Lines
        if type(ret['item_details']) == list:
            for it_det in ret['item_details']:
                line_vals = self.amz_collect_line_vals(it_det, order_id, new_ret_id, return_model)
                self.env['sale.return.line'].create(line_vals)
        else:
            line_vals = self.amz_collect_line_vals(ret['item_details'], order_id, new_ret_id, return_model)
            new_ret_line = self.env['sale.return.line'].create(line_vals)
            _logger.info('New amazon return line created: %s, %s', new_ret_line, line_vals)
        return new_ret_id

    @api.model
    def _amz_old_return(self, old_return, ret, ret_vals, order_id):
        return_model = self.env['sale.return']
        _logger.info('Found old amazon return: %s', old_return.ids)
        old_return.write(ret_vals)
        if type(ret['item_details']) == list:
            # old_return.return_line_ids.unlink()  # Lets just replace existing data
            for it_det in ret['item_details']:
                line_vals = self.amz_collect_line_vals(it_det, order_id, return_model, old_return)
                ret_line = old_return.return_line_ids.filtered(lambda x: x.product_id.id == line_vals['product_id'])
                if ret_line:
                    _logger.info('Old return line already exist: line_id=%s lad=%s', ret_line.id, ret_line.product_id.name)
                else:
                    self.env['sale.return.line'].create(line_vals)
        else:
            pass  # Don't touch single line old returns

    @api.model
    def amz_collect_line_vals(self, item_details, order_id, new_ret_id, old_return):
        product = self.amz_get_product(item_details)
        line_vals = {
            'sale_order_id': False or order_id.id,
            'return_id': new_ret_id.id or old_return.id,
            'product_id': False or product.id,
            'product_uom_qty': int(item_details['return_quantity']['value']),
            'product_uom': 1,
            # 'sale_line_id': line.id,
            'name': item_details['asin']['value'],
            'amz_in_policy': bool(item_details['in_policy']['value']),
            'amz_return_quantity': int(item_details['return_quantity']['value']),
            'amz_return_reason_code': item_details['return_reason_code']['value'],
            'amz_resolution': item_details['resolution']['value']
        }
        return line_vals

    @api.model
    def amz_get_product(self, item_details):
        if not dv(item_details, ('asin', 'value')):
            _logger.error('There is no asin: %s', item_details)
            return False
        pl = self.env['product.listing'].search([('asin', '=', item_details['asin']['value'])])
        if pl:
            pl = pl[0]
        else:
            _logger.error('Cant find listing: %s', item_details)
            return False
        return pl.product_id

    @api.model
    def amazon_get_all_year_returns(self, year):
        """
        Get returns of all year until now
        """
        request_throttling = 60 # seconds
        now = datetime.now()
        year = year or now.year
        slack_returns_channel = self.env['ir.config_parameter'].get_param('slack_returns_channel')
        msg = '[amazon] Pulling amazon %s returns, started at %s' % (year, datetime.utcnow())
        attachment = {
            'color': '#7CD197',
            'fallback': 'Returns pulling',
            'title': '[amazon] Started returns pulling for year %s' % year,
            'text': msg
        }
        self.env['slack.calls'].notify_slack('%s Amazon Returns pulling' % year, '', slack_returns_channel, attachment)
        _logger.info(msg)
        periods = []
        from_date = datetime(year, 1, 1)
        to_date = from_date + timedelta(days=60)
        periods.append((from_date, to_date))
        while to_date.year <= year and to_date < now:
            from_date = to_date
            to_date = to_date + timedelta(days=60)
            if to_date > now:
                if to_date.year > year:
                    to_date = datetime(year + 1, 1, 1)
                else:
                    to_date = now
            elif to_date.year > year:
               to_date = datetime(year + 1, 1, 1)
            periods.append((from_date, to_date))
        for period in periods:
            try:
                now = datetime.now()
                _logger.info('Pulling Amazon returns for year %s period: %s - %s' % (year, period[0].date(), period[1].date()))
                self.env['sale.return'].amazon_get_returns(period[0], period[1])
                now2 = datetime.now()
                seconds_passed = (now2 - now).total_seconds()
                if seconds_passed < request_throttling:
                    time.sleep(request_throttling - seconds_passed)
            except Exception as e:
                _logger.error('Error: %s' % sys.exc_info()[0])
                _logger.error('Error: %s' % sys.exc_info()[1])
                _logger.error('Error: %s' % tools.ustr(e))
                title = '[amazon] Error in returns'
                text = 'Something went wrong pulling returns in the period %s to %s' % (period[0].date(), period[1].date())
                self.slack_error('Amazon Returns Error', title, text)
        msg = 'Done pulling of returns for all amazon stores for the year %s' % year
        _logger.info(msg)
        attachment = {
            'color': '#7CD197',
            'fallback': 'Returns pulling',
            'title': '[amazon] Pulling of returns for year %s is done' % year,
            'text': msg
        }
        self.env['slack.calls'].notify_slack('%s Amazon Returns pulling' % year, '', slack_returns_channel, attachment)

    # @api.model
    # def amazon_get_all_year_returns(self, year):
    #     """
    #     Get returns of all year until now
    #     """
    #     request_throttling = 60 # seconds
    #     now = datetime.now()
    #     periods = []
    #     from_date = datetime(year, 1, 1)
    #     to_date = from_date + timedelta(days=60)
    #     periods.append((from_date, to_date))
    #     while to_date.year <= year and to_date < now:
    #         from_date = to_date
    #         to_date = to_date + timedelta(days=60)
    #         if to_date > now:
    #             to_date = now
    #         elif to_date.year > year:
    #            to_date = datetime(year + 1, 1, 1)
    #         periods.append((from_date, to_date))
    #     for period in periods:
    #         now = datetime.now()
    #         self.env['sale.return'].amazon_get_returns(period[0], period[1])
    #         now2 = datetime.now()
    #         seconds_passed = (now2 - now).total_seconds()
    #         if seconds_passed < request_throttling:
    #             time.sleep(request_throttling - seconds_passed)

    @api.model
    def amazon_process_return(self, r):
        # Create return move
        if r.receipt_pickings_count == 0:
            if (r.amz_return_request_status == 'Approved' or r.amz_resolution == 'StandardRefund') and r.return_line_ids:
                r.create_picking_for_receipt()
                r.receipt_state = 'to_receive'
                r.with_return = True
        if r.amz_resolution == 'StandardRefund':
            r.with_refund = True
            r.with_replacement = False
        # Set no replacement
        # -
        # Create replacement
        # -
        # Set refund state = 'We must refund'
        if r.amz_refund_amount:
            r.with_refund = True

    @api.model
    def amz_collect_values(self, ret, refund_data, order_id):
        carrier = dv(ret, ('label_details', 'return_carrier', 'value'))
        ret_vals = {
            'type': 'amazon',
            'initiated_by': 'webstore',
            'state': 'open',
            'amz_refund_amount': refund_data['total_refund'],
            'amz_refund_date': refund_data['refund_date'],
            'amz_adjusted_fee': refund_data['amz_adjusted_fee'],
            'sale_order_id': order_id.id if order_id else False,
            'request_date': datetime.strptime(ret['return_request_date']['value'], "%Y-%m-%dT%H:%M:%SZ"),
            'amz_return_request_date': datetime.strptime(ret['return_request_date']['value'], "%Y-%m-%dT%H:%M:%SZ"),
            'amz_return_type': dv(ret, ('return_type', 'value')),
            'amz_return_request_status': dv(ret, ('return_request_status', 'value')),
            'amz_label_to_be_paid_by': ret['label_to_be_paid_by']['value'],
            'amz_rma_id': dv(ret, ('amazon_rma_id', 'value')),
            'amz_label_cost': float(dv(ret, ('label_details', 'label_cost', 'value'), 0.0)),
            'amz_label_type': dv(ret, ('label_details', 'label_type', 'value')),
            'amz_return_carrier': dv(ret, ('label_details', 'return_carrier', 'value')),
            'carrier_id': self.get_carrier(carrier) if carrier else False,
            'amz_tracking_id': dv(ret, ('label_details', 'tracking_id', 'value')),
            'tracking_number': dv(ret, ('label_details', 'tracking_id', 'value')),
        }
        return ret_vals


class SaleReturnLineAmazon(models.Model):
    _inherit = 'sale.return.line'

    amz_in_policy = fields.Boolean('In policy')
    amz_resolution = fields.Char('Resolution')
    amz_return_quantity = fields.Char('Qty')
    amz_return_reason_code = fields.Char('Reason')
    amz_return_request_details = fields.Char('Return')

    @api.multi
    def write(self, values):
        result = super(SaleReturnLineAmazon, self).write(values)
        self.return_id.amz_resolution = values['amz_resolution'] if values.get('amz_resolution') else self.return_id.amz_resolution
        self.return_id.amz_return_request_details = values['amz_return_request_details'] if values.get('amz_return_request_details') else self.return_id.amz_return_request_details
        return result


def amazon_date_from_string(date_string):
    date = None
    try:
        date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        pass
    if not date:
        try:
            date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
        except:
            pass
    return date


def dv(data, path, ret_type=None):
    # Deep value of nested dict. Return ret_type if cant find it
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:])
        else:
            return ret_type
    return data


def to_list(dict_or_list):
        if isinstance(dict_or_list, dict):
            return [dict_or_list]
        elif isinstance(dict_or_list, list):  # Explicit cases in case the api changes
            return dict_or_list
        else:
            return []
