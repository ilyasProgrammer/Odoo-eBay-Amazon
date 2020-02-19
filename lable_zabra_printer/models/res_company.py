# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    product_printer = fields.Char()
    location_printer = fields.Char()
    shipping_printer = fields.Char()
