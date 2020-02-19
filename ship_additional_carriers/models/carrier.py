# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Carrier(models.Model):
    _inherit = 'ship.carrier'

    name = fields.Selection(selection_add=[('PYLE', 'Pyle'),
                                           ('AVERITT', 'Averitt'),
                                           ('DIAMOND', 'Diamond Line'),
                                           ('CENTRAL', 'Central Freight'),
                                           ('CROSSCTY', 'Cross Country'),
                                           ('STAMPS', 'Stamps'),
                                           ('DAYTON', 'Dayton'),
                                           ('R+L CARRRIER', 'R+L Carrier'),
                                           ('BEAVER EXPRESS SERVICE', 'Beaver Express Service LLC')])
