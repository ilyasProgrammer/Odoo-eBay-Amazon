# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    preferred_carrier_id = fields.Many2one('ship.carrier', "Preferred Carrier")
    preferred_service_id = fields.Many2one('ship.carrier.service', "Preferred Service")
    preferred_package_id = fields.Many2one('ship.carrier.package', "Preferred Package")

    @api.multi
    @api.onchange('preferred_carrier_id')
    def onchange_carrier_id(self):
        if not self.preferred_carrier_id:
            return {'domain': {
                'preferred_service_id': [],
                'preferred_package_id': [],
            }}
        return {'domain': {
                'preferred_service_id': [('carrier_id.id', '=', self.preferred_carrier_id.id)],
                'preferred_package_id': [('carrier_id.id', '=', self.preferred_carrier_id.id)]
            }}
