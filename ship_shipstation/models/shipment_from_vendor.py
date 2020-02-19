# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ShipmentFromVendor(models.Model):
    _name = 'sale.shipment.from.vendor'
    _rec_name = 'tracking_number'

    tracking_number = fields.Char('Tracking Number', required=True)
    sale_id = fields.Many2one('sale.order', 'Sales Order')
    store_id = fields.Many2one('sale.store', 'Store', related='sale_id.store_id', store=True)
    service_id = fields.Many2one('ship.carrier.service', 'Service')
    carrier_id = fields.Many2one('ship.carrier', 'Carrier', related='service_id.carrier_id')
    shipping_state = fields.Selection([('waiting_shipment', 'Waiting Shipment'), 
        ('in_transit', 'In Transit'),
        ('done', 'Done'),
        ('failed', 'Failed')], string="Shipment Status", default='waiting_shipment')
    store_notified = fields.Boolean(string="Store notified?")

    @api.multi
    def action_mark_as_in_transit(self):
        for shipment in self:
            shipment.write({'shipping_state': 'in_transit'})

    @api.multi
    def action_mark_as_done(self):
        for shipment in self:
            shipment.write({'shipping_state': 'done'})

    @api.multi
    def action_mark_as_failed(self):
        for shipment in self:
            shipment.write({'shipping_state': 'failed'})

    @api.multi
    def action_reset_to_waiting_shipment(self):
        for shipment in self:
            shipment.write({'shipping_state': 'waiting_shipment'})
