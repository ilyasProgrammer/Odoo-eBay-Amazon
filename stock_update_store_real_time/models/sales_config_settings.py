# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ShipRateCalculationConfiguration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'sale.config.settings'

    ship_from_address_id = fields.Many2one('res.partner', 'Ship From')
    ship_to_address_id = fields.Many2one('res.partner', 'Ship To')

    @api.multi
    def set_ship_rate_addresses(self):
        ship_from_address_id = self[0].ship_from_address_id.id or ''
        self.env['ir.config_parameter'].set_param('ship_from_address_id', ship_from_address_id, groups=["base.group_user"])
        ship_to_address_id = self[0].ship_to_address_id.id or ''
        self.env['ir.config_parameter'].set_param('ship_to_address_id', ship_to_address_id, groups=["base.group_user"])

    @api.model
    def get_default_ship_rate_addresses(self, fields):
        params = self.env['ir.config_parameter']
        ship_from_address_id = params.get_param('ship_from_address_id', default='')
        ship_to_address_id = params.get_param('ship_to_address_id', default='')
        return {
            'ship_from_address_id': int(ship_from_address_id) if ship_from_address_id else False,
            'ship_to_address_id': int(ship_to_address_id) if ship_to_address_id else False,
        }
