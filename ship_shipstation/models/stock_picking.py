# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
import pprint
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _order = 'id desc'

    warehouse_id = fields.Many2one('stock.warehouse', string='Ship From')
    weight = fields.Float(string="Weight", digits=dp.get_precision('Stock Weight'))
    length = fields.Float(string="Length", digits=dp.get_precision('Product Dimension'))
    width = fields.Float(string="Width", digits=dp.get_precision('Product Dimension'))
    height = fields.Float(string="Height", digits=dp.get_precision('Product Dimension'))
    tracking_number = fields.Char('Tracking No.', help="Tracking number of shipment provided by carrier")
    shipment_id = fields.Char('Shipment ID', help="Shipment ID of the Tracking number of shipment provided by carrier.")
    is_label_voided = fields.Boolean('Label Voided ?')
    shipping_state = fields.Selection([('waiting_shipment', 'Waiting Shipment'),
        ('in_transit', 'In Transit'),
        ('done', 'Done'),
        ('failed', 'Failed')], string="Shipment Status", default='waiting_shipment')
    service_id = fields.Many2one('ship.carrier.service')
    carrier_id = fields.Many2one('ship.carrier', 'Carrier')
    package_id = fields.Many2one('ship.carrier.package', 'Package')
    rate = fields.Float('Rate', help='Price of the shipment')
    exceeds_limits = fields.Boolean(string="Exceeds Limits?")
    label = fields.Binary('File', readonly=True)
    file_name = fields.Char('File Name', compute='_compute_file_name')
    store_notified = fields.Boolean(string="Store notified?")
    store_id = fields.Many2one('sale.store', 'Store')
    sale_id = fields.Many2one('sale.order', "Sales Order", compute='_compute_sale_id', search='_search_sale_id', store=True)
    out_type = fields.Boolean(compute='compute_picking_type_out', string='Out Type')
    carrier_tracking_status = fields.Char(string="Carrier Tracking Status", readonly=True)
    tracking_line_ids = fields.One2many('stock.picking.tracking.line', 'picking_id', 'Additonal Tracking Numbers')
    high_rate_warned = fields.Boolean('Warned for high rate')

    @api.one
    @api.depends('group_id')
    def _compute_sale_id(self):
        for picking in self:
            if picking.group_id:
                picking.sale_id = self.env['sale.order'].search([('procurement_group_id', '=', picking.group_id.id)], limit=1)

    def _search_sale_id(self, operator, value):
        moves = self.env['stock.move'].search(
            [('picking_id', '!=', False), ('procurement_id.sale_line_id.order_id', operator, value)]
        )
        return [('id', 'in', moves.mapped('picking_id').ids)]

    @api.multi
    @api.onchange('carrier_id')
    def onchange_carrier_id(self):
        if not self.carrier_id:
            return {'domain': {
                'service_id': [],
                'package_id': [],
            }}
        return {'domain': {
                'service_id': [('carrier_id.id', '=', self.carrier_id.id)],
                'package_id': [('carrier_id.id', '=', self.carrier_id.id)]
            }}

    # @api.model
    # def run(self):
    #     pickings = self.env['stock.picking'].search([('label', '!=', False), ('out_type', '!=', False)])
    #     for picking in pickings:
    #         picking.button_get_tracking_details()

    @api.multi
    def process_to_validate(self):
        self.ensure_one()
        # If still in draft => confirm and assign
        if self.state == 'draft':
            self.action_confirm()
            if self.state != 'assigned':
                self.action_assign()
                if self.state != 'assigned':
                    raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
        for pack in self.pack_operation_ids:
            if pack.product_qty > 0:
                pack.write({'qty_done': pack.product_qty})
            else:
                pack.unlink()
        self.do_transfer()

    @api.multi
    def button_lable_void(self):
        self.ensure_one()
        if self.tracking_number and self.label and self.shipment_id:
            result = self.env['sale.order'].ss_execute_request('POST', '/shipments/voidlabel', {'shipmentId': self.shipment_id})
            if result.get('approved'):
                self.write({'is_label_voided': True})

    @api.multi
    def button_get_tracking_details(self):
        self.ensure_one()
        if not self.tracking_number:
            raise UserError("There are no Trackiing Number available.")
        if self.carrier_id:
            method_name = '%s_get_status_of_tracking_number' % self.carrier_id.ss_code
            if hasattr(self.carrier_id, method_name):
                method = getattr(self.carrier_id, method_name)
            if not hasattr(self.carrier_id, method_name):
                raise UserError(_('No method found for get status.'))
            response = method(shipment=self)
            if response:
                self.carrier_tracking_status = response

    @api.depends('picking_type_id.name')
    def compute_picking_type_out(self):
        for picking in self:
            if picking.picking_type_code == 'outgoing':
                picking.out_type = True
            else:
                picking.out_type = False

    @api.multi
    def prepare_get_label_data(self, shipstation_id):
        from_partner_id = self.warehouse_id.partner_id
        to_partner_id = self.sale_id.partner_id if self.sale_id else self.replacement_return_id.partner_id
        today = datetime.today().strftime('%Y-%m-%d')
        fedex_carrier = self.env['ship.carrier'].browse(1)
        self.residential = fedex_carrier.fedex_validate_address(self, {'toCity': to_partner_id.city,
                                                                       'toState': to_partner_id.state_id.code,
                                                                       'toPostalCode': to_partner_id.zip,
                                                                       'toCountry': to_partner_id.country_id.code})
        data = {
            'orderId': shipstation_id,
            'carrierCode': self.carrier_id.ss_code,
            'serviceCode': self.service_id.ss_code,
            'fedex_code': self.service_id.fedex_code,
            'packageCode': self.package_id.ss_code,
            'confirmation': 'delivery',
            'shipDate': today,
            'weight': {
                'value': self.weight,
                'units': 'pounds'
            },
            'dimensions': {
                'units': 'inches',
                'length': self.length,
                'width': self.width,
                'height': self.height,
            },
            'shipFrom': {
                'name': self.store_id.name,
                'street1': from_partner_id.street,
                'street2': from_partner_id.street2 or '',
                'city': from_partner_id.city,
                'state': from_partner_id.state_id.code,
                'postalCode': from_partner_id.zip,
                'country': from_partner_id.country_id.code,
                'phone': from_partner_id.phone,
            },
            'shipTo': {
                'name': to_partner_id.name,
                'street1': to_partner_id.street,
                'street2': to_partner_id.street2 or '',
                'city': to_partner_id.city,
                'state': to_partner_id.state_id.code,
                'postalCode': to_partner_id.zip,
                'country': to_partner_id.country_id.code,
                'phone': to_partner_id.phone,
                'residential': self.residential
            },
            'advancedOptions': {
                'warehouseId': self.store_id.ss_warehouse_id
            }
        }
        return data

    @api.multi
    def button_get_label(self):
        self.ensure_one()
        if self.carrier_id.name == 'USPS' and self.rate >= 30.0 and not self.high_rate_warned:
            self.write({'high_rate_warned': True})
            self.env.cr.commit()
            raise UserError(_("The shipping rate is unusually high. Please let your administrator know to see if there is a likely configuration error."))
        fedex_oversized = self.env.ref('ship_fedex.carrier_fedex_oversized')
        if self.carrier_id == fedex_oversized:
            data = self.prepare_get_label_data('')
            result = self.carrier_id.fedex_get_label(self, data)
        else:
            if not self.sale_id:
                result = self.replacement_return_id.sale_order_id.ss_send_order(self.replacement_return_id.sale_order_id.name + datetime.now().strftime('%Y%m%d%H%M%S'))
                data = self.prepare_get_label_data(result['orderId'])
                #self.replacement_return_id.write({'shipstation_id': result['orderId']})
                #data = self.prepare_get_label_data(self.replacement_return_id.shipstation_id)
            else:
                if not self.sale_id.shipstation_id:
                    result = self.sale_id.ss_send_order(self.sale_id.name)
                    self.sale_id.write({'shipstation_id': result['orderId']})
                data = self.prepare_get_label_data(self.sale_id.shipstation_id)
            result = self.env['sale.order'].ss_execute_request('POST', '/orders/createlabelfororder', data)
        self.write({'tracking_number': result['trackingNumber'], 'shipment_id': result['shipmentId'], 'is_label_voided': result['voided'], 'label': result['labelData']})

    @api.multi
    def button_get_new_label(self):
        now = datetime.now().strftime('%Y%m%d%H%M%S')
        order_result = {'orderId': ''}
        fedex_oversized = self.env.ref('ship_fedex.carrier_fedex_oversized')
        if self.carrier_id == fedex_oversized:
            data = self.prepare_get_label_data('')
            result = self.carrier_id.fedex_get_label(self, data)
        else:
            if not self.sale_id:
                order_result = self.replacement_return_id.sale_order_id.ss_send_order(self.replacement_return_id.sale_order_id.name + datetime.now().strftime('%Y%m%d%H%M%S'))
                data = self.prepare_get_label_data(order_result['orderId'])
            else:
                order_result = self.sale_id.ss_send_order(self.sale_id.name + now)
                data = self.prepare_get_label_data(order_result['orderId'])
            result = self.env['sale.order'].ss_execute_request('POST', '/orders/createlabelfororder', data)
        self.env['stock.picking.tracking.line'].create({
            'name': result['trackingNumber'],
            'label': result['labelData'],
            'picking_id': self.id,
            'shipstation_id': order_result['orderId']
        })

    @api.multi
    def button_update_shipment_rate(self):
        for picking in self:
            rate = picking.sale_id.get_update_shipment_rate()
            picking.write({'rate': rate})

    @api.multi
    def get_cheapest_service(self):
        self.ensure_one()
        if self.length == 0 or self.width == 0 or self.height == 0 or self.weight == 0:
            return {'rate': 0.0, 'service_id': False, 'package_id': False}
        log = ''
        replace_log = ''
        ServiceObj = self.env['ship.carrier.service']
        girth = self.length + (2 * self.width) + 2 * (self.height)
        allowed_service_ids = ServiceObj.search([('enabled', '=', True),
                                                 ('max_weight', '>=', self.weight),
                                                 ('max_length', '>=', self.length),
                                                 ('max_length_plus_girth', '>=', girth),
                                                 ('oversized', '=', True if girth > 136 else False)])
        if not allowed_service_ids:
            return {'rate': 0.0, 'service_id': False, 'package_id': False, 'exceeds_limits': True}
        if girth > 136:
            # carrier_ids = allowed_service_ids.mapped('carrier_id').filtered(lambda x: x.enabled and x.max_girth > 130)
            carrier_ids = [self.env.ref('ship_fedex.carrier_fedex_oversized')]
            # carrier_ids.append(self.env.ref('sale_store.carrier_fedex'))
        else:
            carrier_ids = allowed_service_ids.mapped('carrier_id').filtered(lambda x: x.enabled)
        first_result = True
        cheapest_rate = 0.0
        cheapest_service_id = ServiceObj
        fedex_carrier = self.env.ref('sale_store.carrier_fedex')
        for c in carrier_ids:
            replace_log = ''
            data = {
                'carrierCode': c.ss_code,
                'packageCode': 'package',
                'fromPostalCode': self.warehouse_id.partner_id.zip or '48035',
                'toPostalCode': self.partner_id.zip,
                'toState': self.partner_id.state_id.code,
                'toCountry': self.partner_id.country_id.code,
                'toCity': self.partner_id.city,
                'weight': {
                    'value': self.weight,
                    'units': 'pounds'
                },
                'dimensions': {
                    'units': 'inches',
                    'length': self.length,
                    'width': self.width,
                    'height': self.height
                },
                'confirmation': 'delivery'
            }
            self.residential = fedex_carrier.fedex_validate_address(self, data)
            data['residential'] = self.residential
            _logger.info('%s' % data)
            result = []
            if girth < 136:
                result = self.env['sale.order'].ss_execute_request('POST', '/shipments/getrates', data)
                for r_ss in result:
                    r_ss['src'] = 'SS'
                    log += 'Src: SS  Service: %s  Rate: %s' % (r_ss['serviceCode'], r_ss['shipmentCost'] + r_ss['otherCost']) + '\n'
            else:
                if c.ss_code == 'fedex':
                    try:
                        rr = c.fedex_get_rates(picking=self, data=data)  # rate request
                        fedex_result = []
                        logging.info("HighestSeverity: %s", rr.response.HighestSeverity)
                        # RateReplyDetails can contain rates for multiple ServiceTypes if ServiceType was set to None
                        for service in rr.response.RateReplyDetails:
                            for detail in service.RatedShipmentDetails:
                                for surcharge in detail.ShipmentRateDetail.Surcharges:
                                    if surcharge.SurchargeType == 'OUT_OF_DELIVERY_AREA':
                                        logging.info("%s: ODA rr charge %s", service.ServiceType, surcharge.Amount.Amount)
                            for rate_detail in service.RatedShipmentDetails:
                                logging.info("%s: %s Net FedEx Charge %s %s", service.ServiceType, rate_detail.ShipmentRateDetail.RateType, rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Currency, rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount)
                                fedex_result.append({'src': 'Direct FedEx',
                                                     'otherCost': 0,
                                                     'RateType': rate_detail.ShipmentRateDetail.RateType,
                                                     'serviceName': service.ServiceType,
                                                     'serviceCode': 'fedex_' + service.ServiceType.lower() if 'fedex' not in service.ServiceType.lower() else service.ServiceType.lower(),
                                                     'fedex_code': service.ServiceType,
                                                     'shipmentCost': rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount})
                        # Check for warnings, this is also logged by the base class.
                        if rr.response.HighestSeverity == 'NOTE':
                            for notification in rr.response.Notifications:
                                if notification.Severity == 'NOTE':
                                    logging.info(notification)
                        log += '\nResidential: %s\n' % rr.RequestedShipment.Shipper.Address.Residential
                        for fr in fedex_result:
                            log += 'Src: FX  Service: %s  Rate: %s  Rate Type: %s' % (fr['serviceCode'], fr['shipmentCost'], fr['RateType']) + '\n'
                        # for ssr in result:
                        #     if fr['serviceCode'].replace('_', '') == ssr['serviceCode'].replace('_', '') and (ssr.get('RateType') is None or ssr.get('RateType') and ssr['RateType'] != 'PAYOR_ACCOUNT_PACKAGE'):
                        #         msg = 'FedEx SS rate %s %s replaced with %s' % (ssr['serviceCode'], ssr['otherCost'] + ssr['shipmentCost'], fr['shipmentCost'])
                        #         logging.info(msg)
                        #         replace_log += msg + '\n'
                        #         ssr['otherCost'] = 0
                        #         ssr['shipmentCost'] = fr['shipmentCost']
                        #         ssr['RateType'] = fr['RateType']
                        #         break
                        result = fedex_result
                    except Exception as e:
                        logging.error(e)
            for rate in result:
                total_rate = rate['shipmentCost'] + rate['otherCost']
                if rate.get('fedex_code'):
                    service_id = allowed_service_ids.filtered(lambda x: x.fedex_code == rate['fedex_code'] and x.carrier_id.id == c.id)
                else:
                    service_id = allowed_service_ids.filtered(lambda x: x.ss_code == rate['serviceCode'] and x.carrier_id.id == c.id)
                if first_result:
                    if service_id:
                        cheapest_rate = total_rate
                        cheapest_service_id = service_id[0]
                        first_result = False
                if not first_result and total_rate < cheapest_rate and service_id:
                    cheapest_rate = total_rate
                    cheapest_service_id = service_id[0]
        self.services_prices_log = log + '\n' + replace_log
        if cheapest_service_id:
            return {'rate': cheapest_rate, 'service_id': cheapest_service_id.id, 'package_id': cheapest_service_id.package_id.id, 'exceeds_limits': False}
        else:
            return {'rate': 0.0, 'service_id': False, 'package_id': False, 'exceeds_limits': False}

    @api.multi
    def button_get_cheapest_service(self):
        for picking in self:
            service = picking.get_cheapest_service()
            service_id = self.env['ship.carrier.service'].browse(service['service_id'])
            picking.write({
                'rate': service.get('rate'),
                'service_id': service.get('service_id'),
                'carrier_id': service_id.carrier_id.id,
                'package_id': service.get('package_id'),
                'exceeds_limits': service['exceeds_limits'] if service.get('exceeds_limits') else False
            })

    @api.multi
    def button_set_dimension_from_first_order_line(self):
        for picking in self:
            if picking.move_lines:
                p = picking.move_lines[0].product_id
                dim = [p.length, p.width, p.height, p.weight]
                for d in dim:
                    if d == 0.0:
                        p.button_sync_with_autoplus()
                        break
                picking.write({'length': p.length, 'width': p.width, 'height': p.height, 'weight': p.weight})

    @api.multi
    def _compute_file_name(self):
        for picking in self:
            picking.file_name = (picking.tracking_number or 'blank') + '.pdf'

    @api.multi
    def button_get_status_of_tracking_number(self):
        self.ensure_one()
        if hasattr(self.carrier_id, '%s_get_status_of_tracking_number' % self.carrier_id.name.lower()):
            state = getattr(self.carrier_id, '%s_get_status_of_tracking_number' % self.carrier_id.name.lower())(self)

    @api.multi
    def action_mark_as_in_transit(self):
        for picking in self:
            picking.write({'shipping_state': 'in_transit'})

    @api.multi
    def action_mark_as_done(self):
        for picking in self:
            picking.write({'shipping_state': 'done'})

    @api.multi
    def action_mark_as_failed(self):
        for picking in self:
            picking.write({'shipping_state': 'failed'})

    @api.multi
    def action_reset_to_waiting_shipment(self):
        for picking in self:
            picking.write({'shipping_state': 'waiting_shipment'})

    @api.multi
    def update_autoplus(self):
        PickingOrder = self.env['stock.picking']
        for picking in self:
            if len(picking.move_lines) > 1:
                raise UserError(_('This order has more than one products. AutoPlus will not be updated. Proceed with getting the cheapest shipping service.'))
            product = picking.product_id
            product.write({'length': picking.length, 'width': picking.width, 'height': picking.height, 'weight': picking.weight})
            product.update_autoplus()
            pickings = PickingOrder.search([('product_id', '=', product.id), ('state', '!=', 'done')])
            pickings.button_set_dimension_from_first_order_line()
            if picking.sale_id:
                picking.sale_id.write({'length': picking.length, 'width': picking.width, 'height': picking.height, 'weight': picking.weight})
        return True


class TrackingLine(models.Model):
    _name = 'stock.picking.tracking.line'
    _order = 'id desc'

    name = fields.Char('Tracking Number', required=True)
    shipstation_id = fields.Char('Shipstation ID', required=True)
    file_name = fields.Char('File Name', compute='_compute_file_name')
    label = fields.Binary('File', readonly=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', required=True)

    @api.multi
    def _compute_file_name(self):
        for t in self:
            t.file_name = (t.name or 'blank') + '.pdf'
