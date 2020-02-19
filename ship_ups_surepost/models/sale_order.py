# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def button_get_cheapest_service(self):
        for so in self:
            ups_carrier_id = self.env['ship.carrier'].search([('name', '=', 'UPS'), ('enabled', '=', True)], limit=1)
            if ups_carrier_id:
                ups_carrier_id.ups_get_rates(so)
            # service = so.get_cheapest_service()
            # so.write({
            #     'rate': service.get('rate'),
            #     'service_id': service.get('service_id'),
            #     'package_id': service.get('package_id'),
            #     'exceeds_limits': service['exceeds_limits'] if service.get('exceeds_limits') else False
            # })
