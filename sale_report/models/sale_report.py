# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Team(models.Model):
    _inherit = 'crm.team'

    use_excep_quot = fields.Boolean('Exception Quotation', help="Check this box to manage exception quotation in this sales team.")
