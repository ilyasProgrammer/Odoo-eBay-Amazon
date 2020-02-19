# -*- coding: utf-8 -*-

import logging
import time
import sys
import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, tools

_logger = logging.getLogger(__name__)


class SaleReturnsEbay(models.Model):
    _inherit = 'sale.return'

    ebay_returnId = fields.Char('Return ID', help='eBay returnId', track_visibility='onchange')
    ebay_state = fields.Selection([('AUTO_REFUND_INITIATED', 'Auto Refund Initiated'),
                                   ('CLOSED', 'Closed'),
                                   ('INITIAL', 'Initial'),
                                   ('ITEM_DELIVERED', 'Item Delivered'),
                                   ('ITEM_KEPT', 'Item Kept'),
                                   ('ITEM_READY_TO_SHIP', 'Item Ready to Ship'),
                                   ('ITEM_SHIPPED', 'Item Shipped'),
                                   ('LESS_THAN_A_FULL_REFUND_ISSUED', 'Less Than a Full Refund Issued'),
                                   ('PARTIAL_REFUND_DECLINED', 'Partial Refund Declined'),
                                   ('PARTIAL_REFUND_FAILED', 'Partial Refund Failed'),
                                   ('PARTIAL_REFUND_INITIATED', 'Partial Refund Initiated'),
                                   ('PARTIAL_REFUND_NON_PAYPAL_INITIATED', 'Partial Refund Non Paypal Initiated'),
                                   ('PARTIAL_REFUND_REQUESTED', 'Partial Refund Requested'),
                                   ('PARTIAL_REFUNDED', 'Partial Refunded'),
                                   ('PAYOUT_INITIATED', 'Payout Initiated'),
                                   ('REFUND_INITIATED', 'Refund Initiated'),
                                   ('REFUND_SENT_PENDING_CONFIRMATION', 'Refund Sent Pending Confirmation'),
                                   ('REFUND_TIMEOUT', 'Refund Timeout'),
                                   ('REPLACED', 'Replaced'),
                                   ('REPLACEMENT_CLOSED', 'Replacement Closed'),
                                   ('REPLACEMENT_DELIVERED', 'Replacement Delivered'),
                                   ('REPLACEMENT_LABEL_REQUESTED', 'Replacement Label Requested'),
                                   ('REPLACEMENT_LABEL_REQUESTED_TIMEOUT', 'Replacement Label Requested Timeout'),
                                   ('REPLACEMENT_REQUEST_TIMEOUT', 'Replacement Request Timeout'),
                                   ('REPLACEMENT_REQUESTED', 'Replacement Request'),
                                   ('REPLACEMENT_RMA_PENDING', 'Replacement RMA Pending'),
                                   ('REPLACEMENT_SHIPPED', 'Replacement Shipped'),
                                   ('REPLACEMENT_STARTED', 'Replacement Started'),
                                   ('RETURN_LABEL_PENDING', 'Return Label Pending'),
                                   ('RETURN_LABEL_PENDING_TIMEOUT', 'Return Label Pending Timeout'),
                                   ('RETURN_LABEL_REQUESTED', 'Return Label Requested'),
                                   ('RETURN_LABEL_REQUESTED_TIMEOUT', 'Return Label Requested Timeout'),
                                   ('RETURN_REJECTED', 'Return Rejected'),
                                   ('RETURN_REQUEST_TIMEOUT', 'Return Request Timeout'),
                                   ('RETURN_REQUESTED', 'Return Requested'),
                                   ('RMA_PENDING', 'RMA Pending'),
                                   ('UNKNOWN', 'Unknown')], 'eBay State', help='eBay state', track_visibility='onchange')
    ebay_status = fields.Selection([('CLOSED', 'Closed'),
                                    ('ESCALATED', 'Escalated'),
                                    ('ITEM_DELIVERED', 'Item Delivered'),
                                    ('ITEM_SHIPPED', 'Item Shipped'),
                                    ('LESS_THAN_A_FULL_REFUND_ISSUED', 'Less Than a Full Refund Issued'),
                                    ('PARTIAL_REFUND_DECLINED', 'Partial Refund Declined'),
                                    ('PARTIAL_REFUND_FAILED', 'Partial Refund Failed'),
                                    ('PARTIAL_REFUND_INITIATED', 'Partial Refund Initiated'),
                                    ('PARTIAL_REFUND_REQUESTED', 'Partial Refund Requested'),
                                    ('READY_FOR_SHIPPING', 'Ready For Shipping'),
                                    ('REPLACED', 'Replaced'),
                                    ('REPLACEMENT_CLOSED', 'Replacement Closed'),
                                    ('REPLACEMENT_DELIVERED', 'Replacement Delivered'),
                                    ('REPLACEMENT_LABEL_REQUESTED', 'Replacement Label Requested'),
                                    ('REPLACEMENT_REQUESTED', 'Replacement Requested'),
                                    ('REPLACEMENT_SHIPPED', 'Replacement Shipped'),
                                    ('REPLACEMENT_STARTED', 'Replacement Started'),
                                    ('REPLACEMENT_WAITING_FOR_RMA', 'Replacement Waiting Fro RMA'),
                                    ('RETURN_LABEL_REQUESTED', 'Return Label Requested'),
                                    ('RETURN_REJECTED', 'Return Rejected'),
                                    ('RETURN_REQUESTED', 'Return Requested'),
                                    ('RETURN_REQUESTED_TIMEOUT', 'Return Requested Timeout'),
                                    ('UNKNOWN', 'Unknown'),
                                    ('WAITING_FOR_RETURN_LABEL', 'Waiting For Return Label'),
                                    ('WAITING_FOR_RMA', 'Waiting For RMA'), ], 'eBay Status', help='eBay status', track_visibility='onchange')
    ebay_timeoutDate = fields.Datetime('Timeout date', help='eBay timeoutDate', track_visibility='onchange')
    ebay_sellerTotalRefund = fields.Float('eBay Refund', help='eBay sellerTotalRefund', track_visibility='onchange')
    ebay_currentType = fields.Selection([('CANCEL', 'CANCEL'),
                                         ('MONEY_BACK', 'MONEY_BACK'),
                                         ('REPLACEMENT', 'REPLACEMENT'),
                                         ('UNKNOWN', 'UNKNOWN')], 'Current Type', help='eBay currentType', track_visibility='onchange')
    ebay_comments = fields.Char('Comment', help='eBay comments', track_visibility='onchange')
    ebay_creationDate = fields.Datetime('Created', help='eBay creationDate', track_visibility='onchange')
    ebay_reason = fields.Selection([('ARRIVED_DAMAGED', 'Arrived Damaged'),
                                    ('ARRIVED_LATE', 'Arrived Late'),
                                    ('BUYER_CANCEL_ORDER', 'Buyer Cancel Order'),
                                    ('BUYER_NO_SHOW', 'Buyer No Show'),
                                    ('BUYER_NOT_SCHEDULED', 'Buyer Not Scheduled'),
                                    ('BUYER_REFUSED_TO_PICKUP', 'Buyer Refused To Pickup'),
                                    ('DEFECTIVE_ITEM', 'Defective Item'),
                                    ('DIFFERENT_FROM_LISTING', 'Different From Listing'),
                                    ('EXPIRED_ITEM', 'Expired Item'),
                                    ('FAKE_OR_COUNTERFEIT', 'Fake Or Counterfeit'),
                                    ('FOUND_BETTER_PRICE', 'Found Better Price'),
                                    ('IN_STORE_RETURN', 'In Store Return'),
                                    ('MISSING_PARTS', 'Missing Parts'),
                                    ('NO_LONGER_NEED_ITEM', 'No Longer Need Item'),
                                    ('NO_REASON', 'No Reason'),
                                    ('NOT_AS_DESCRIBED', 'Not As Described'),
                                    ('ORDERED_ACCIDENTALLY', 'Ordered Accidentally'),
                                    ('ORDERED_DIFFERENT_ITEM', 'Ordered Different Item'),
                                    ('ORDERED_WRONG_ITEM', 'Ordered Wrong Item'),
                                    ('OTHER', 'Other'),
                                    ('OUT_OF_STOCK', 'Out Of Stock'),
                                    ('RETURNING_GIFT', 'Returning Gift'),
                                    ('VALET_DELIVERY_ISSUES', 'Valet Delivery Issues'),
                                    ('VALET_UNAVAILABLE', 'Valet Unavailable'),
                                    ('WRONG_SIZE', 'Wrong Size')], 'Reason', help='eBay reason', track_visibility='onchange')
    ebay_reasonType = fields.Selection([('CANCEL', 'Cancel'),
                                        ('MONEY_BACK', 'Money Back'),
                                        ('REPLACEMENT', 'Replacement'),
                                        ('UNKNOWN', 'Unknown')], 'Reason Type', help='eBay reasonType')
    ebay_transactionId = fields.Char('Transaction ID', help='eBay transactionId', track_visibility='onchange')
    ebay_returnQuantity = fields.Integer('Return quantity', help='eBay returnQuantity', track_visibility='onchange')
    ebay_label_cost = fields.Float('Label Cost')
    ebay_label_payee = fields.Selection([('BUYER', 'BUYER'),
                                         ('EBAY', 'EBAY'),
                                         ('OTHER', 'OTHER'),
                                         ('SELLER', 'SELLER'),
                                         ('SYSTEM', 'SYSTEM')], 'Label payee')
    ebay_receipt_deliveryStatus = fields.Selection([('canceled', 'canceled'),
                                                    ('CREATED', 'CREATED'),
                                                    ('DELIVERED', 'DELIVERED'),
                                                    ('IN_TRANSIT', 'IN_TRANSIT'),
                                                    ('UNKNOWN', 'UNKNOWN')], 'Receive status')
    ebay_replacement_deliveryStatus = fields.Selection([('canceled', 'canceled'),
                                                        ('CREATED', 'CREATED'),
                                                        ('DELIVERED', 'DELIVERED'),
                                                        ('IN_TRANSIT', 'IN_TRANSIT'),
                                                        ('UNKNOWN', 'UNKNOWN')], 'Replacement status')
    ebay_refundStatus = fields.Selection([('FAILED', 'FAILED'), ('OTHER', 'OTHER'), ('PENDING', 'PENDING'), ('SUCCESS', 'SUCCESS')], 'Refund Status')
    ebay_refundInitiationType = fields.Selection([('AUTO_REFUND', 'AUTO_REFUND'), ('OTHER', 'OTHER'), ('SELLER_INITIATED', 'SELLER_INITIATED')], 'Init Type')
    ebay_creationInfo_type = fields.Selection([('CANCEL', 'CANCEL'), ('MONEY_BACK', 'MONEY_BACK'), ('REPLACEMENT', 'REPLACEMENT'), ('UNKNOWN', 'UNKNOWN')], 'Creation Type')
    ebay_response_history = fields.Text('History')

    @api.model
    def ebay_get_new_returns(self):
        # TODO consider multiline returns !
        # Only RETURN_STARTED ones. Called by cron. Get all newly created returns from ebay for every store and create sale.return for every one
        self.env['slack.calls'].notify_slack('[eBay] Get ebay new returns', 'Started at %s' % datetime.utcnow())
        stores = self.env['sale.store'].search([('enabled', '=', True), ('site', '=', 'ebay')])
        for store in stores:
            _logger.info('Fetching returns for store: ' + store.name)
            self.get_new_returns(store)
        _logger.info('Done fetching of returns for all eBay stores')
        self.env['slack.calls'].notify_slack('[eBay] Get ebay new returns', 'Ended at %s' % datetime.utcnow())

    @api.model
    def get_new_returns(self, store, page=1):
        slack_returns_channel = self.env['ir.config_parameter'].get_param('slack_returns_channel')
        return_response = store.ebay_postorder_execute(action='return', args='search?offset=%s&return_state=RETURN_STARTED' % page)
        if not return_response.status_code == 200:
            _logger.error('Bad eBay response: %s', return_response.status_code)
            return
        return_data = return_response.json()
        _logger.info('Received eBay returns: %s', return_response.status_code)
        if not return_data.get('members'):
            _logger.error('Bad eBay data in response: %s', return_data)
            return
        for member in return_data['members']:
            OrderLineItemID = ''
            try:
                member_response = store.ebay_postorder_execute(action='return', args=member['returnId'])
                if not member_response.status_code == 200:
                    _logger.error('Bad eBay response: %s', member_response.status_code)
                    continue
                ret = member_response.json()
                OrderLineItemID = ret['detail']['itemDetail']['itemId'] + '-' + ret['detail']['itemDetail']['transactionId']
                order_id = self.env['sale.order'].search([('web_order_id', '=', OrderLineItemID), ('state', '!=', 'cancel')])
                if not order_id:
                    order_line_id = self.env['sale.order.line'].search([('web_orderline_id', '=', OrderLineItemID)])
                    if order_line_id:
                        order_id = order_line_id.order_id
                if not order_id:
                    msg = 'Trying to create return but sale order does not exists: Store:%s Item:%s  Transaction:%s Web_order_id:%s' % (store.code, ret['detail']['itemDetail']['itemId'],ret['detail']['itemDetail']['transactionId'], OrderLineItemID)
                    _logger.error(msg)
                    attachment = {
                        'color': '#DC3545',
                        'fallback': 'Returns pulling',
                        'title': 'Returns pulling. Store: %s' % store.code,
                        'text': msg
                    }
                    self.env['slack.calls'].notify_slack('eBay returns', '', slack_returns_channel, attachment)
                    continue
                    # we decide to skip return creation in such situations
                    # order_id = store.ebay_get_order_by_order_id(OrderLineItemID, datetime.now())
                    # _logger.warning('New sale order created: %s', order_id.id)
                if len(order_id) > 1:
                    msg = 'Several orders for one web order id.: Orders: %s Store: %s Item: %s Transaction: %s Web_order_id: %s' % (len(order_id), store.code, ret['detail']['itemDetail']['itemId'], ret['detail']['itemDetail']['transactionId'], OrderLineItemID)
                    _logger.error(msg)
                    continue
                new_ret_id = self.env['sale.return']
                old_return = self.env['sale.return'].search([('ebay_returnId', '=', ret['summary']['returnId'])])
                cr_info = ret['summary']['creationInfo']
                comment = cr_info['comments']['content'] if cr_info['comments'] else False
                ret_vals = self.ebay_collect_values(ret, cr_info, order_id, comment, old_return)
                if old_return:
                    for r in old_return:
                        _logger.info('\n\nFound old return: %s', r.id)
                        if ret['summary']['status'] != old_return.ebay_status:
                            msg = "%s status updated: %s -> %s" % (old_return.name, old_return.ebay_status, ret['summary']['status'])
                            attachment = {
                                'color': '#7CD197',
                                'fallback': 'Returns pulling',
                                'title': 'Returns updating cron. Store: %s' % store.code,
                                'text': msg
                            }
                            self.env['slack.calls'].notify_slack('eBay returns', '', slack_returns_channel, attachment)
                        old_return.write(ret_vals)
                        _logger.debug('\n\nOld return %s updated with: %s', r.id, ret_vals)
                        return_id = r.id
                else:
                    new_ret_id = self.env['sale.return'].create(ret_vals)
                    return_id = new_ret_id.id
                    msg = 'New return created: %s' % new_ret_id.name
                    _logger.info(msg)
                    attachment = {
                        'color': '#7CD197',
                        'fallback': 'Returns pulling',
                        'title': 'Returns pulling. Store: %s' % store.code,
                        'text': msg
                    }
                    self.env['slack.calls'].notify_slack('eBay returns', '', slack_returns_channel, attachment)
                    # Lines
                    # for ln in ret['lines']:  # TODO combined orders returns ?
                    for line in order_id.order_line:
                        line_vals = {
                            'sale_order_id': order_id.id,
                            'return_id': new_ret_id.id,
                            'name': OrderLineItemID,
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'sale_line_id': line.id,
                            'return_reason': cr_info['reason'],
                            'customer_comments': comment,
                            'item': cr_info['item']['itemTitle'],
                        }
                        new_ret_line = self.env['sale.return.line'].create(line_vals)
                        _logger.info('New return line created: %s', new_ret_line.id)
                (old_return or new_ret_id).ebay_write_history(ret)
                self.ebay_process_return(old_return or new_ret_id)
                # Get attachments
                _logger.info('Getting attachments from eBay ...')
                files_resp = store.ebay_postorder_execute(action='return', args=ret['summary']['returnId'] + '/files')
                if not files_resp.status_code == 200:
                    _logger.warning('Bad eBay response for files: %s', files_resp.status_code)
                else:
                    files_data = files_resp.json()
                    for ebay_file in files_data['files']:
                        file_vals = {
                            'name': ebay_file['fileName'],
                            'datas': ebay_file['fileData'],
                            'datas_fname': ebay_file['fileName'],
                            'res_model': self._name,
                            'res_id': return_id,
                            'int_type': 'buyer',
                        }
                        old_attachment = self.env['ir.attachment'].search([('name', '=', ebay_file['fileName'])])
                        if len(old_attachment) == 0:
                            new_attachment = self.env['ir.attachment'].create(file_vals)
                            _logger.info('New attachment created: %s', new_attachment.id)
            except Exception as e:
                _logger.error('Error in: %s' % OrderLineItemID)
                _logger.error('Error: %s' % sys.exc_info()[0])
                _logger.error('Error: %s' % sys.exc_info()[1])
                _logger.error('Error: %s' % tools.ustr(e))
        _logger.info('Proceeded returns. Store: %s Page: %s of: %s', store.name, return_data['paginationOutput']['offset'], return_data['paginationOutput']['totalPages'])
        if return_data['paginationOutput']['totalPages'] > return_data['paginationOutput']['offset']:
            self.get_new_returns(store, page=return_data['paginationOutput']['offset']+1)

    @api.model
    def ebay_get_all_returns(self):
        # supposed to be run only once
        base = 'https://api.ebay.com/post-order/v2/return/'
        headers = {'Content-Type': 'application/json', 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'}
        stores = self.env['sale.store'].search([('enabled', '=', True), ('site', '=', 'ebay')])
        for store in stores:
            _logger.info('Fetching returns for store: ' + store.name)
            headers['Authorization'] = 'TOKEN ' + store['ebay_token']
            self.get_returns(store, base, headers)
        _logger.info('Done fetching of returns for all eBay stores')

    def get_returns(self, store, base, headers, page=1, year=None):
        if not year:
            return_response = requests.get(base + 'search?limit=200&offset=%s' % page, headers=headers)
            missed = False
        else:
            date_from = datetime(year, 1, 1).isoformat() + 'Z'
            date_to = datetime(year + 1, 1, 1).isoformat() + 'Z'
            return_response = requests.get(base + 'search?creation_date_range_from=%s&creation_date_range_to=%s&limit=200&offset=%s' % (date_from, date_to, page), headers=headers)
            missed = True
        if not return_response.status_code == 200:
            _logger.error('Bad eBay response: %s', return_response.status_code)
            return
        return_data = return_response.json()
        _logger.info('Received eBay returns: %s', return_response.status_code)
        if not return_data.get('members'):
            _logger.error('Bad eBay data in response: %s', return_data)
            return
        for member in return_data['members']:
            OrderLineItemID = ''
            try:
                member_response = requests.get(base + member['returnId'], headers=headers)
                if not member_response.status_code == 200:
                    _logger.error('Bad eBay response: %s', member_response.status_code)
                    continue
                ret = member_response.json()
                OrderLineItemID = ret['detail']['itemDetail']['itemId'] + '-' + ret['detail']['itemDetail']['transactionId']
                order_id = self.env['sale.order'].search([('web_order_id', '=', OrderLineItemID)])
                if not order_id:
                    order_line_id = self.env['sale.order.line'].search([('web_orderline_id', '=', OrderLineItemID)])
                    if order_line_id:
                        order_id = order_line_id.order_id
                if not order_id:
                    msg = 'Trying to create return but sale order does not exists: Store:%s Item:%s  Transaction:%s Web_order_id:%s' % (store.code, ret['detail']['itemDetail']['itemId'],ret['detail']['itemDetail']['transactionId'], OrderLineItemID)
                    _logger.error(msg)
                    slack_returns_channel = self.env['ir.config_parameter'].get_param('slack_returns_channel')
                    attachment = {
                        'color': '#7CD197',
                        'fallback': 'Returns pulling',
                        'title': 'Returns pulling. Store: %s' % store.code,
                        'text': msg
                    }
                    self.env['slack.calls'].notify_slack('eBay returns', '', slack_returns_channel, attachment)
                new_ret_id = self.env['sale.return']
                # old_return = self.env['sale.return'].search([('ebay_returnId', '=', ret['summary']['returnId'])])
                old_return = self.env['sale.return'].search([('sale_order_id', '=', order_id.id), ('state', '!=', 'cancel')])
                if len(old_return) > 1:
                    _logger.warning('Multiple eBay returns: %s %s', order_id, old_return)
                    continue
                cr_info = ret['summary']['creationInfo']
                comment = cr_info['comments']['content'] if cr_info['comments'] else False
                ret_vals = self.ebay_collect_values(ret, cr_info, order_id, comment, old_return)
                if old_return:
                    _logger.info('Found old return: %s', old_return.ids)
                    old_return.write(ret_vals)
                    _logger.info('Old return %s updated with: %s', old_return.ids, ret_vals)
                    return_id = old_return.id
                    # Keep lines as is ?
                else:
                    ret_vals['missed'] = missed
                    new_ret_id = self.env['sale.return'].create(ret_vals)
                    return_id = new_ret_id.id
                    _logger.info('New eBay return created: %s', new_ret_id.id)
                    # Lines
                    # for ln in ret['lines']:  # TODO combined orders returns ?
                    if order_id:
                        for line in order_id.order_line:
                            if line.web_orderline_id == OrderLineItemID:
                                line_vals = {
                                    'sale_order_id': order_id.id,
                                    'return_id': new_ret_id.id,
                                    'name': OrderLineItemID,
                                    'product_id': line.product_id.id,
                                    'product_uom_qty': line.product_uom_qty,
                                    'product_uom': line.product_uom.id,
                                    'sale_line_id': line.id,
                                    'return_reason': cr_info['reason'],
                                    'customer_comments': comment,
                                    'item': cr_info['item']['itemTitle'],
                                }
                                new_ret_line = self.env['sale.return.line'].create(line_vals)
                                _logger.info('New eBay return line created: %s', new_ret_line.id)
                    else:
                        pl = self.env['product.listing'].search([('name', '=', ret['detail']['itemDetail']['itemId'])])
                        line_vals = {
                            'sale_order_id': False,
                            'return_id': new_ret_id.id,
                            'name': OrderLineItemID,
                            'product_id': pl.product_tmpl_id.id,
                            'product_uom_qty': ret['detail']['itemDetail']['returnQuantity'],
                            'product_uom': pl.product_tmpl_id.uom_id.id,
                            'sale_line_id': False,
                            'return_reason': cr_info['reason'],
                            'customer_comments': comment,
                            'item': cr_info['item']['itemTitle'],
                        }
                        new_ret_line = self.env['sale.return.line'].create(line_vals)
                        _logger.info('New return line created: %s', new_ret_line.id)
                (old_return or new_ret_id).ebay_write_history(ret)
                self.ebay_process_return(old_return or new_ret_id)
                # Get attachments
                files_resp = requests.get(base + ret['summary']['returnId'] + '/files', headers=headers)
                if not files_resp.status_code == 200:
                    _logger.warning('Bad eBay response for files: %s', files_resp.status_code)
                else:
                    files_data = files_resp.json()
                    for ebay_file in files_data['files']:
                        file_vals = {
                            'name': ebay_file['fileName'],
                            'datas': ebay_file['fileData'],
                            'datas_fname': ebay_file['fileName'],
                            'res_model': self._name,
                            'res_id': return_id,
                            'int_type': 'buyer',
                        }
                        old_attachment = self.env['ir.attachment'].search([('name', '=', ebay_file['fileName'])])
                        if len(old_attachment) == 0:
                            new_attachment = self.env['ir.attachment'].create(file_vals)
                            _logger.info('New attachment created: %s', new_attachment.id)
                self._cr.commit()
            except Exception as e:
                _logger.error('Error in: %s' % OrderLineItemID)
                _logger.error(e)
                _logger.error('Error: %s' % sys.exc_info()[0])
                _logger.error('Error: %s' % sys.exc_info()[1])
            self._cr.commit()
        _logger.info('Proceeded returns. Store: %s Page: %s of: %s', store.name, return_data['paginationOutput']['offset'], return_data['paginationOutput']['totalPages'])
        if return_data['paginationOutput']['totalPages'] > return_data['paginationOutput']['offset']:
            self.get_returns(store, base, headers, page=return_data['paginationOutput']['offset']+1)

    @api.model
    def ebay_update_old_returns(self):
        self.env['slack.calls'].notify_slack('[eBay] Update ebay old returns', 'Started at %s' % datetime.utcnow())
        base = 'https://api.ebay.com/post-order/v2/return/'
        headers = {'Content-Type': 'application/json', 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'}
        stores = self.env['sale.store'].search([('enabled', '=', True), ('site', '=', 'ebay')])
        # stores = self.env['sale.store'].browse(5) # vis
        for store in stores:
            _logger.info('Fetching returns for store: ' + store.name)
            headers['Authorization'] = 'TOKEN ' + store['ebay_token']
            self.get_old_returns(store, base, headers)
        _logger.info('Done fetching of returns for all eBay stores')
        self.env['slack.calls'].notify_slack('[eBay] Update ebay old returns', 'Ended at %s' % datetime.utcnow())

    def get_old_returns(self, store, base, headers):
        slack_returns_channel = self.env['ir.config_parameter'].get_param('slack_returns_channel')
        start_date = datetime.strftime(datetime.now() - timedelta(days=50), '%Y-%m-%d')
        returns = self.env['sale.return'].search([('create_date', '>', start_date),
                                                  ('ebay_status', '!=', 'CLOSED'),
                                                  ('store_id', '=', store.id),
                                                  ('ebay_returnId', '!=', False)])
        total = len(returns)
        cnt = 0
        for ret in returns:
            time.sleep(1)
            _logger.info('\n\nProceeding return: %s %s %s %s/%s', store.code, ret.id, ret.ebay_returnId, cnt, total)
            cnt += 1
            return_response = requests.get(base + str(ret.ebay_returnId), headers=headers)
            # return_response = requests.get(base + '5099701171', headers=headers)
            if not return_response.status_code == 200:
                _logger.error('Bad eBay response: %s', return_response)
                continue
            ret = return_response.json()
            _logger.info('Received eBay returns: %s', return_response.status_code)
            try:
                OrderLineItemID = ret['detail']['itemDetail']['itemId'] + '-' + ret['detail']['itemDetail']['transactionId']
                order_id = self.env['sale.order'].search([('web_order_id', '=', OrderLineItemID), ('state', '!=', 'cancel')])
                if not order_id:
                    order_line_id = self.env['sale.order.line'].search([('web_orderline_id', '=', OrderLineItemID)])
                    if order_line_id:
                        order_id = order_line_id.order_id
                if not order_id:
                    _logger.error('Sale order does not exists: ' + OrderLineItemID)
                    continue
                    # we decide to skip return creation in such situations
                    # order_id = store.ebay_get_order_by_order_id(OrderLineItemID, datetime.now())
                    # _logger.warning('New sale order created: %s', order_id.id)
                if len(order_id) > 1:
                    msg = 'Several orders for one web order id.: Orders: %s Store: %s Item: %s Transaction: %s Web_order_id: %s' % (len(order_id), store.code, ret['detail']['itemDetail']['itemId'], ret['detail']['itemDetail']['transactionId'], OrderLineItemID)
                    _logger.error(msg)
                    continue
                old_return = self.env['sale.return'].search([('ebay_returnId', '=', ret['summary']['returnId'])])
                cr_info = ret['summary']['creationInfo']
                comment = cr_info['comments']['content'] if cr_info['comments'] else False
                ret_vals = self.ebay_collect_values(ret, cr_info, order_id, comment, old_return)
                new_ret_id = self.env['sale.return']
                if old_return:
                    _logger.info('Found old return: %s', old_return.ids)
                    _logger.debug('\n\nOld return %s updated with: %s\n', old_return.ids, ret_vals)
                    if ret['summary']['status'] != old_return.ebay_status:
                        msg = "%s status updated: %s -> %s" % (old_return.name, old_return.ebay_status, ret['summary']['status'])
                        attachment = {
                            'color': '#7CD197',
                            'fallback': 'Returns pulling',
                            'title': 'Returns updating cron. Store: %s' % store.code,
                            'text': msg
                        }
                        self.env['slack.calls'].notify_slack('eBay returns', '', slack_returns_channel, attachment)
                    old_return.write(ret_vals)
                    return_id = old_return.id
                    # Keep lines as is ?
                else:
                    new_ret_id = self.env['sale.return'].create(ret_vals)
                    return_id = new_ret_id.id
                    msg = 'New return created: %s' % new_ret_id.name
                    _logger.info(msg)
                    attachment = {
                        'color': '#7CD197',
                        'fallback': 'Returns pulling',
                        'title': 'Returns updating cron. Store: %s' % store.code,
                        'text': msg
                    }
                    self.env['slack.calls'].notify_slack('eBay returns', '', slack_returns_channel, attachment)
                    # Lines
                    # for ln in ret['lines']:  # TODO combined orders returns ?
                    for line in order_id.order_line:
                        line_vals = {
                            'sale_order_id': order_id.id,
                            'return_id': new_ret_id.id,
                            'name': OrderLineItemID,
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'sale_line_id': line.id,
                            'return_reason': cr_info['reason'],
                            'customer_comments': comment,
                            'item': cr_info['item']['itemTitle'],
                        }
                        new_ret_line = self.env['sale.return.line'].create(line_vals)
                        _logger.info('New return line created: %s', new_ret_line.id)
                (old_return or new_ret_id).ebay_write_history(ret)
                self.ebay_process_return(old_return or new_ret_id)
                # Get attachments
                time.sleep(1)
                files_resp = requests.get(base + ret['summary']['returnId'] + '/files', headers=headers)
                if not files_resp.status_code == 200:
                    _logger.warning('Bad eBay response for files: %s', files_resp.status_code)
                else:
                    files_data = files_resp.json()
                    for ebay_file in files_data['files']:
                        file_vals = {
                            'name': ebay_file['fileName'],
                            'datas': ebay_file['fileData'],
                            'datas_fname': ebay_file['fileName'],
                            'res_model': self._name,
                            'res_id': return_id,
                            'int_type': 'buyer',
                        }
                        old_attachment = self.env['ir.attachment'].search([('name', '=', ebay_file['fileName'])])
                        if len(old_attachment) == 0:
                            new_attachment = self.env['ir.attachment'].create(file_vals)
                            _logger.info('New attachment created: %s', new_attachment.id)
            except Exception as e:
                _logger.error('Error: %s' % sys.exc_info()[0])
                _logger.error('Error: %s' % sys.exc_info()[1])
                _logger.error('Error: %s' % tools.ustr(e))

    @api.model
    def ebay_get_all_year_returns(self, year=None):
        year = year or datetime.now().year
        self.env['slack.calls'].notify_slack('[eBay] Update ebay %s returns' % str(year), 'Started at %s' % datetime.utcnow())
        base = 'https://api.ebay.com/post-order/v2/return/'
        headers = {'Content-Type': 'application/json', 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'}
        stores = self.env['sale.store'].search([('enabled', '=', True), ('site', '=', 'ebay')])
        for store in stores:
            _logger.info('Fetching returns for year %s for store: %s' % (str(year), store.name))
            headers['Authorization'] = 'TOKEN ' + store['ebay_token']
            self.get_returns(store, base, headers, year=year)
        _logger.info('Done fetching of returns for all eBay stores for the year %s' % str(year))
        self.env['slack.calls'].notify_slack('[eBay] Update ebay %s returns finished' % str(year), 'Finished at %s' % datetime.utcnow())

    @api.model
    def ebay_write_history(self, ret):
        text = ''
        hist = dv(ret, ('detail', 'responseHistory'))
        for rec in hist:
            text += 'Date: %s  ' % (rec['creationDate']['value'])
            text += 'State: %s -> %s\n' % (rec['fromState'], rec['toState'])
            text += 'Author: %s Activity: %s\n' % (rec['author'], rec['activity'])
            text += 'Text: %s\n' % (rec.get('notes')) if rec.get('notes') else ''
            text += '\n'
        self.ebay_response_history = text

    @api.model
    def ebay_collect_values(self, ret, cr_info, order_id, comment, old_return):
        carrier = dv(ret, ('detail', 'returnShipmentInfo', 'shipmentTracking', 'carrierEnum'))
        ret_vals = {
            'type': 'ebay',
            'initiated_by': 'webstore',
            'ebay_returnId': ret['summary']['returnId'],
            'ebay_transactionId': ret['detail']['itemDetail']['transactionId'],
            'ebay_state': ret['summary']['state'],
            'ebay_status': ret['summary']['status'],
            'ebay_timeoutDate': datetime.strptime(ret['summary']['timeoutDate']['value'][0:19], "%Y-%m-%dT%H:%M:%S"),
            'ebay_sellerTotalRefund': dv(ret, ('summary', 'sellerTotalRefund', 'actualRefundAmount', 'value')),
            'ebay_currentType': ret['summary']['currentType'],
            'ebay_comments': comment,
            'customer_comments': comment,
            'ebay_creationDate': datetime.strptime(cr_info['creationDate']['value'][0:19], "%Y-%m-%dT%H:%M:%S"),
            'ebay_reason': cr_info['reason'],
            'return_reason': cr_info['reason'],
            'ebay_returnQuantity': cr_info['item']['returnQuantity'],
            'sale_order_id': order_id.id if order_id else False,
            'request_date': datetime.strptime(cr_info['creationDate']['value'][0:19], "%Y-%m-%dT%H:%M:%S"),
            'ebay_label_cost': dv(ret, ('detail', 'returnShipmentInfo', 'shippingLabelCost', 'totalAmount', 'value')),
            'tracking_number': dv(ret, ('detail', 'returnShipmentInfo', 'shipmentTracking', 'trackingNumber')),
            'carrier_id': self.get_carrier(carrier) if carrier else False,
            'ebay_label_payee': dv(ret, ('detail', 'returnShipmentInfo', 'payee')),
            'ebay_receipt_deliveryStatus': dv(ret, ('detail', 'returnShipmentInfo', 'shipmentTracking', 'deliveryStatus')),
            'ebay_replacement_deliveryStatus': dv(ret, ('detail', 'replacementShipmentInfo', 'shipmentTracking', 'deliveryStatus')),
            'ebay_refundStatus': dv(ret, ('detail', 'refundInfo', 'actualRefundDetail', 'refundStatus')),
            'ebay_refundInitiationType': dv(ret, ('detail', 'refundInfo', 'actualRefundDetail', 'refundInitiationType')),
            'ebay_creationInfo_type': dv(ret, ('summary', 'creationInfo', 'type')),
        }
        if not old_return.refund_amount:
            for r in dv(ret, ('detail', 'refundInfo', 'actualRefundDetail', 'actualRefund', 'itemizedRefundDetail'), ret_type=[]):
                if r['refundFeeType'] == 'PURCHASE_PRICE':
                    ret_vals['refund_amount'] = float(r['refundAmount']['value'])
                    ret_vals['refund_status'] = 'paid'
                    _logger.info('eBay actual refund set: %s %s', order_id, ret_vals['refund_amount'])
        return ret_vals

    @api.model
    def ebay_process_return(self, r):
        # All most important automation is here
        if r.ebay_currentType == 'MONEY_BACK':
            r.with_return = True
            r.with_refund = True
            r.with_replacement = False
            r.state = 'waiting_buyer_send'
        # Create return move
        if r.receipt_pickings_count == 0:
            if r.ebay_receipt_deliveryStatus in ['CREATED', 'IN_TRANSIT'] or \
                            r.ebay_refundStatus in ['PENDING', 'SUCCESS']:
                r.create_picking_for_receipt()
                r.receipt_state = 'to_receive'
                r.with_return = True
                r.state = 'waiting_receipt'
        # Create replacement. Even receipt is DELIVERED it has to be scanned by WH. Only after it become validated.
        if (r.ebay_receipt_deliveryStatus == 'DELIVERED' or r.receipt_state == 'delivered') and \
                (r.ebay_currentType == 'REPLACEMENT' or r.ebay_replacement_deliveryStatus not in ['canceled', 'UNKNOWN', False]):
            r.with_replacement = True
            r.with_return = True
            r.with_refund = False
            r.replacement_by = 'wh'
            r.replacement_state = 'to_send'
            r.state = 'to_replacement'
            if r.replacement_pickings_count == 0:
                r.create_replacement()
            # r.validate_replacement()
        if r.ebay_replacement_deliveryStatus == 'IN_TRANSIT':
            r.with_return = True
            r.with_refund = False
            r.with_replacement = True
            r.replacement_by = 'wh'
            r.replacement_state = 'in_transit'
        # Set refund state = 'We must refund'
        if r.ebay_refundInitiationType == 'AUTO_REFUND':
            r.with_return = True
            r.with_refund = True
            r.with_replacement = False
            r.refund_type = 'auto'
        if r.ebay_refundStatus == 'PENDING':
            r.with_refund = True
            r.refund_status = 'pending'
        if r.ebay_refundStatus == 'SUCCESS':
            r.with_refund = True
            r.state = 'refund_paid'
            r.refund_status = 'paid'
        # Must refund or send replacement
        if r.ebay_receipt_deliveryStatus == 'DELIVERED':
            r.receipt_state = 'delivered'
            r.with_return = True
            if r.ebay_currentType == 'MONEY_BACK' and (r.refund_status not in ['pending', 'paid'] or r.ebay_refundStatus in ['PENDING', 'SUCCESS']):
                r.refund_status = 'need_to_pay'  # Even if WH did not scanned item, we already can refund or replace
                r.state = 'to_refund'
                r.with_refund = True
                r.with_replacement = False

        if r.ebay_replacement_deliveryStatus == 'DELIVERED':
            r.with_return = False
            r.with_refund = False
            r.with_replacement = True
            # r.state = 'done'


def dv(data, path, ret_type=None):
    # Deep value of nested dict. Return ret_type if cant find it
    for ind, el in enumerate(path):
        if data.get(el):
            return dv(data[el], path[ind+1:], ret_type)
        else:
            return ret_type
    return data
