# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
import locale
import re

_logger = logging.getLogger(__name__)


class AmzReturnMessage(models.Model):
    _name = 'sale.store.amz.return.message'
    _inherit = ['mail.thread']
    _order = "id"

    name = fields.Char('Subject', required=True)
    store_id = fields.Many2one('sale.store', 'Store')
    raw_content = fields.Text('Raw Content')
    return_id = fields.Many2one('sale.return', string='Return')

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        self = self.with_context(default_user_id=False)
        defaults = {
            'name':  msg_dict.get('subject') or "No Subject"
        }
        # _logger.info('Amazon message: %s' % msg_dict)
        try:
            store_email = msg_dict['to'].split('<')[1][:-1]
        except Exception as e:
            _logger.error(e)
            return super(AmzReturnMessage, self).message_new(msg_dict, custom_values=defaults)
        store_id = self.env['sale.store'].search([('amz_returns_email', '=', store_email)])
        if store_id:
            defaults['store_id'] = store_id.id
        return super(AmzReturnMessage, self).message_new(msg_dict, custom_values=defaults)

    @api.multi
    def process_message(self):
        _logger.info('Processing Amazon return message. %s' % self)
        if self.name.startswith('Return authorization notification'):
            if self.message_ids:
                content = self.message_ids[0].body.replace('<br>', '\n').split('\n')
                # Just for testing purpose
                if len(content) < 5:
                    test_content = self.message_ids[0].body.replace('<br style="font-size: 12.8px">', '').replace('</span>', '')
                    content = test_content.split('<span style="font-size: 12.8px">')
                if len(content) < 5:
                    test_content = self.message_ids[0].body.replace('<br style="font-size:12.8px">', '').replace('</span>', '')
                    content = test_content.split('<span style="font-size:12.8px">')

                values = {'lines': []}
                searchstrings = [
                    ['web_order_id', 'Order ID: #'],
                    ['item', 'Item:'],
                    ['product_uom_qty', 'Quantity:'],
                    ['return_reason', 'Return reason:'],
                    ['customer_comments', 'Customer comments:'],
                    ['carrier_id', 'Return Shipping Carrier:'],
                    ['tracking_number', 'Tracking ID:'],
                    ['amz_return_request_details', 'Return request details:'],
                    ['request_date', 'Request received:']
                ]
                for ind, line in enumerate(content):
                    for searchstring in searchstrings:
                        if line.strip().startswith(searchstring[1]):
                            val = line[len(searchstring[1]):].strip()
                            if searchstring[0] == "item":
                                values['lines'].append({'item': val})
                            elif searchstring[0] == "product_uom_qty":
                                values['lines'][-1]['product_uom_qty'] = float(val)
                            elif searchstring[0] == "return_reason":
                                values['lines'][-1]['return_reason'] = val
                            elif searchstring[0] == "customer_comments":
                                values['lines'][-1]['customer_comments'] = val
                            elif searchstring[0] == "request_date":
                                values['request_date'] = datetime.strptime(val.strip(), '%B %d, %Y').strftime(DEFAULT_SERVER_DATE_FORMAT)
                            elif searchstring[0] == "carrier_id":
                                values['carrier_id'] = line[len(searchstring[1]) + 2:].strip()
                            elif searchstring[0].strip() == "amz_return_request_details":
                                if re.findall("<a.*>(.*?)</a>", content[ind + 1]):
                                    values['amz_return_request_details'] = re.findall("<a.*>(.*?)</a>", content[ind + 1])[0]
                                elif re.findall("http.*", content[ind + 1]):
                                    values['amz_return_request_details'] = re.findall("http.*", content[ind + 1])[0]
                            else:
                                values[searchstring[0]] = line[len(searchstring[1]):].strip()
                            break
                if 'carrier_id' in values and values['carrier_id']:
                    carrier_id = self.env['ship.carrier'].search([('name', '=', values['carrier_id'])])
                    if carrier_id:
                        values['carrier_id'] = carrier_id.id
                    else:
                        values.pop('carrier_id')
                values['amz_related_message_id'] = self.id
                values['store_id'] = self.store_id.id
                lines = values['lines']
                values.pop('lines')
                if values.get('web_order_id'):
                    sale_order_id = self.env['sale.order'].search([('web_order_id', '=', values['web_order_id']), ('state', '!=', 'cancel')], limit=1)
                    if not sale_order_id:
                        _logger.error('Cant find order %s  %s', values['web_order_id'], self)
                    if len(sale_order_id.order_line) == len(lines) and len(lines) == 1:
                        values['partner_id'] = sale_order_id.partner_id.id
                        values['sale_order_id'] = sale_order_id.id
                        values['type'] = 'amazon'
                        old_return = self.env['sale.return'].search([('web_order_id', '=', values['web_order_id'])])
                        if old_return:
                            self.proceed_old_return(old_return, lines)
                        else:
                            self.proceed_new_return(sale_order_id, values, lines)
                else:
                    _logger.error('No web_order_id: %s' % self)

    @api.multi
    def create_return(self):
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        _logger.info('Manual creation of return using Amazon return message. %s' % self)
        if self.message_ids and self.store_id:
            body = self.message_ids[0].body

            content = body.replace('<br>', '\n').split('\n')

            values = {'lines': []}
            searchstrings = [
                ['web_order_id', 'Order ID: # '],
                ['item', 'Item: '],
                ['product_uom_qty', 'Quantity: '],
                ['return_reason', 'Return reason: '],
                ['customer_comments', 'Customer comments: '],
                ['carrier_id', 'Return Shipping Carrier:'],
                ['tracking_number', 'Tracking ID: '],
                ['amz_return_request_details', 'Return request details:'],
                ['request_date', 'Request received: ']
            ]
            for ind, line in enumerate(content):
                for searchstring in searchstrings:
                    if line.startswith(searchstring[1]):
                        val = line[len(searchstring[1]):].replace('\n', '').strip()
                        if searchstring[0] == "item":
                            values['lines'].append({'item': val})
                        elif searchstring[0] == "product_uom_qty":
                            values['lines'][-1]['product_uom_qty'] = float(val)
                        elif searchstring[0] == "return_reason":
                            values['lines'][-1]['return_reason'] = val
                        elif searchstring[0] == "customer_comments":
                            values['lines'][-1]['customer_comments'] = val
                        elif searchstring[0] == "request_date":
                            values['request_date'] = datetime.strptime(val, '%B %d, %Y').strftime(DEFAULT_SERVER_DATE_FORMAT)
                        elif searchstring[0] == "carrier_id":
                            values['carrier_id'] = line[len(searchstring[1]) + 2:].strip()
                        elif searchstring[0].strip() == "amz_return_request_details":
                            if re.findall("<a.*>(.*?)</a>", content[ind + 1]):
                                values['amz_return_request_details'] = re.findall("<a.*>(.*?)</a>", content[ind + 1])[0]
                            elif re.findall("http.*", content[ind + 1]):
                                values['amz_return_request_details'] = re.findall("http.*", content[ind + 1])[0]
                        else:
                            values[searchstring[0]] = line[len(searchstring[1]):].strip()
                        break
            if 'carrier_id' in values and values['carrier_id']:
                carrier_id = self.env['ship.carrier'].search([('name', '=', values['carrier_id'])])
                if carrier_id:
                    values['carrier_id'] = carrier_id.id
                else:
                    values.pop('carrier_id')
            values['amz_related_message_id'] = self.id
            values['store_id'] = self.store_id.id
            lines = values['lines']
            values.pop('lines')
            if values.get('web_order_id'):
                sale_order_id = self.env['sale.order'].search([('web_order_id', '=', values['web_order_id']), ('state', '!=', 'cancel')], limit=1)
                if not sale_order_id:
                    _logger.error('Cant find order %s  %s', values['web_order_id'], self)
                # if len(sale_order_id.order_line) == len(lines) and len(lines) == 1:
                values['partner_id'] = sale_order_id.partner_id.id
                values['sale_order_id'] = sale_order_id.id
                values['type'] = 'amazon'
                old_return = self.env['sale.return'].search([('web_order_id', '=', values['web_order_id'])])
                if old_return:
                    self.proceed_old_return(old_return, lines, values)
                else:
                    self.proceed_new_return(sale_order_id, values, lines)
            else:
                _logger.error('No web_order_id: %s' % self)

    @api.model
    def proceed_old_return(self, old_return, lines, values):
        self.return_id = old_return.id
        old_return.return_reason = lines[0].get('return_reason')
        old_return.customer_comments = lines[0].get('customer_comments')
        old_return.amz_return_request_details = values.get('amz_return_request_details')
        old_return.amz_related_message_id = self.id

    @api.model
    def proceed_new_return(self, sale_order_id, values, lines):
        return_id = self.env['sale.return'].create(values)
        self.return_id = return_id.id
        ok = False
        if len(sale_order_id.order_line) == len(lines) and len(lines) == 1:  # If single line just pick it up
            values['partner_id'] = sale_order_id.partner_id.id
            values['sale_order_id'] = sale_order_id.id
            values['type'] = 'amazon'
            return_id = self.env['sale.return'].create(values)
            self.return_id = return_id.id
            lines[0]['name'] = sale_order_id.order_line[0].product_id.name
            lines[0]['return_id'] = return_id.id
            lines[0]['product_id'] = sale_order_id.order_line[0].product_id.id
            lines[0]['sale_line_id'] = sale_order_id.order_line[0].id
            lines[0]['product_uom'] = sale_order_id.order_line[0].product_uom.id
            self.env['sale.return.line'].create(lines[0])
        else:  # Few lines. Lets try to match using partslink
            for index, ln in enumerate(lines):
                for order_line in sale_order_id.order_line:
                    if order_line.product_id.partslink in ln['item']:
                        ok = True
                        ln['name'] = order_line.name
                        ln['return_id'] = return_id.id
                        ln['product_id'] = order_line.product_id.id
                        ln['sale_line_id'] = order_line.id
                        ln['product_uom'] = order_line.product_uom.id
                        self.env['sale.return.line'].create(ln)
            if not ok:
                msg = {
                    'name': 'Achtung ! Cant match return item',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'custom.message',
                    'target': 'new',
                    'context': {'default_text': 'Return is created, but please check lines manually cuz I cant match it with message text.'}
                }
                return msg
        msg = 'Amazon return created using return message. Order:%s Return:%s' % (values['web_order_id'], return_id.name)
        _logger.info(msg)
        attachment = {
            'color': '#7CD197',
            'fallback': 'Amazon return',
            'title': 'Amazon return. No:%s' % return_id.name,
            'text': msg
        }
        slack_returns_channel = self.env['ir.config_parameter'].get_param('slack_returns_channel')
        self.env['slack.calls'].notify_slack('Amazon return', '', slack_returns_channel, attachment)
