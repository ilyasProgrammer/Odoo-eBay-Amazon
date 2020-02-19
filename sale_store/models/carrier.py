# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from datetime import datetime

class CarrierPackage(models.Model):
    _name = 'ship.carrier.package'

    name = fields.Char('Package Name', required=True, help="Name of the package")
    carrier_id = fields.Many2one('ship.carrier', 'Carrier', required=True, help="Carrier allowing the package")
    ss_code = fields.Char('Package Code', required=True, help="Code of the package as provided by Shipstation")
    international = fields.Boolean('International')
    domestic = fields.Boolean('Domestic')

class Carrier(models.Model):
    _name = 'ship.carrier'

    name = fields.Selection([
        ('AGS', 'AGS'),
        ('CNWY', 'CNWY'),
        ('FedEx', 'FedEx'),
        ('SAIA', 'SAIA'),
        ('UPS', 'UPS'),
        ('USPS', 'USPS'),
        ('YRC', 'YRC'),
        ('ESTES', 'ESTES'),
    ], 'Carrier Name', required=True, help="Name of the carrier")
    description = fields.Char('Description')
    ss_code = fields.Char('Carrier Code', required=True, help="Code of the carrier as provided by Shipstation")
    package_ids = fields.One2many('ship.carrier.package', 'carrier_id', 'Packages')
    service_ids = fields.One2many('ship.carrier.service', 'carrier_id', 'Services')
    enabled = fields.Boolean('Active')

    # @api.multi
    # def _check_required_if_name(self):
    #     """ If the field has 'required_if_name="<name>"' attribute, then it is
    #     required if record.name is <name>. """
    #     for carrier in self:
    #         if any(getattr(f, 'required_if_name', None) == carrier.name.lower() and not carrier[k] for k, f in self._fields.items()):
    #             return False
    #     return True
    #
    # _constraints = [
    #     (_check_required_if_name, 'Required fields not filled', []),
    # ]

class CarrierService(models.Model):
    _name = 'ship.carrier.service'

    name = fields.Char('Service Name', required=True, help="Name of the service")
    ss_code = fields.Char('Service Code', help="Code of the service as provided by Shipstation")
    carrier_id = fields.Many2one('ship.carrier', 'Provided by', required=True, help="Carrier providing the service")
    package_id = fields.Many2one('ship.carrier.package', 'Package', help="Package to be used for the service")
    max_weight = fields.Float('Max Weight (lbs)', digits=dp.get_precision('Stock Weight'))
    max_length = fields.Float('Max Length (in)', digits=dp.get_precision('Product Dimension'))
    max_length_plus_girth = fields.Float('Girth (Length + 2(Width) + 2(height)) in', digits=dp.get_precision('Product Dimension'))
    international = fields.Boolean('International')
    domestic = fields.Boolean('Domestic')
    enabled= fields.Boolean('Enabled')
